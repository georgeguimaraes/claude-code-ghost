#!/usr/bin/env -S uv run --with markdownify --with markdown
"""Ghost blog markdown helper: fetch posts as markdown, push markdown back as HTML.

Requires `uv` (https://docs.astral.sh/uv/).

Usage:
    ghost_md.py pull <post_id> [output_file]   - fetch post as markdown
    ghost_md.py push <post_id> <markdown_file>  - convert markdown to HTML and update post
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ghost_api import Ghost
from markdownify import markdownify as html_to_md
import markdown


def _detect_code_language(pre_el):
    """Extract language from <code class="language-xxx"> inside a <pre> element."""
    code = pre_el.find("code")
    if code and code.get("class"):
        classes = code["class"] if isinstance(code["class"], list) else [code["class"]]
        for c in classes:
            if c.startswith("language-"):
                return c.replace("language-", "")
    return ""


def pull(post_id, output=None):
    g = Ghost()
    post = g.get(f"admin/posts/{post_id}", formats="html", include="tags,authors")["posts"][0]
    md = html_to_md(
        post["html"],
        heading_style="ATX",
        code_language_callback=_detect_code_language,
    )
    if output:
        with open(output, "w") as f:
            f.write(md)
        print(f"Saved to {output}")
    else:
        print(md)


def push(post_id, md_file):
    g = Ghost()
    with open(md_file) as f:
        md_content = f.read()

    html = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
    post = g.get(f"admin/posts/{post_id}")["posts"][0]
    g.put(
        f"admin/posts/{post_id}",
        {"posts": [{"html": html, "updated_at": post["updated_at"]}]},
        source="html",
    )
    print("Updated")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd = args[0]
    if cmd == "pull":
        pull(args[1], args[2] if len(args) > 2 else None)
    elif cmd == "push":
        if len(args) < 3:
            print("Usage: ghost_md.py push <post_id> <markdown_file>", file=sys.stderr)
            sys.exit(1)
        push(args[1], args[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
