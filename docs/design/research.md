# Trickfish design research and creative direction

Scope: daily X cards (1080x1350 question and answer), Gumroad covers and thumbnails, the X avatar and the X banner.
Both earlier attempts were rejected as looking "AI generated": (1) a navy/coral glow with rounded cards, pills and Inter; (2) a black and white Swiss layout with Inter Display, huge tight numbers, hairlines, a flat grey board and one orange accent.

Note on method: the sandbox could only reach some websites. Most primary pages (uber.com, mckltype.com, itsnicethat.com, superside.com) could not be fetched, so many points below come from search-engine excerpts of those pages. Anthropic's article was read in full. Nothing below is presented as a direct quote unless it was confirmed.

---

## 1. The tells of AI-generated / "vibe-coded" design (2025-2026)

The sources agree on the cause. Models and template tools return the statistical median of their training data. Anthropic calls this "distributional convergence". Its own write-up says unguided output converges on "Inter fonts, purple gradients on white backgrounds, and minimal animations". Others blame Tailwind's indigo-leaning defaults, Inter being the default in many tools, and shadcn/Tailwind UI/Vercel templates being the layouts models pattern-match on.

Tells cited repeatedly across sources:

| Area | Tell |
|---|---|
| Type | Inter (also Geist, Roboto, Open Sans, Lato, system fonts). The "safest possible answer". Weightless headline copy ("Build faster. Ship smarter."). Default Tailwind size steps (12/14/16/18/24/30/36/48/60/72) instead of a deliberate scale. |
| Second-order defaults | Fonts that "anti-slop" prompts recommend have become tells themselves. Anthropic notes Claude converges on **Space Grotesk**. Its recommended list (Bricolage Grotesque, Playfair, JetBrains Mono, Newsreader) is now widely used by AI too. One 2026 source names **cream + serif + sage** as the new "tasteful default" tell. |
| Colour | Purple-to-blue or indigo gradients, "the single most recognizable AI tell". Neon palettes. Dark mode with decorative glow. Evenly distributed, timid palettes. |
| Surfaces | A card around every block, cards nested in cards. Soft grey drop shadows. Heavy uniform corner radius. Glassmorphism / "liquid glass" (Creative Boom lists "glass everything" among the trends creatives are sick of in 2026). |
| Furniture | Pill chips and badges, status dots everywhere, emoji or stock icons in tinted rounded squares, little progress bars. |
| Layout | A centered hero, a row of three identical icon cards, symmetric grids, too much padding, and the same section order every time. |
| Content | Placeholder names, generic copy, almost-right lettering, "Canva template with the details swapped in". |
| Concept | The underlying tell is that **no one made a decision**. There is no idea, so every choice is a default. Several sources warn that swapping one default for another default just recreates the problem. |

What this means for Trickfish: attempt 1 hit the colour, surface and furniture tells. Attempt 2 dodged those but landed on the 2025-26 "tasteful minimal" default: Inter Display, hairlines, one accent and a neutral grey board. It had no idea specific to Trickfish, so it could have been any fintech or AI-startup stat card.

## 2. What separates top human brand design

- **An idea first, then styling.** Michael Bierut (Pentagram) describes taking an idea and stripping the decoration out "but still allowed it to communicate". His MAD museum identity grew from one observed fact, a continuous slot through the building. Trickfish needs one equivalent fact (see section 6).
- **Distinctive brand assets, repeated.** Jenni Romaniuk (Ehrenberg-Bass) defines distinctive assets as non-name cues that identify the brand. They are scored on *fame* and *uniqueness*, and she says they "do not become assets overnight" because they need reinforcement over time. An Ipsos/JKR study found only about 15% of brand assets are truly distinctive. Implication: pick 2-3 ownable devices and use them on every single card.
- **Committed choices.** Anthropic's own guidance says to use one distinctive font "decisively", to put dominant colour against sharp accents rather than timid even palettes, to use extreme weight contrast (100/200 vs 800/900), and to make size jumps of 3x or more.
- **Texture and the hand.** Creative Bloq's 2026 trend report frames the year around rejecting AI's hyper-polish in favour of work "unmistakably made by human hands". Stills and Creative Boom point to scrapbook and scanner aesthetics. Canva reported a 30% rise in searches for tactile textures. Use these as tools in service of the idea, not as a filter laid over everything.
- **Product and brand as one system.** Revolut's Gareth Morgan argues customers do not separate the app from the ad (per a Superside webinar recap). For Trickfish, the PDF interior, the covers and the X cards must share one visual language.

## 3. Uber and Revolut: why they feel premium and human

**Uber (2018, Wolff Olins + Uber in-house + Jeremy Mickel/MCKL)**
- It replaced the widely criticised 2016 "bit and atom" system with a plain black-and-white wordmark, set in a custom typeface, **Uber Move**. Mickel drew the typeface and the logo at the same time.
- Uber Move came from **transport signage research**: Highway Gothic and DIN. It was meant to feel friendlier than the previous Clan Pro, signalling safety and accessibility rather than "bravado" (Fast Company). The typeface itself is the brand's voice, so there is no decoration to hold up.
- The system has 9 elements: logo, composition, typography, iconography, colour, motion, photography, illustration and tone of voice. Black and white are primary. "Safety blue" is used *sparingly* for support moments. Illustration was reduced to basic geometric shapes in block colour.
- The human part is **photography of real people, places and drivers**, localised per region. Transform magazine credits the photography with adding "humanity". Key lesson: the restraint is premium because a *custom* typeface and *real* imagery carry it. Restraint built on Inter with stock content reads as a template, and that is exactly why attempt 2 failed.

**Revolut**
- Brand typeface: **Aeonik Pro** (CoType), a geometric grotesk with quirks, listed on Fonts In Use. The 2020 in-house refresh kept the "R" and changed the brand colour. Third-party token sites treat a near-black (about #191C1F) as the structural colour, with white type and accents used sparingly. These hex values are unofficial.
- Morgan describes illustration maturing **from cute, toy-like 3D to photorealistic renders**, and photography moving from youthful lifestyle shots to considered portraits. His stated stance is to stop doing competitor analyses and build a brand too specific to copy.
- Lesson: premium comes from **material realism** (metal cards, coins, renders lit like product photography), confident large type in one face, and dark surfaces with *no glow*. Revolut's darkness is lit like a photograph, while AI darkness is lit like a nightclub.

## 4. Chess brands and creators on social

- **Lichess** deliberately keeps "absence of design": a clean, no-frills interface focused on the board. It is honest and trusted, but it is not a brand voice to copy.
- **Chess.com** builds equity around the green pawn. The pawn was chosen as the weakest piece, the symbol of every player's starting point. Its brand resources ship the pawn as a standalone asset. That is one simple, repeated device.
- **World Chess** (Pentagram, 2012) is pure black and white, the colours of the pieces and of opposition, with an optical-illusion board mark that has lasted. **Shuka's 2018 identity** (Gerbera + a Rockwell-style geometric slab, chessboard graphics, streetwear energy) was the "most talked about design in chess". It was also controversial and was later dropped. Lesson: a provocative concept gets attention, and a cheap joke has a short shelf life.
- **Puzzle posts** are reliably high-engagement on chess X. Chessify's daily mate-in-2 posts reach hundreds of thousands of views by asking a question and holding back the solution. Chess.com analysis suggests puzzle/lesson content out-engages other instructional genres. Trickfish's question/answer pair is the right format.
- **Creators (GothamChess etc.)** are known for clickbait thumbnails. Even fans in r/chess threads find them off-putting. A 507k-video vendor study found 62% of breakout thumbnails use all-caps text and only 6.3% repeat the title. Lesson for Trickfish: the card text should *add* to the post copy, not repeat it.
- **Data journalism is the closest model for a "stat + position" card.** The FT built a social-specific black-background chart style, and people save those posts. The Economist leans on witty titles. Both always show the source, because images travel without context.
- **Format caveat:** guides disagree on whether X shows 4:5 uncropped in every view. Keep everything essential inside a centred 1080x1080 safe zone of the 1080x1350 canvas.

## 5. Typeface candidates (all SIL OFL 1.1, all verified on npm as `@fontsource/<name>` v5.3.x)

| Package | Why it fits Trickfish |
|---|---|
| `@fontsource/redaction` (+ `redaction-10/20/35/50/70/100`) | Drawn by **Jeremy Mickel (MCKL), the same designer as Uber Move**, for Titus Kaphar and Reginald Dwayne Betts' *Redaction* project. A legal-brief serif with seven grades of fax/photocopy degradation. It has real provenance and texture, and almost no AI output uses it. |
| `@fontsource/big-shoulders-display` | Patric King's condensed American Gothic, made for the Chicago Design System. Civic signage lineage, like Uber Move's DIN/Highway Gothic roots. Huge, tall numerals for statistics. |
| `@fontsource/schibsted-grotesk` | An editorial grotesk from Scandinavian newspaper heritage. A grown-up body/UI face with more voice than Inter. |
| `@fontsource/familjen-grotesk` | From the Stockholm ad agency Familjen. A grotesk with quirky, slightly ink-trapped details. Good for headlines that need personality without shouting. |
| `@fontsource/martian-mono` | Evil Martians, 2023. Has a width axis and a tall x-height, and suits notation (1.e4 e5 2.Nf3) and data labels. A fresher choice than JetBrains/Space Mono. |
| `@fontsource/ibm-plex-mono` / `ibm-plex-sans-condensed` | A corporate-engineering voice, good for "verified by Stockfish" data captions. |
| `@fontsource/libre-caslon-text` / `@fontsource/young-serif` | A book-printing serif for a "chess book" register. Use Caslon for text and Young Serif for warm display. |
| `@fontsource/gloock` | A high-contrast display serif for one big number per card. |
| `@fontsource/noto-sans-symbols-2` | Chess glyphs (U+2654-265F) for figurine notation (♘f3) in captions. |

Avoid as primary voice: Inter, Inter Display/Tight, Geist, Space Grotesk, Bricolage Grotesque, Playfair Display, Instrument Serif, Manrope, Sora, Syne and Unbounded. They are either defaults or the anti-default defaults.

## 6. Creative direction

**The core fact to build on.** In chess a *line* is a sequence of moves, and in fishing a *line* is what the hook hangs from. A *fish* is chess slang for a weak player, and Stockfish is the engine that verifies every trap. A Trickfish trap is literally bait, a bite and a hook, set by thousands of real 1200-1599 players. Every route below expresses part of that. Recommendation: **Route A**, using the redaction-bar mechanic from Route B for the question cards if wanted.

### Route A: "Line & Hook" (recommended)
- **Idea:** every trap is drawn as a fishing line. The punishing sequence is one continuous drawn stroke across the board that ends in a hook on the decisive square.
- **Type:** Young Serif or Gloock for the one big number. Schibsted Grotesk for text. Martian Mono for notation and data. Figurines from Noto Sans Symbols 2.
- **Palette:** Bait paper `#EEEAE0`, Ink `#15130F`, Hook red `#C4161C` (used only for the line and the hook), Water `#1F3A44` (cover backgrounds and the dark avatar), Bobber white `#FFFFFF`. No gradients.
- **Board:** treated as a *printed book diagram*. Light squares are paper. Dark squares are **hatched** in ink with diagonal lines, as in classic printed diagrams, not grey fills. Use classic diagram piece silhouettes. Draw a thin ink frame with file and rank letters in Martian Mono. The red line is drawn with slight hand irregularity (variable stroke width, a rounded nib), never as a perfect arrow.
- **Layout:** an asymmetric, editorial page. The board sits big and offset to one side. The statistic is set like a caption in a field guide ("65% bite here. n = 3,412 Lichess games, 1200-1599"). Leave generous empty paper space; use no boxes. The answer card uses the same position plus the hook line. The mistake is named in plain words and the punishment line is printed in figurine notation.
- **Ownable devices:** the hook glyph (also the avatar: a red hook on Water), the hatched board, and red appearing *only* as line. Pack covers read like angling-catalogue plates ("Plate 03 - The Fishing Pole, Ruy Lopez").

### Route B: "Case File"
- **Idea:** traps are crimes committed against real players. Stockfish is the forensic lab, and the Lichess database is the evidence.
- **Type:** Redaction (grades 35-70 for headlines, 100 for text) + Martian Mono for evidence numbers and notation.
- **Palette:** Photocopy white `#F4F3EF`, Toner black `#0D0D0D`, Highlighter yellow `#FFE24A` (marks the punishing move), Stamp red `#D9231D` (verdict stamps only).
- **Board:** a photocopied diagram with toner grain, a slight skew of at most 0.5 degrees, and real paper texture. On the **question card the losing move is covered by a black redaction bar**. The answer card is "declassified": the bar is lifted and the move is highlighted in yellow.
- **Layout:** document logic. An exhibit number, a case header in mono, and the stat written as a finding ("Exhibit 14. 2,207 of 3,412 players played 6...Bg4?"). Use typewriter-style left alignment, and put red stamps at an angle.
- **Ownable devices:** the redaction bar (also usable as the avatar: a black bar with a small red hook), the degraded type and the exhibit numbering. Risk: it becomes a costume. Keep props to the bar, the stamp and grain; no paper clips, coffee rings or folders.

### Route C: "Opening Lines" (closest to Uber)
- **Idea:** openings are transit lines. Each opening family has a line colour, and every trap is a stop on that line.
- **Type:** Big Shoulders Display (800-900) for numbers and titles, Familjen Grotesk for text, and Martian Mono for notation. Set big, flush left, signage-tight but optically kerned.
- **Palette:** Signal black `#0B0B0B`, White `#FFFFFF`, and line colours for whole fields: Ruy Lopez `#D0202E`, Italian `#00875A`, Sicilian `#1D4FD8`, Queen's Gambit `#F2B705`, London `#6B3FA0`. Each card is one solid full-bleed line colour, plus black and white.
- **Board:** monumental and **cropped**. Show only the 4x4 or 5x5 region where the trap happens, bleeding off the canvas edge. Use flat two-tone squares in tints of the line colour, black and white piece silhouettes, and one heavy signage arrow for the key move.
- **Layout:** wayfinding. A line badge (a coloured disc with a short code like "RL-03"), a big number on a strict 6-column grid, and source data set in mono at the bottom like a timetable.
- **Ownable devices:** the line-colour system (pack covers become a collectible "network map"), the cropped board and the line codes. Risk: the flat colour fields look template-like if the crop and type are timid. The board must be cropped boldly every time.

## 7. Self-review checklist (apply mechanically)

**DON'T**
1. Don't use Inter, Inter Display, Geist, Roboto, Space Grotesk, Bricolage, Playfair, Instrument Serif or system fonts anywhere.
2. Don't use any gradient, glow, bloom, neon, glassmorphism, blur panel or soft drop shadow.
3. Don't put content in rounded cards. Use no border-radius above 2px except on genuinely round objects (a disc badge, a hook).
4. Don't use pill chips, tags, badges-as-decoration, status dots or emoji, and no icons in tinted squares.
5. Don't centre-stack the layout (centered title, centered board, centered number). Use an asymmetric composition anchored to a grid edge.
6. Don't use a flat grey or default-coloured board (no Lichess brown, no Chess.com green). The board must follow the chosen route's treatment.
7. Don't use more than 2 typefaces plus 1 mono, more than 3 sizes per card, or more than one accent colour outside the route's spec.
8. Don't decorate with a colour. Every accent pixel must mean something: the move, the line, the hook, the verdict.
9. Don't write generic copy ("Level up your chess", "Master openings"). Every card names a specific move, a specific opening and a specific number with its sample size.
10. Don't repeat the post text on the card, and don't use clickbait shouting (no all-caps "INSANE TRAP", no arrows pointing at faces).
11. Don't apply texture as a uniform filter. Grain or hatching belongs to an object (paper, toner, diagram), not to the whole frame at random.
12. Don't ship a card without the data source line (sample size, rating band, "Stockfish verified").

**DO**
1. State the route's one-line idea before designing. If a card does not express it, redo the card.
2. Use the same 2-3 ownable devices on every card, cover, avatar and banner.
3. Make one element dominant per card (the board *or* the number), with a size jump of at least 3x to the next element.
4. Use extreme weight contrast (for example 300 against 800), with optical kerning on display sizes and tight but not crushed leading (0.9-1.0 for numbers, 1.3-1.4 for text).
5. Set chess moves in notation in the mono or with figurines, never in the body face.
6. Keep everything critical inside the centred 1080x1080 safe zone of the 1080x1350 canvas.
7. Make question and answer cards an obvious pair: same position, same grid, with only the reveal added.
8. Take the "screenshot test": with the logo hidden, could this be any other brand's card? If yes, it fails.
9. Take the "median test": if an unprompted AI would plausibly produce this exact layout, change the composition, not just the colour.
10. Render once at 100% and once as a 300px thumbnail. The board position and the number must still read at thumbnail size.

---

## Sources

- Anthropic, "Improving frontend design through Skills": https://claude.com/blog/improving-frontend-design-through-skills
- Why your AI keeps building the same purple gradient website: https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website
- 925 Studios, AI slop fonts and gradients: https://www.925studios.co/blog/ai-slop-design-tells
- The Fountain Institute, 7 signs a UI has been vibe coded: https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui
- MakeUseOf on vibe-coded UI tells: https://www.makeuseof.com/vibe-code-only-trust-these-models-ui-design/
- Yuwen Lu, Signs of vibe coded UI: https://x.com/yuwen_lu_/article/2041187936738447565
- Superdesign, why AI design looks generic: https://www.superdesign.dev/blog/why-ai-design-looks-generic
- CodeMySpec, vibe-coded websites look the same: https://codemyspec.com/blog/vibe-coded-websites-look-the-same
- noqta, AI design slop patterns 2026: https://noqta.tn/en/blog/ai-design-slop-overused-ui-patterns-fix-2026
- Pixelslop AI slop pattern catalog: https://cdn.jsdelivr.net/npm/pixelslop@0.3.8/dist/skill/resources/ai-slop-patterns.md
- Design Systems Collective, tired of every Tailwind/shadcn app: https://www.designsystemscollective.com/is-anyone-else-tired-of-every-tailwind-shadcn-app-looking-the-same-69c545e73114
- dev.to, fixing the AI-generated look: https://dev.to/alanwest/how-to-fix-the-ai-generated-look-in-your-frontend-1ahh
- Hacker News, AI posters / Canva look: https://news.ycombinator.com/item?id=49764791
- Creative Boom, 10 trends creatives are over in 2026: https://www.creativeboom.com/insight/10-trends-creatives-are-so-over-in-2026/
- Creative Bloq, 2026 graphic design trends (texture, tactile rebellion): https://www.creativebloq.com/design/graphic-design/texture-warmth-and-tactile-rebellion-the-big-graphic-design-trends-for-2026
- Creative Boom, Stills 2026 trends report: https://creativeboom.com/insight/stills-trends-report-demonstrates-how-bold-human-centred-design-is-defining-2026
- Michael Bierut advice (Design Week / Azure): https://www.designweek.co.uk/how-to-be-michael-bierut/ , https://www.azuremagazine.com/article/michael-bierut-designthinkers-2018/
- Romaniuk / distinctive brand assets: https://marketingscience.info/building-distinctive-brand-assets/ , https://www.thedrum.com/news/2025/10/06/mark-ritson-we-know-what-distinctive-marketing-looks-now-let-s-agree-what-call-it
- Dezeen, Uber rebrand by Wolff Olins: https://www.dezeen.com/2018/09/14/uber-rebrand-wolff-olins-black-white-wordmark-logo-typography/amp/
- Fast Company, Uber has a new brand again: https://www.fastcompany.com/90235065/uber-has-a-new-brand-again
- Creative Bloq, Uber new logo: https://www.creativebloq.com/news/uber-hails-its-new-logo
- Uber Design, inspiration behind the 2018 redesign: https://www.uber.com/careers/design/work/2018-redesign
- Uber 2018 partner brand guide (PDF): https://cdn.shopify.com/s/files/1/0565/3423/7349/files/Uber_2018.pdf
- MCKL, Uber Move: https://mckltype.com/custom/uber
- Transform magazine, Uber's brand: https://www.transformmagazine.net/articles/2018/ubers-brand-is-always-on-the-move/
- Design Week, Uber rebrand 2018: https://www.designweek.co.uk/issues/17-23-september-2018/uber-rebrand-looks-to-reflect-how-the-taxi-app-is-changing
- Grapheine, Uber 2016 bit and atom: https://grapheine.com/en/magazine/new-logo-uber-2018/
- Superside, How Revolut built an uncopyable brand (Gareth Morgan): https://www.superside.com/blog/uncopyable-brand
- Fonts In Use, Revolut (Aeonik Pro): https://www.fontsinuse.com/uses/61484/revolut
- Revolut brand guidelines summary: https://madegooddesigns.com/revolut-brand-guidelines/
- Kate Trofimova, Revolut 3D illustration system: https://kate-trofimova.com/projects/revolut-3d
- Lichess v2 is here: https://lichess.org/blog/XMvcJSwAADkA0hPE/lichess-v2-is-here
- Chess.com logo story: https://chess.com/blog/erik/the-chess-com-logo-story ; brand resources: https://www.chess.com/article/view/chess-com-brand-resources
- Pentagram, World Chess: https://www.pentagram.com/work/world-chess
- It's Nice That, Shuka on World Chess: https://www.itsnicethat.com/articles/we-had-no-other-choice-but-to-make-it-exciting-shuka-on-its-radical-re-brand-of-world-chess
- Fonts In Use, World Chess (Shuka): https://www.fontsinuse.com/uses/21645/world-chess
- Chessify, best chess puzzles from Twitter: https://chessify.me/blog/best-chess-puzzles-from-twitter
- Eden, 507,478-thumbnail study: https://eden.so/blog/what-makes-a-good-youtube-thumbnail/
- Digiday, FT Instagram strategy: https://digiday.com/media/inside-financial-times-instagram-strategy/
- Medium, Lessons for showcasing data journalism on social media (Economist): https://medium.com/severe-contest/lessons-for-showcasing-data-journalism-on-social-media-17e6ed03a868
- Tableau, charts for social media: https://www.tableau.com/blog/6-tips-to-design-charts-for-social-media
- Edward Winter, Chess diagrams: https://www.chesshistory.com/winter/extra/diagrams.html
- X image sizes (conflicting guidance): https://influencermarketinghub.com/twitter-image-size/ , https://recurpost.com/schedule-tweets/twitter-post-dimensions/
- AIGA Eye on Design, Redaction typeface: https://eyeondesign.aiga.org/a-typeface-inspired-by-legal-briefs-that-challenges-the-justice-system/
- Fontsource, Redaction: https://fontsource.org/fonts/redaction/about
- Fontsource, Big Shoulders Display: https://fontsource.org/fonts/big-shoulders-display/about
- Martian Mono (Sessions): https://www.sessions.edu/notes-on-design/free-font-friday-martian-mono/
- Familjen Grotesk / Schibsted Grotesk: https://fontalternatives.com/fonts/familjen-grotesk/ , https://fontalternatives.com/fonts/schibsted-grotesk/
- npm registry (package/licence check): https://registry.npmjs.org/@fontsource/redaction/latest
