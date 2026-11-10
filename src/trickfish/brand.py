"""Trickfish visual system: dark, typographic, one accent colour.

Everything is drawn with Pillow at 2x and downsampled, so edges stay smooth.
Fonts: Inter / Inter Display (SIL OFL). Falls back to DejaVu when absent.
"""

import io
import pathlib

import chess
import chess.svg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INK = (10, 14, 20)
CARD = (20, 26, 36)
LINE = (38, 48, 62)
WHITE = (255, 255, 255)
MUTED = (139, 151, 168)
SOFT = (196, 205, 217)
ACCENT = (255, 90, 54)
ICE = (157, 184, 211)
SCALE = 2

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOGO = ROOT / "assets" / "trickfish-logo.png"
FONT_DIRS = [pathlib.Path("/usr/share/fonts/opentype/inter"), ROOT / "assets" / "fonts"]
FALLBACK = {"bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"}
_fonts = {}


def font(name, size):
    """name: e.g. 'InterDisplay-Black', 'Inter-SemiBold'. Size in final pixels."""
    key = (name, size)
    if key not in _fonts:
        path = next((directory / (name + ".otf") for directory in FONT_DIRS
                     if (directory / (name + ".otf")).exists()), None)
        if path is None:
            path = FALLBACK["bold" if any(w in name for w in ("Bold", "Black", "Semi")) else "regular"]
        _fonts[key] = ImageFont.truetype(str(path), size * SCALE)
    return _fonts[key]


class Canvas:
    """A 2x drawing surface with layout helpers in final-pixel coordinates."""

    def __init__(self, width, height, glow=((0.85, 0.08, 0.55, 0.16),), background=INK):
        self.width, self.height = width, height
        self.image = Image.new("RGB", (width * SCALE, height * SCALE), background)
        for x, y, radius, strength in glow:
            self.glow(x, y, radius, strength)
        self.draw = ImageDraw.Draw(self.image)

    def glow(self, x, y, radius, strength, color=ACCENT):
        size = int(max(self.width, self.height) * radius * SCALE)
        layer = Image.new("L", self.image.size, 0)
        ImageDraw.Draw(layer).ellipse((x * self.width * SCALE - size, y * self.height * SCALE - size,
                                       x * self.width * SCALE + size, y * self.height * SCALE + size),
                                      fill=int(255 * strength))
        layer = layer.filter(ImageFilter.GaussianBlur(size * 0.45))
        self.image = Image.composite(Image.new("RGB", self.image.size, color), self.image, layer)

    def s(self, *values):
        return [int(value * SCALE) for value in values]

    def text(self, xy, text, face, size, fill=WHITE, anchor="la"):
        self.draw.text(self.s(*xy), text, font=font(face, size), fill=fill, anchor=anchor)

    def width_of(self, text, face, size):
        return font(face, size).getlength(text) / SCALE

    def wrap(self, xy, text, face, size, width, fill=WHITE, leading=1.25):
        words, lines, line = text.split(), [], ""
        for word in words:
            trial = (line + " " + word).strip()
            if self.width_of(trial, face, size) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        x, y = xy
        for index, value in enumerate(lines):
            self.text((x, y + index * size * leading), value, face, size, fill)
        return y + len(lines) * size * leading

    def card(self, box, radius=28, fill=CARD, outline=LINE, width=2):
        self.draw.rounded_rectangle(self.s(*box), radius=radius * SCALE, fill=fill,
                                    outline=outline, width=width * SCALE)

    def pill(self, xy, label, face="Inter-SemiBold", size=26, fill=CARD, color=SOFT, outline=LINE,
             pad=(22, 12), dot=None):
        x, y = xy
        extra = (size * 0.55 + 12) if dot else 0
        w = self.width_of(label, face, size) + pad[0] * 2 + extra
        h = size + pad[1] * 2
        self.draw.rounded_rectangle(self.s(x, y, x + w, y + h), radius=int(h * SCALE / 2), fill=fill,
                                    outline=outline, width=2 * SCALE)
        if dot:
            r = size * 0.22
            cx, cy = x + pad[0] + r, y + h / 2
            self.draw.ellipse(self.s(cx - r, cy - r, cx + r, cy + r), fill=dot)
        self.text((x + pad[0] + extra, y + h / 2), label, face, size, color, anchor="lm")
        return x + w

    def paste(self, image, xy, radius=0):
        """Paste an image produced at 2x (board(), mark()) at final-pixel position xy."""
        mask = None
        if radius:
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1),
                                                   radius=radius * SCALE, fill=255)
        if image.mode == "RGBA":
            alpha = image.getchannel("A")
            if mask is not None:
                alpha = Image.composite(alpha, Image.new("L", image.size, 0), mask)
            mask = alpha
        self.image.paste(image.convert("RGB"), tuple(self.s(*xy)), mask)

    def shadow(self, box, radius=28, blur=40, strength=0.55):
        layer = Image.new("L", self.image.size, 0)
        x0, y0, x1, y1 = box
        ImageDraw.Draw(layer).rounded_rectangle(self.s(x0, y0 + 18, x1, y1 + 18), radius=radius * SCALE,
                                                fill=int(255 * strength))
        layer = layer.filter(ImageFilter.GaussianBlur(blur * SCALE))
        self.image = Image.composite(Image.new("RGB", self.image.size, (0, 0, 0)), self.image, layer)
        self.draw = ImageDraw.Draw(self.image)

    def save(self, path):
        self.image.resize((self.width, self.height), Image.LANCZOS).save(path, optimize=True)


def board(position, size, lastmove=None, flipped=False, arrows=()):
    import cairosvg

    svg = chess.svg.board(position, size=size * SCALE, lastmove=lastmove, flipped=flipped, coordinates=False,
                          arrows=list(arrows),
                          colors={"square light": "#e9edf2", "square dark": "#8197ad",
                                  "square light lastmove": "#ffd2c2", "square dark lastmove": "#f08a6c"})
    image = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8")))).convert("RGB")
    return image.resize((size * SCALE, size * SCALE), Image.LANCZOS)


_marks = {}


def mark(size, fish=WHITE, trap=ACCENT):
    key = (size, fish, trap)
    if key not in _marks:
        _marks[key] = _mark(size, fish, trap)
    return _marks[key]


def _mark(size, fish, trap):
    """The logo recoloured for dark backgrounds, cropped to its content, as RGBA."""
    logo = Image.open(LOGO).convert("RGBA")
    pixels = logo.load()
    out = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    target = out.load()
    for y in range(logo.height):
        for x in range(logo.width):
            r, g, b, a = pixels[x, y]
            if a < 10:
                continue
            luminance = 0.3 * r + 0.59 * g + 0.11 * b
            if luminance > 225:
                continue  # white cut-outs stay transparent
            colour = fish if luminance < 75 else trap
            target[x, y] = colour + (a,)
    out = out.crop(out.getbbox())
    ratio = size * SCALE / max(out.size)
    return out.resize((max(1, int(out.width * ratio)), max(1, int(out.height * ratio))), Image.LANCZOS)


def wordmark(canvas, xy, size=34, mark_size=None):
    x, y = xy
    mark_size = mark_size or int(size * 1.5)
    canvas.paste(mark(mark_size), (x, y - mark_size * 0.08))
    canvas.text((x + mark_size + 12, y + mark_size * 0.36), "trickfish", "InterDisplay-Bold", size, WHITE,
                anchor="lm")
