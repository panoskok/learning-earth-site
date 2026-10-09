#!/usr/bin/env python3
"""
The Learning Earth: static site generator.

Run from anywhere:   python3 _src/build.py
Reads:   _src/content/*.md  (articles) + the registry below
Writes:  index.html, book/, articles/, about/, newsletter/, 404.html, one folder per article,
         sitemap.xml, robots.txt, .htaccess, assets/og/*.jpg   (all at the repo root)

To publish an article:  set its status to "published" in PAGES, run the build, commit.
Draft pages are built into _drafts/ (noindex, blocked in robots.txt and .htaccess).
"""
import datetime
import html
import json
import re
import shutil
import sys
import textwrap
from pathlib import Path

import markdown
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "_src" / "content"
SITE = "https://thelearningearth.com"
SITE_NAME = "The Learning Earth"
AUTHOR = "Panagiotis Kokkorogiannis"
SUBTITLE = "A Philosophical Framework for Life, Consciousness and Memory"
TODAY = "2026-10-10"
WORK_BG = ROOT / "_src" / "og-bg"  # backgrounds for the social-preview (OG) cards

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
PILLARS = [
    dict(key="earth", slug="earth-as-a-learning-system", label="Earth as a Learning System",
         blurb="Life did not only adapt to the planet; it rebuilt it. What can “learning” rigorously mean at planetary scale?"),
    dict(key="chi", slug="chi", label="Chi, Reframed",
         blurb="Chi as a process, not a substance: the flow of organization, and what the primary texts actually describe."),
    dict(key="sources", slug="sources", label="Ancient Sources, Modern Lens",
         blurb="The primary texts on qi, prana and pneuma: what each says, when it was written, and how translation bends it."),
    dict(key="science", slug="science", label="The Science of Organization",
         blurb="The scientific anchors of the book: what each establishes, what it does not support, and where the philosophy begins."),
]
PILLAR = {p["key"]: p for p in PILLARS}

# status: published | draft | planned
PAGES = [
    dict(path="/earth-as-a-learning-system/", pillar="earth", kind="cornerstone", status="published",
         file="earth-as-learning-system-cornerstone.md",
         hero="earth-learning-system", og_bg="bg_earth.jpg",
         alt="Layered strata spiral outward from a tree-root trunk, carrying fossils and rivers toward a translucent human figure and a modern landscape.",
         caption="Layers of retention: each stage keeps what the one before it learned.",
         meta="Life did not just adapt to Earth; it rebuilt it. What can “learning” rigorously mean for a planet? A systems engineer’s introduction."),
    dict(path="/chi/", pillar="chi", kind="cornerstone", status="published",
         file="what-is-chi-cornerstone.md",
         hero="chi-pattern-and-material", og_bg="bg_chi.jpg",
         alt="Grey particles enter from the left, pass through a standing teal pattern at the centre, and leave on the right as orange particles. The pattern persists while the material is replaced.",
         caption="The pattern persists; the material turns over.",
         meta="Chi is usually called a mysterious life energy. A systems engineer argues it is the flow of organization: a process, not a substance."),
    dict(path="/sources/", pillar="sources", kind="cornerstone", status="published",
         file="ancient-texts-vital-energy-cornerstone.md",
         hero="sources-qi", og_bg="bg_sources.jpg",
         alt="The Chinese character qi (氣) in large type, with the titles Neiye, Mencius and Huangdi Neijing in Chinese beneath it.",
         caption=None,
         meta="A reader’s guide to the primary sources on qi, prana and pneuma: dates, what each text says, and why standard translations distort it."),
    dict(path="/science/", pillar="science", kind="cornerstone", status="draft",
         file="science-behind-learning-earth-cornerstone.md",
         hero="science-energy-flow", og_bg="bg_science.jpg",
         alt="A stream of coloured light flows from the Sun to Earth and spreads across a living landscape.",
         caption="Energy flowing through a system held away from equilibrium.",
         meta="The five scientific anchors of The Learning Earth: what each establishes, what it does not support, and where the philosophy begins."),
    # planned clusters (become real pages when a markdown file + status are added)
    dict(path="/earth-as-a-learning-system/dissipative-structures-explained/", pillar="earth", kind="cluster", status="planned",
         title="Dissipative Structures Explained: How Order Arises from Energy Flow"),
    dict(path="/earth-as-a-learning-system/complex-adaptive-systems-101/", pillar="earth", kind="cluster", status="planned",
         title="Complex Adaptive Systems 101: Ants, Immune Systems and Ecosystems"),
    dict(path="/chi/chi-vs-qi/", pillar="chi", kind="cluster", status="planned",
         title="Chi vs. Qi: Same Word, Different Spelling, Different Meanings?"),
    dict(path="/chi/why-chi-is-not-a-substance/", pillar="chi", kind="cluster", status="planned",
         title="Why Chi Is Not a Substance"),
    dict(path="/chi/acupuncture-and-neurophysiology/", pillar="chi", kind="cluster", status="planned", listed=False,
         title="Acupuncture and Neurophysiology"),
    dict(path="/sources/neiye/", pillar="sources", kind="cluster", status="planned",
         title="The Neiye (Inward Training): Translation and Commentary"),
    dict(path="/sources/mencius-haoran-zhi-qi/", pillar="sources", kind="cluster", status="planned",
         title="Mencius and Haoran Zhi Qi: The “Flood-Like Qi”"),
    dict(path="/sources/huangdi-neijing/", pillar="sources", kind="cluster", status="planned",
         title="The Huangdi Neijing: Inner Canon of the Yellow Emperor"),
    dict(path="/sources/enuma-elish/", pillar="sources", kind="cluster", status="planned",
         title="Enūma Eliš and the Emergence of Order"),
    dict(path="/sources/breath-traditions/", pillar="sources", kind="cluster", status="planned",
         title="Pneuma, Prana and the Breath Traditions"),
    dict(path="/science/michael-levin-bioelectricity/", pillar="science", kind="cluster", status="planned",
         title="Michael Levin’s Bioelectricity, Explained for Non-Biologists"),
    dict(path="/science/landauer-principle/", pillar="science", kind="cluster", status="planned",
         title="Landauer’s Principle: Why Erasing Information Costs Energy"),
]
BY_PATH = {p["path"]: p for p in PAGES}

# Placeholder links "[text](#)" in the markdown are resolved through this map.
LINKMAP = {
    "Sources Library": "/sources/",
    "What Is Chi?": "/chi/",
    "Michael Levin's Bioelectricity, Explained for Non-Biologists": "/science/michael-levin-bioelectricity/",
    "a separate piece": "/chi/acupuncture-and-neurophysiology/",
    "The Science Behind The Learning Earth": "/science/",
    "Dissipative Structures Explained": "/earth-as-a-learning-system/dissipative-structures-explained/",
    "Read the Neiye guide": "/sources/neiye/",
    "Read the Mencius guide": "/sources/mencius-haoran-zhi-qi/",
    "Read the Huangdi Neijing guide": "/sources/huangdi-neijing/",
    "Read the Enūma Eliš guide": "/sources/enuma-elish/",
    "Read the breath traditions overview": "/sources/breath-traditions/",
    "what systems science says about how organization accumulates": "/earth-as-a-learning-system/",
    "what bioelectric research has found about information in living tissue": "/science/michael-levin-bioelectricity/",
    "The Earth as a Learning System": "/earth-as-a-learning-system/",
    "Landauer's Principle: Why Erasing Information Costs Energy": "/science/landauer-principle/",
    "chi, understood as the flow of organization": "/chi/",
    "the ancient sources": "/sources/",
}

NAV = [("/book/", "The Book"), ("/articles/", "Articles"), ("/sources/", "Sources Library"),
       ("/about/", "About"), ("/newsletter/", "Newsletter")]

BOUNDARY_IDS = ("where-the-boundary-sits", "where-the-science-ends", "on-convergence-and-what-it-does-not-prove")

BOOK_TOC = [
    ("Prologue", "A Body That Refused to Lie"),
    ("Chapter 1", "The Cosmic Window"),
    ("Chapter 2", "The Sun That Holds, the Earth That Learns"),
    ("Chapter 3", "What the Cultures Knew"),
    ("Chapter 4", "What Science Finds"),
    ("Chapter 5", "Chi as the Flow of Organization"),
    ("Chapter 6", "A Planet That Learns"),
    ("Chapter 7", "The Emergence of Consciousness"),
    ("Chapter 8", "Consciousness Moves Chi"),
    ("Chapter 9", "Nothing Is Lost"),
    ("Chapter 10", "We Are the Earth Thinking"),
    ("Chapter 11", "Evil, Pain and Complexity"),
    ("Chapter 12", "The Ethic of Recognition"),
    ("Chapter 13", "Where Are We Going?"),
    ("Epilogue", "The Body Knew First"),
    ("Appendix", "The Five Postulates of the Framework"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
esc = html.escape


def human_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def url(path):
    return SITE + path


def is_live(path):
    p = BY_PATH.get(path)
    return bool(p and p["status"] == "published")


def write(rel, text):
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def plain_text(h):
    return re.sub(r"<[^>]+>", " ", h)


def resolve_links(md):
    def sub(m):
        text = m.group(1)
        target = LINKMAP.get(text.replace("’", "'"))
        if target is None:
            sys.exit(f"BUILD ERROR: placeholder link with no mapping: [{text}](#)")
        if is_live(target):
            return f"[{text}]({target})"
        return f'<span class="soon" title="Coming soon">{text}</span>'
    return re.sub(r"\[([^\]]+)\]\(#\)", sub, md)


# ---------------------------------------------------------------------------
# Shared page furniture
# ---------------------------------------------------------------------------
FONT_PRELOAD = """<link rel="preload" href="/assets/fonts/fraunces-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>"""

MARK = ('<svg class="mark" viewBox="0 0 40 40" aria-hidden="true"><g stroke="#52DAC6" stroke-width="1.2" opacity=".8">'
        '<line x1="8" y1="12" x2="20" y2="7"/><line x1="20" y1="7" x2="32" y2="13"/><line x1="8" y1="12" x2="14" y2="27"/>'
        '<line x1="20" y1="7" x2="19" y2="25"/><line x1="32" y1="13" x2="27" y2="28"/><line x1="14" y1="27" x2="19" y2="25"/>'
        '<line x1="19" y1="25" x2="27" y2="28"/></g><g fill="#ECE8DE"><circle cx="8" cy="12" r="2"/><circle cx="32" cy="13" r="2"/>'
        '<circle cx="14" cy="27" r="1.7"/><circle cx="19" cy="25" r="1.7"/><circle cx="27" cy="28" r="1.7"/></g>'
        '<circle cx="20" cy="7" r="2.4" fill="#52DAC6"/></svg>')


def head(title, desc, path, og_image, schema=None, noindex=False, suffix=True, canonical_path=None):
    full = f"{title} | {SITE_NAME}" if suffix and len(title) + len(SITE_NAME) + 3 <= 62 else title
    canon = url(canonical_path or path)
    robots = '<meta name="robots" content="noindex, nofollow">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large">'
    ld = ""
    for obj in (schema or []):
        ld += f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>\n'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{canon}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0A0D12">
<meta property="og:type" content="{'website' if path == '/' else 'article'}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{url(og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{url(og_image)}">
{FONT_PRELOAD}
<link rel="stylesheet" href="/assets/style.css">
{ld}</head>
"""


def header(active=""):
    items = "".join(
        f'<li><a href="{p}"{" aria-current=\"page\"" if p == active else ""}>{esc(n)}</a></li>' for p, n in NAV)
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
<div class="wrap bar">
<a class="brand" href="/" aria-label="{SITE_NAME}, home">{MARK}<span>The Learning Earth</span></a>
<nav aria-label="Main"><ul>{items}</ul></nav>
</div>
</header>
"""


def footer():
    links = "".join(f'<a href="{p}">{esc(n)}</a>' for p, n in NAV)
    return f"""<footer class="site-footer">
<div class="wrap">
<div class="foot-top"><a class="brand" href="/">{MARK}<span>The Learning Earth</span></a><nav aria-label="Footer">{links}</nav></div>
<p class="foot-note">{SUBTITLE}. By {AUTHOR}.</p>
<p class="foot-legal">&copy; 2026 {AUTHOR}. Where this site marks a claim as interpretation rather than established science, the marking is deliberate.</p>
</div>
</footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


def notify_form(uid="f"):
    return f"""<form class="notify" data-endpoint="/subscribe.php" novalidate>
<label class="sr-only" for="email-{uid}">Email address</label>
<input type="email" id="email-{uid}" name="email" placeholder="you@email.com" autocomplete="email" required>
<button type="submit">Notify me</button>
<p class="form-note" role="status" aria-live="polite"></p>
<p class="form-fine">Your email is stored on this site’s own server and used only to tell you about the book.</p>
</form>"""


def breadcrumb(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": url(p)}
                                for i, (n, p) in enumerate(items)]}


# ---------------------------------------------------------------------------
# OG cards
# ---------------------------------------------------------------------------
def load_font(size, serif=True, bold=False):
    candidates = []
    if serif:
        candidates = ["/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else
                      "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"]
    else:
        candidates = ["/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def make_og(slug, kicker, title, bg_name):
    out = ROOT / "assets" / "og" / f"{slug}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = 1200, 630
    canvas = Image.new("RGB", (W, H), (10, 13, 18))
    if bg_name and (WORK_BG / bg_name).exists():
        bg = Image.open(WORK_BG / bg_name).convert("RGB")
        scale = max(W / bg.width, H / bg.height)
        bg = bg.resize((round(bg.width * scale), round(bg.height * scale)), Image.LANCZOS)
        left, top = (bg.width - W) // 2, (bg.height - H) // 2
        canvas = bg.crop((left, top, left + W, top + H))
    ov = Image.new("RGBA", (W, H))
    od = ImageDraw.Draw(ov)
    for x in range(W):
        a = int(max(0, min(235, 235 - (x / W) * 235 * 0.95))) if x < W else 0
        od.line([(x, 0), (x, H)], fill=(10, 13, 18, a if bg_name else 255))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(canvas)
    d.rectangle([70, 96, 76, 150], fill=(82, 218, 198))
    d.text((96, 100), kicker.upper(), font=load_font(20, serif=False), fill=(82, 218, 198))
    tf = load_font(62, bold=False)
    lines = []
    for para in [title]:
        words, line = para.split(), ""
        for w in words:
            test = (line + " " + w).strip()
            if d.textlength(test, font=tf) > 640:
                lines.append(line)
                line = w
            else:
                line = test
        lines.append(line)
    y = 190
    for ln in lines[:5]:
        d.text((72, y), ln, font=tf, fill=(236, 232, 222))
        y += 76
    d.text((72, 560), "THELEARNINGEARTH.COM", font=load_font(18, serif=False), fill=(142, 148, 136))
    canvas.save(out, "JPEG", quality=86, optimize=True)
    return f"/assets/og/{slug}.jpg"


# ---------------------------------------------------------------------------
# Article rendering
# ---------------------------------------------------------------------------
def prep_markdown(raw):
    text = raw.replace("\r\n", "\n")
    # formatting artifacts left over from a search tool: "(cite index=...>" ... "</cite>"
    text = re.sub(r'\(cite index="[^"]*">', "", text)
    text = text.replace("</cite>", "")
    m = re.match(r"# (.+)\n", text)
    title = m.group(1).strip().replace("'", "’")
    text = text[m.end():]
    mm = re.search(r"^\*Meta description: (.+)\*\s*$", text, re.M)
    meta = mm.group(1).strip() if mm else ""
    if mm:
        text = text[:mm.start()] + text[mm.end():]
    text = re.sub(r"^\s*---\s*\n", "", text, count=1)
    cta_re = re.compile(r"^\[Read more about the book →\]\(#\) \| \[Get the first chapter free →\]\(#\)\s*$", re.M)
    text = cta_re.sub(
        '\n<div class="cta"><a class="btn" href="/book/">Read more about the book →</a>'
        '<a class="btn btn-ghost" href="/newsletter/">Get the first chapter free →</a></div>\n', text)
    text = resolve_links(text)
    return title, meta, text.strip() + "\n"


def render_body(md_text):
    md = markdown.Markdown(extensions=["toc", "smarty", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "2-3", "permalink": False}})
    body = md.convert(md_text)
    toc = [(t["id"], t["name"]) for t in md.toc_tokens if t["level"] == 2]
    # epistemic-boundary sections become a distinct, recurring component
    def wrap(m):
        return ('<aside class="boundary" aria-label="Epistemic boundary">'
                '<p class="boundary-label">The boundary</p>' + m.group(1) + "</aside>")
    pattern = re.compile(r'(<h2 id="(?:%s)">.*?)(?=<h2|<hr|\Z)' % "|".join(BOUNDARY_IDS), re.S)
    body = pattern.sub(wrap, body)
    return body, toc


def article_page(page):
    raw = (CONTENT / page["file"]).read_text(encoding="utf-8")
    title, orig_meta, md_text = prep_markdown(raw)
    meta = page.get("meta") or orig_meta
    body, toc = render_body(md_text)
    words = len(plain_text(body).split())
    minutes = max(1, round(words / 220))
    pil = PILLAR[page["pillar"]]
    draft = page["status"] != "published"
    path = page["path"]
    out_rel = (("_drafts" + path) if draft else path).strip("/") + "/index.html"
    og_path = make_og(path.strip("/").replace("/", "-"), pil["label"], title, page.get("og_bg"))
    page["title"] = title
    page["words"] = words
    page["minutes"] = minutes
    page["meta_len"] = len(meta)
    page["og"] = og_path

    toc_html = ""
    if len(toc) >= 4:
        lis = "".join(f'<li><a href="#{i}">{esc(html.unescape(re.sub(r"<[^>]+>", "", n)))}</a></li>' for i, n in toc)
        toc_html = f'<nav class="toc" aria-label="In this article"><p class="toc-title">In this article</p><ol>{lis}</ol></nav>'

    cluster_items = ""
    for c in [p for p in PAGES if p["pillar"] == page["pillar"] and p["kind"] == "cluster" and p.get("listed", True)]:
        if c["status"] == "published":
            cluster_items += f'<li><a href="{c["path"]}">{esc(c["title"])}</a></li>'
        else:
            cluster_items += f'<li><span class="soon">{esc(c["title"])}</span><span class="tag">Coming soon</span></li>'
    others = "".join(
        f'<li><a href="{o["path"]}">{esc(PILLAR[o["pillar"]]["label"])}</a></li>'
        for o in PAGES if o["kind"] == "cornerstone" and o["status"] == "published" and o["path"] != path)
    more = f"""<section class="more wrap-narrow" aria-labelledby="more-h">
<h2 id="more-h">More in this pillar</h2><ul class="pillar-list">{cluster_items}</ul>
<h2>The other pillars</h2><ul class="plain-list">{others}</ul>
</section>""" if cluster_items else ""

    cap = f"<figcaption>{esc(page['caption'])}</figcaption>" if page.get("caption") else ""
    hero = f"""<figure class="hero">
<img src="/assets/img/{page['hero']}.webp" width="1200" height="658" alt="{esc(page['alt'])}" fetchpriority="high">{cap}
</figure>"""

    schema = [
        {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": meta,
         "image": [url(og_path)], "author": {"@type": "Person", "name": AUTHOR},
         "publisher": {"@type": "Organization", "name": SITE_NAME,
                       "logo": {"@type": "ImageObject", "url": url("/favicon-192.png")}},
         "datePublished": TODAY, "dateModified": TODAY, "mainEntityOfPage": url(path), "wordCount": words},
        breadcrumb([("Home", "/"), ("Articles", "/articles/"), (title, path)]),
    ]
    h = head(title, meta, path, og_path, schema, noindex=draft, canonical_path=path)
    h += header("/sources/" if path == "/sources/" else "/articles/")
    h += f"""<main id="main">
<article>
<header class="art-head">
<div class="wrap-narrow">
<p class="kicker"><span>{esc(pil['label'])}</span><span class="dot">&middot;</span><span>Cornerstone</span></p>
<h1>{esc(title)}</h1>
<p class="dek">{esc(meta)}</p>
<p class="byline">By {AUTHOR}<span class="dot">&middot;</span>{human_date(TODAY)}<span class="dot">&middot;</span>{minutes} min read</p>
</div>
</header>
{hero}
<div class="prose wrap-narrow">
{toc_html}
{body}
</div>
{more}
<section class="signup-band" aria-labelledby="sb-h"><div class="wrap-narrow">
<h2 id="sb-h">Be first to know</h2>
<p>The book is in its final editing stage. Leave your email and you will hear when it is ready.</p>
{notify_form("a")}
</div></section>
</article>
</main>
"""
    h += footer()
    write(out_rel, h)
    return page


# ---------------------------------------------------------------------------
# Other pages
# ---------------------------------------------------------------------------
def cornerstone_cards():
    cards = ""
    for pil in PILLARS:
        pg = next(p for p in PAGES if p["pillar"] == pil["key"] and p["kind"] == "cornerstone")
        live = pg["status"] == "published"
        thumb = f'<img src="/assets/img/{pg["hero"]}.webp" width="600" height="329" alt="" loading="lazy">'
        if live:
            cta = f'<a class="card-link" href="{pg["path"]}">Read the guide <span aria-hidden="true">→</span></a>'
        else:
            cta = '<span class="tag">In preparation</span>'
        cards += f"""<article class="card">
<div class="card-img">{thumb}</div>
<div class="card-body"><p class="kicker-sm">{esc(pil['label'])}</p>
<h3>{esc(pg.get('title', ''))}</h3>
<p>{esc(pil['blurb'])}</p>{cta}</div></article>"""
    return cards


def home_page():
    desc = ("A philosophical framework for life, consciousness and memory. Systems science, thermodynamics and "
            "the oldest texts on qi, read side by side, with the boundary between them marked.")
    og = make_og("home", SUBTITLE, "The Learning Earth", "bg_home.jpg")
    schema = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE + "/",
               "description": desc, "author": {"@type": "Person", "name": AUTHOR}}]
    h = head(f"{SITE_NAME}: {SUBTITLE}", desc, "/", og, schema, suffix=False)
    h += header()
    h += f"""<main id="main">
<section class="home-hero"><div class="wrap hero-grid">
<div class="hero-copy">
<p class="eyebrow">A book in progress</p>
<h1>The Learning <em>Earth</em></h1>
<p class="subtitle">{SUBTITLE}</p>
<p class="lead">The standard account treats Earth as a habitat. This book asks what changes if the planet is read as a system that accumulates structure, and what “learning” can rigorously mean at that scale. It is written by an engineer, and it marks the line between established science and interpretation.</p>
<p class="actions"><a class="btn" href="/earth-as-a-learning-system/">Start with the introduction</a><a class="btn btn-ghost" href="/newsletter/">Be first to know</a></p>
</div>
<figure class="hero-fig"><img src="/assets/img/home-hero.webp" width="900" height="1347" alt="A translucent human figure rises from the sea. Its torso is an island of forest and animals; below the waterline the body continues as a column of ocean life, from plankton and shells to fish." fetchpriority="high"></figure>
</div></section>

<section class="home-section"><div class="wrap">
<p class="kicker-sm light">Four ways in</p>
<h2>Four pillars, one argument</h2>
<div class="cards">{cornerstone_cards()}</div>
</div></section>

<section class="home-band"><div class="wrap-narrow">
<h2>Be first to know</h2>
<p>The book is in its final editing stage. Leave your email and you will hear when it is ready.</p>
{notify_form("h")}
</div></section>
</main>
"""
    h += footer()
    write("index.html", h)


def book_page():
    desc = "The Learning Earth, a philosophical framework for life, consciousness and memory: what the book argues and its table of contents. Coming soon."
    og = "/assets/og/home.jpg"
    toc = "".join(f'<li><span class="toc-l">{esc(a)}</span><span class="toc-t">{esc(b)}</span></li>' for a, b in BOOK_TOC)
    schema = [breadcrumb([("Home", "/"), ("The Book", "/book/")])]
    h = head("The Book", desc, "/book/", og, schema)
    h += header("/book/")
    h += f"""<main id="main">
<header class="page-head"><div class="wrap-narrow"><p class="eyebrow">Coming soon</p>
<h1>The Learning Earth</h1><p class="dek">{SUBTITLE}</p></div></header>
<div class="prose wrap-narrow">
<h2>What the book argues</h2>
<p>The standard account treats Earth as a habitat: a stage on which life happens. The Learning Earth reads the planet and its biosphere as one coupled system, and asks what “learning” can rigorously mean for such a system.</p>
<p>It extends one reframing upward from organisms to ecosystems to the planet: <strong>chi, the concept the old traditions kept circling, read as the flow of organization</strong> (a process, not a substance), and asks what follows if organization, rather than energy or matter, is the thing that accumulates.</p>
<p>It is a philosophical synthesis, not a scientific result. Every step from physical description to interpretation is marked.</p>
<h2>Where to buy</h2>
<p>Not yet available. Leave your email below and you will hear when the book is ready.</p>
{notify_form("b")}
<h2>Contents</h2>
<ol class="book-toc">{toc}</ol>
</div>
</main>
"""
    h += footer()
    write("book/index.html", h)


def articles_page():
    desc = "All articles on The Learning Earth, organized by the four pillars: Earth as a learning system, chi reframed, the ancient sources, and the science of organization."
    blocks = ""
    for pil in PILLARS:
        pg = next(p for p in PAGES if p["pillar"] == pil["key"] and p["kind"] == "cornerstone")
        live = pg["status"] == "published"
        title = pg.get("title", "")
        main = (f'<a href="{pg["path"]}">{esc(title)}</a>' if live else f'<span class="soon">{esc(title)}</span><span class="tag">In preparation</span>')
        clusters = ""
        for c in [p for p in PAGES if p["pillar"] == pil["key"] and p["kind"] == "cluster" and p.get("listed", True)]:
            clusters += (f'<li><a href="{c["path"]}">{esc(c["title"])}</a></li>' if c["status"] == "published"
                         else f'<li><span class="soon">{esc(c["title"])}</span><span class="tag">Coming soon</span></li>')
        blocks += f"""<section class="pillar-block"><p class="kicker-sm">{esc(pil['label'])}</p>
<h2>{main}</h2><p>{esc(pil['blurb'])}</p><ul class="pillar-list">{clusters}</ul></section>"""
    schema = [breadcrumb([("Home", "/"), ("Articles", "/articles/")])]
    h = head("Articles", desc, "/articles/", "/assets/og/home.jpg", schema)
    h += header("/articles/")
    h += f"""<main id="main">
<header class="page-head"><div class="wrap-narrow"><h1>Articles</h1>
<p class="dek">Four pillars. Each starts with one long cornerstone guide; shorter articles branch from it and link back.</p></div></header>
<div class="wrap-narrow pillars">{blocks}</div>
</main>
"""
    h += footer()
    write("articles/index.html", h)


def about_page():
    desc = f"About {AUTHOR}, the engineer behind The Learning Earth."
    schema = [{"@context": "https://schema.org", "@type": "Person", "name": AUTHOR, "url": SITE + "/about/",
               "jobTitle": "Engineer and author"}, breadcrumb([("Home", "/"), ("About", "/about/")])]
    h = head("About the Author", desc, "/about/", "/assets/og/home.jpg", schema, noindex=True)
    h += header("/about/")
    h += f"""<main id="main">
<header class="page-head"><div class="wrap-narrow"><h1>{AUTHOR}</h1></div></header>
<div class="prose wrap-narrow">
<p>Panagiotis Kokkorogiannis is an engineer by training. He brings a systems mindset (inputs, feedback, signal versus noise) to questions that philosophy and biology have long circled separately.</p>
<p>He describes himself as an engineer, not a scientist. On this site, what is established science and what is his own interpretation are kept apart and marked as such.</p>
</div>
</main>
"""
    h += footer()
    write("about/index.html", h)


def newsletter_page():
    desc = "Be first to know when The Learning Earth is published."
    schema = [breadcrumb([("Home", "/"), ("Newsletter", "/newsletter/")])]
    h = head("Newsletter", desc, "/newsletter/", "/assets/og/home.jpg", schema)
    h += header("/newsletter/")
    h += f"""<main id="main">
<header class="page-head"><div class="wrap-narrow"><h1>Be first to know</h1>
<p class="dek">The book is in its final editing stage. Leave your email and you will hear when it is ready.</p></div></header>
<div class="wrap-narrow newsletter">{notify_form("n")}</div>
</main>
"""
    h += footer()
    write("newsletter/index.html", h)


def not_found_page():
    h = head("Page not found", "This page does not exist.", "/404.html", "/assets/og/home.jpg", noindex=True)
    h += header()
    h += """<main id="main"><header class="page-head"><div class="wrap-narrow"><h1>Page not found</h1>
<p class="dek">This page does not exist, or it has not been published yet.</p>
<p><a class="btn" href="/articles/">See the articles</a></p></div></header></main>
"""
    h += footer()
    write("404.html", h)


def seo_files():
    urls = ["/", "/book/", "/articles/", "/newsletter/"] + [p["path"] for p in PAGES if p["status"] == "published"]
    items = "".join(f"<url><loc>{url(u)}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /_drafts/\nDisallow: /_src/\n\nSitemap: {SITE}/sitemap.xml\n")
    write(".htaccess", textwrap.dedent("""\
        # The Learning Earth: server rules (Apache, as used by Plesk)
        Options -Indexes
        ErrorDocument 404 /404.html

        # never serve database files (subscribers.db) or build sources
        <FilesMatch "\\.(db|sqlite|sqlite3)$">
          Require all denied
        </FilesMatch>
        RedirectMatch 404 ^/(_src|_drafts|\\.git)(/|$)

        <IfModule mod_deflate.c>
          AddOutputFilterByType DEFLATE text/html text/css application/javascript image/svg+xml application/xml
        </IfModule>
        <IfModule mod_expires.c>
          ExpiresActive On
          ExpiresByType image/webp "access plus 1 year"
          ExpiresByType image/jpeg "access plus 1 year"
          ExpiresByType font/woff2 "access plus 1 year"
          ExpiresByType text/css "access plus 1 month"
          ExpiresByType application/javascript "access plus 1 month"
          ExpiresByType text/html "access plus 1 hour"
        </IfModule>
        """))


def clean():
    for rel in ["index.html", "404.html", "sitemap.xml", "robots.txt", ".htaccess", "book", "articles", "about",
                "newsletter", "_drafts", "assets/og"]:
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for p in PAGES:
        d = ROOT / p["path"].strip("/").split("/")[0]
        if p["kind"] == "cornerstone" and d.is_dir():
            shutil.rmtree(d)


def main():
    clean()
    for p in PAGES:
        if p["kind"] == "cornerstone":
            article_page(p)
    home_page()
    book_page()
    articles_page()
    about_page()
    newsletter_page()
    not_found_page()
    seo_files()
    print("Built. Pages:")
    for p in PAGES:
        if p["kind"] == "cornerstone":
            flag = "" if p["meta_len"] <= 160 else "  (meta description > 160 chars)"
            print(f"  [{p['status']:9}] {p['path']:34} {p['words']:5} words, {p['minutes']} min, meta {p['meta_len']}{flag}")


if __name__ == "__main__":
    main()
