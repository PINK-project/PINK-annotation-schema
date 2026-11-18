"""Build the GitHub Pages site from the Markdown files in docs/.

Usage: python docs/build_pages.py [OUTPUT_FOLDER]   (default: public)

Each docs/<name>.md becomes <name>.html, with links between the pages
rewritten from .md to .html. The example spreadsheets are copied along.
"""

import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# Pages in the navigation bar: (file name without .md, title)
NAV = [("index", "Home"), ("annotating", "Annotating resources"), ("scripts", "Scripts")]

TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} - PINK annotation schema</title>
    <style>
      :root {{ color-scheme: light; }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        line-height: 1.6;
        color: #1f2937;
        background: #f8fafc;
      }}
      nav {{
        background: #0f172a;
        padding: 0.6rem 1.25rem;
      }}
      nav a {{
        color: #e2e8f0;
        margin-right: 1.25rem;
        text-decoration: none;
      }}
      nav a.current {{ font-weight: bold; color: #ffffff; }}
      main {{
        max-width: 960px;
        margin: 0 auto;
        padding: 2.5rem 1.25rem 3rem;
      }}
      h1, h2, h3 {{ line-height: 1.25; color: #0f172a; }}
      code {{
        background: #e2e8f0;
        padding: 0.12rem 0.3rem;
        border-radius: 0.25rem;
      }}
      pre code {{
        display: block;
        padding: 0.9rem;
        overflow-x: auto;
      }}
      a {{ color: #0b5ed7; }}
      table {{ border-collapse: collapse; }}
      th, td {{ border: 1px solid #cbd5e1; padding: 0.4rem 0.6rem; }}
    </style>
  </head>
  <body>
    <nav>{nav}</nav>
    <main>
{body}
    </main>
  </body>
</html>
"""


def build(output):
    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for page in sorted(DOCS.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), page.stem)
        body = markdown.markdown(text, extensions=["extra", "toc"])
        # Links to other pages: name.md and name.md#anchor -> name.html
        body = re.sub(r'href="([^":/]+)\.md(#[^"]*)?"', r'href="\1.html\2"', body)
        nav = "".join(
            f'<a href="{name}.html"{" class=current" if name == page.stem else ""}>{label}</a>'
            for name, label in NAV
        )
        html = TEMPLATE.format(title=title, nav=nav, body=body)
        (output / f"{page.stem}.html").write_text(html, encoding="utf-8")
        print(f"Wrote {output / page.stem}.html")

    shutil.copytree(ROOT / "example_spreadsheets", output / "example_spreadsheets")
    (output / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "public")
