"""The sound layer for the videos, synthesised from scratch with numpy: no samples, nothing
downloaded, nothing copyrighted. Quiet, short, tactile sounds placed on the video's event
timeline (see video.build), mixed to 48 kHz stereo and set by one static gain (no compressor, no ambient bed: the gaps between events are silent)."""
import json
import pathlib
import re
import subprocess
import wave

import numpy as np

SR = 48000
TARGET_LUFS, TRUE_PEAK = -19.0, -2.0   # static: peak -2 dBTP before the AAC encode keeps the file under -1 dBTP


def _t(seconds):
    return np.arange(int(seconds * SR)) / SR


def _shape(x, attack=0.001, release=0.006):
    """Short fades on both ends so no sound can click."""
    a, r = max(2, int(attack * SR)), max(2, int(release * SR))
    x = x.copy()
    x[:a] *= np.linspace(0, 1, a)
    x[-r:] *= np.linspace(1, 0, r)
    return x


def _band_noise(seconds, centre, width, rng):
    """Noise band-passed around `centre` Hz (gaussian window in the spectrum), unit peak."""
    n = int(seconds * SR)
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spectrum *= np.exp(-0.5 * ((freqs - centre) / width) ** 2)
    x = np.fft.irfft(spectrum, n)
    return x / (np.abs(x).max() + 1e-9)


def tock(rng, heavy=False):
    """Wooden tock: band-passed noise burst, fast exponential decay, plus a low body thump."""
    length = 0.09 if heavy else 0.06
    t = _t(length)
    centre, tau, body_hz, gain = (1100, 0.016, 110, 1.0) if heavy else (1900, 0.010, 170, 0.8)
    click = _band_noise(length, centre * rng.uniform(0.96, 1.04), centre * 0.45, rng) * np.exp(-t / tau)
    hz = body_hz * (1 + 0.5 * np.exp(-t / 0.008))
    body = np.sin(2 * np.pi * np.cumsum(hz) / SR) * np.exp(-t / (0.026 if heavy else 0.018))
    return _shape(gain * (0.75 * click + (0.65 if heavy else 0.4) * body), 0.0008, 0.012)


def check_tick(rng):
    t = _t(0.03)
    x = _band_noise(0.03, 3300, 900, rng) * np.exp(-t / 0.005)
    x += 0.5 * np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.006)
    return 0.5 * _shape(x, 0.0005, 0.008)


def blip():
    """Countdown: a soft, short high blip."""
    t = _t(0.085)
    x = np.sin(2 * np.pi * 1480 * t) + 0.18 * np.sin(2 * np.pi * 2960 * t)
    x *= np.exp(-t / 0.026)
    return 0.8 * _shape(x, 0.004, 0.02)


def ratchet(seconds, rng):
    """Fishing reel: soft clicks whose rate rises a little over the line's growth.
    Returns a stereo (2, n) array; clicks alternate slightly left and right."""
    n = int(seconds * SR) + int(0.03 * SR)
    out = np.zeros((2, n))
    at, i = 0.0, 0
    while at < seconds:
        progress = at / max(seconds, 1e-6)
        rate = 26 + 12 * progress
        t = _t(0.012)
        c = _band_noise(0.012, 3800 * rng.uniform(0.9, 1.1), 1400, rng) * np.exp(-t / 0.0028)
        c += 0.5 * np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.004)
        c = _shape(c, 0.0004, 0.004) * 0.5 * rng.uniform(0.75, 1.0)
        pan = 0.5 + (0.12 if i % 2 else -0.12)
        s = int(at * SR)
        out[0, s:s + len(c)] += c * (1 - pan) * 1.4
        out[1, s:s + len(c)] += c * pan * 1.4
        at += 1 / rate * rng.uniform(0.92, 1.08)
        i += 1
    # a tiny fade at either end of the whole run
    f = int(0.004 * SR)
    out[:, :f] *= np.linspace(0, 1, f)
    return out


def tink_thud():
    """Hook landing: a small metallic tink with a short tail, plus a low thud."""
    length = 0.45
    t = _t(length)
    tink = np.zeros_like(t)
    for ratio, amp, tau in ((1, 1.0, 0.11), (2.76, 0.55, 0.07), (5.4, 0.3, 0.04), (8.9, 0.14, 0.02)):
        tink += amp * np.sin(2 * np.pi * 2350 * ratio * t) * np.exp(-t / tau)
    tink *= 0.3
    thud_t = t[:int(0.16 * SR)]
    thud = np.sin(2 * np.pi * np.cumsum(62 * (1 + 0.6 * np.exp(-thud_t / 0.02))) / SR) * np.exp(-thud_t / 0.05)
    tink[:len(thud)] += 0.3 * thud
    return _shape(tink, 0.0008, 0.12)


def chord(seconds):
    """End card: a gentle, warm three-note chord (C major add 9 spread: C4, E4, G4), lightly staggered."""
    t = _t(seconds)
    out = np.zeros_like(t)
    for i, hz in enumerate((261.63, 329.63, 392.0)):
        d = int(i * 0.045 * SR)
        tt = t[:len(t) - d]
        x = (np.sin(2 * np.pi * hz * tt) + 0.25 * np.sin(2 * np.pi * 2 * hz * tt) + 0.06 * np.sin(2 * np.pi * 3 * hz * tt))
        x *= np.minimum(1, tt / 0.03) * np.exp(-tt / 0.9)
        out[d:] += x / 3
    return 0.75 * _shape(out, 0.03, 0.25)


def _put(mix, mono, at, gain=1.0, pan=0.5):
    s = int(round(at * SR))
    if s >= mix.shape[1]:
        return
    mono = mono[:mix.shape[1] - s]
    mix[0, s:s + len(mono)] += mono * gain * (1 - pan) * 2 ** 0.5 * 0.7071
    mix[1, s:s + len(mono)] += mono * gain * pan * 2 ** 0.5 * 0.7071


def mix(events, seconds, seed=7):
    """Float stereo (2, n) mix of the events, peak about 0.8, no DC. Events: [{"type", "t"}, ...]."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = np.zeros((2, n))
    for e in events:
        k, at = e["type"], e["t"]
        if k == "tick":
            _put(out, blip(), at)
        elif k == "move":
            _put(out, tock(rng), at, 0.8, 0.5 + rng.uniform(-0.04, 0.04))
        elif k == "capture":
            _put(out, tock(rng, True), at, 0.8, 0.5)
        elif k == "check":
            _put(out, check_tick(rng), at + 0.09, 1.0, 0.56)
        elif k == "hook":
            _put(out, tink_thud(), at, 1.0, 0.5)
        elif k == "end_card":
            _put(out, chord(max(0.5, seconds - at - 0.02)), at, 1.0, 0.5)
    for a, b in zip([e for e in events if e["type"] == "line_start"], [e for e in events if e["type"] == "line_end"]):
        r = ratchet(max(0.05, b["t"] - a["t"]), rng)
        s = int(a["t"] * SR)
        r = r[:, :n - s]
        out[:, s:s + r.shape[1]] += r
    out -= out.mean(axis=1, keepdims=True)
    peak = np.abs(out).max()
    return out * (0.8 / peak) if peak > 0 else out


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1).T * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def true_peak_and_lufs(wav):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, check=True).stderr
    summary = r[r.rindex("Summary"):]
    return (float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1)),
            float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1)))


def mux(video, wav, out):
    """One static linear gain so the true peak sits at TRUE_PEAK, then AAC 192k stereo 48 kHz;
    the video stream is copied."""
    peak, _ = true_peak_and_lufs(wav)
    gain = TRUE_PEAK - peak
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                    "-af", "volume=%.3fdB" % gain, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-ac", "2", "-movflags", "+faststart", "-shortest", str(out)], check=True)
