"""Build the HTML and PDF documentation from the Markdown sources.

    ./venv/bin/pip install -r docs/requirements.txt    # once
    ./venv/bin/python docs/build_docs.py

The `.md` files are the source of truth; every `.html` and `.pdf` in docs/ is generated
from them, so edit the Markdown and rebuild. Links between the sources are rewritten to
the generated HTML, and every internal link is checked: the build fails on a link to a
heading that does not exist. PDF needs Google Chrome or Chromium; without it only HTML
is built.
"""

import html
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension

DOCS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DOCS_DIR.parent
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


@dataclass(frozen=True)
class Document:
    source: Path
    output: str  # file name without extension, inside docs/
    lang: str
    pdf: bool = True


DOCUMENTS = (
    Document(DOCS_DIR / "scalert_event_ka.md", "scalert_event_ka", "ka"),
    Document(DOCS_DIR / "scalert_event_en.md", "scalert_event_en", "en"),
    Document(PROJECT_DIR / "scalert_event_ka.md", "setup_ka", "ka"),
    Document(DOCS_DIR / "README.md", "index", "ka", pdf=False),
)

STYLE = """
body { font-family: "Noto Sans Georgian", "DejaVu Sans", sans-serif; font-size: 15px;
       line-height: 1.55; color: #1f2328; max-width: 980px; margin: 0 auto; padding: 24px 32px; }
h1 { border-bottom: 2px solid #0b5394; padding-bottom: 6px; color: #0b5394; }
h2 { border-bottom: 1px solid #d0d7de; padding-bottom: 4px; margin-top: 2em; color: #0b5394; }
h3 { margin-top: 1.5em; }
a { color: #0b5394; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 0.88em; background: #f2f4f7;
       padding: 1px 4px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 10px 12px;
      overflow-x: auto; line-height: 1.35; }
pre code { background: none; padding: 0; font-size: 12.5px; }
table { border-collapse: collapse; margin: 12px 0; width: 100%; }
th, td { border: 1px solid #d0d7de; padding: 5px 9px; vertical-align: top; text-align: left; }
th { background: #eef2f7; }
tr:nth-child(even) td { background: #fafbfc; }
@page { size: A4; margin: 16mm 14mm; }
@media print {
  body { max-width: none; padding: 0; font-size: 11pt; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; }
  pre code { font-size: 8pt; }
  h2 { break-before: auto; break-after: avoid; }
  h3 { break-after: avoid; }
  tr, pre { break-inside: avoid; }
}
"""

PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
{body}
</body>
</html>
"""


def github_slug(value: str, separator: str = "-") -> str:
    """Heading id as GitHub and the Cursor preview make it, so `.md` links work everywhere."""
    value = re.sub(r"[^\w\- ]", "", value.strip().lower())
    return value.replace(" ", separator)


def render(document: Document) -> str:
    """Markdown → HTML body, with links to other sources pointing at their HTML."""
    converter = markdown.Markdown(
        extensions=["tables", "fenced_code", TocExtension(slugify=github_slug)],
        output_format="html",
    )
    body = converter.convert(document.source.read_text(encoding="utf-8"))
    outputs = {doc.source: doc.output for doc in DOCUMENTS}

    def relink(match: re.Match) -> str:
        target, anchor = match.group(1), match.group(2) or ""
        resolved = (document.source.parent / html.unescape(target)).resolve()
        if resolved not in outputs:
            raise SystemExit(f"{document.source.name}: link to {target}, which is not built")
        return f'href="{outputs[resolved]}.html{anchor}"'

    return re.sub(r'href="([^"#:]+\.md)(#[^"]*)?"', relink, body)


def check_links(pages: dict[str, str]) -> list[str]:
    """Return every internal link whose page or heading id does not exist."""
    ids = {name: set(re.findall(r'id="([^"]+)"', body)) for name, body in pages.items()}
    broken = []
    for name, body in pages.items():
        for href in re.findall(r'href="([^"]*)"', body):
            if re.match(r"[a-z]+:", href):
                continue
            page, _, anchor = href.partition("#")
            page = page.removesuffix(".html") if page else name
            if page.endswith(".pdf"):
                continue
            if page not in ids or (anchor and html.unescape(anchor) not in ids[page]):
                broken.append(f"{name}.html: {html.unescape(href)}")
    return broken


def find_chrome() -> str | None:
    return next((path for name in CHROME_NAMES if (path := shutil.which(name))), None)


def print_pdf(chrome: str, page: Path, pdf: Path) -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", page.as_uri()],
            check=True, capture_output=True, timeout=120,
        )


def main() -> int:
    bodies = {doc.output: render(doc) for doc in DOCUMENTS}
    broken = check_links(bodies)
    if broken:
        print("Broken links:\n  " + "\n  ".join(broken), file=sys.stderr)
        return 1

    for doc in DOCUMENTS:
        title = re.search(r"<h1[^>]*>(.*?)</h1>", bodies[doc.output], re.S)
        page = DOCS_DIR / f"{doc.output}.html"
        page.write_text(
            PAGE.format(lang=doc.lang, title=re.sub(r"<[^>]+>", "", title.group(1)) if title else doc.output,
                        style=STYLE, body=bodies[doc.output]),
            encoding="utf-8",
        )
        print(f"HTML {page.relative_to(PROJECT_DIR)}")

    chrome = find_chrome()
    if chrome is None:
        print("PDF skipped: Google Chrome or Chromium not found", file=sys.stderr)
        return 0
    for doc in DOCUMENTS:
        if doc.pdf:
            pdf = DOCS_DIR / f"{doc.output}.pdf"
            print_pdf(chrome, DOCS_DIR / f"{doc.output}.html", pdf)
            print(f"PDF  {pdf.relative_to(PROJECT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
