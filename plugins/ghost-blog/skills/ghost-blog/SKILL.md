---
name: ghost-blog
description: "This skill should be used when the user wants to interact with a Ghost blog via its Content and Admin APIs. Relevant when the user says things like 'list my blog posts', 'create a new draft', 'publish my draft', 'schedule a post for tomorrow', 'upload an image to my blog', 'manage blog tags', 'show my Ghost site info', 'filter posts by tag', 'delete a post', 'list members', 'send a newsletter', or any Ghost blog management task involving posts, pages, tags, members, newsletters, tiers, or images."
---

# Ghost Blog Management

Interact with the user's Ghost blog using the Content API (read-only, public data) and Admin API (full read/write access).

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GHOST_API_URL` | Base URL of the Ghost instance (e.g. `https://myblog.ghost.io`) |
| `GHOST_CONTENT_API_KEY` | Content API key for read-only public access |
| `GHOST_ADMIN_API_KEY` | Admin API key in `{id}:{secret}` format for full access |

These are created in Ghost Admin under Settings > Integrations > Custom Integration.

## The `ghost_api.py` Module

All operations use the `Ghost` class from `ghost_api.py` (stdlib only, no dependencies). It handles JWT auth, JSON serialization, and HTTP requests. The module lives in the same directory as this skill file.

**Every script follows this pattern** (use the base directory shown when this skill is loaded as the PYTHONPATH):

```bash
PYTHONPATH=<base_directory_of_this_skill> python3 << 'PY'
from ghost_api import Ghost

g = Ghost()
# ... operations here ...
PY
```

### API Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `g.get(path, **params)` | Returns dict | GET request, params become query string |
| `g.post(path, data, **params)` | Returns dict | POST with JSON body |
| `g.put(path, data, **params)` | Returns dict | PUT with JSON body |
| `g.delete(path)` | Returns None | DELETE request |
| `g.upload(file_path, ref=None)` | Returns URL string | Multipart image upload |
| `g.unsplash_search(query, orientation="landscape", per_page=10)` | Returns list of dicts | Search Unsplash photos |
| `g.unsplash_caption(photo_id=None, user_name=None, user_username=None)` | Returns HTML string | Build Unsplash attribution caption |
| `g.set_unsplash_feature_image(post_id, photo_id)` | Returns post dict | Set feature image from Unsplash photo ID |

**Path convention**: paths start with `content/` or `admin/` (e.g. `content/posts`, `admin/posts/abc123`). Auth is handled automatically based on prefix.

## Common Operations

### List Posts

```python
# Public posts
posts = g.get("content/posts", include="tags,authors", limit=15)

# All posts including drafts
posts = g.get("admin/posts", include="tags,authors", formats="html", limit=15)

for p in posts["posts"]:
    date = (p.get("published_at") or "(draft)")[:10]
    tags = ", ".join(t["name"] for t in p.get("tags", []))
    print(f"  {date}  {p['title']}  {tags}")
print(f"Total: {posts['meta']['pagination']['total']}")
```

### Filter and Search Posts

Pass `filter` as a query param using NQL syntax:

```python
# By tag
posts = g.get("content/posts", filter="tag:my-tag", include="tags")

# Drafts only (Admin API)
drafts = g.get("admin/posts", filter="status:draft", formats="html")

# Last 7 days
recent = g.get("admin/posts", filter="published_at:>now-7d", formats="html")

# Combined: published + specific tag (+ is AND, comma is OR)
posts = g.get("admin/posts", filter="status:published+tag:news", formats="html")
```

**NQL operators**: `:` (equals), `-` (not), `>` `>=` `<` `<=` (comparison), `~` (contains), `[a,b]` (in), `+` (AND), `,` (OR), `()` (grouping). Wrap dates/special chars in single quotes.

### Read a Single Post

```python
# By ID
post = g.get("admin/posts/POST_ID", formats="html", include="tags,authors")["posts"][0]

# By slug (Content API)
post = g.get("content/posts/slug/my-post-slug", include="tags,authors")["posts"][0]
```

### Create a Post

Use `g.create_post()` which automatically adds `source=html` when HTML content is present (Ghost v5+ requires this to convert HTML to its internal Lexical format; without it, content will be empty):

```python
post = g.create_post({
    "title": "My New Post",
    "html": "<p>Post content in HTML.</p>",
    "status": "draft",
    "tags": [{"name": "Tag Name"}],
    "custom_excerpt": "A short excerpt.",
})
print(f"Created: {post['title']} (ID: {post['id']})")
```

**Status options**: `draft` (default), `published`, `scheduled` (requires `published_at`).

Tags that don't exist are created automatically. To preserve raw HTML blocks, wrap in `<!--kg-card-begin: html-->` and `<!--kg-card-end: html-->`.

### Update a Post

Use `g.update_post()` which fetches `updated_at` automatically and adds `source=html` when HTML content is present. Tags and authors are **replaced entirely** on update, so send the complete desired list.

```python
post = g.update_post("POST_ID", {
    "title": "Updated Title",
    "html": "<p>Updated content.</p>",
})
```

If you already have `updated_at` from a previous GET, pass it to skip the extra request:

```python
post = g.update_post("POST_ID", {
    "html": "<p>Updated content.</p>",
}, updated_at=existing_post["updated_at"])
```

### Publish a Draft

```python
post = g.get("admin/posts/POST_ID")["posts"][0]
g.put("admin/posts/POST_ID",
    {"posts": [{"status": "published", "updated_at": post["updated_at"]}]})
```

### Schedule a Post

```python
post = g.get("admin/posts/POST_ID")["posts"][0]
g.put("admin/posts/POST_ID",
    {"posts": [{
        "status": "scheduled",
        "published_at": "2026-03-15T11:00:00.000Z",
        "updated_at": post["updated_at"],
    }]})
```

### Delete a Post

**Always confirm with the user before deleting.**

```python
g.delete("admin/posts/POST_ID")
```

### Upload an Image

```python
url = g.upload("/path/to/image.jpg")
print(url)  # https://myblog.ghost.io/content/images/2026/02/image.jpg
```

Supported formats: JPEG, PNG, GIF, WEBP, SVG.

### Insert an Image into Post Content

After uploading, use this HTML to embed the image:

```html
<figure class="kg-card kg-image-card kg-card-hascaption">
  <img src="{uploaded_url}" class="kg-image" alt="description" loading="lazy">
  <figcaption>Optional caption</figcaption>
</figure>
```

For wide images, add `kg-width-wide` or `kg-width-full` to the figure class.

### Set Feature Image (Hero Image)

Include in create/update payload:

```python
{"posts": [{
    "feature_image": "https://example.com/image.jpg",
    "feature_image_alt": "Alt text",
    "feature_image_caption": "Caption",
    "updated_at": post["updated_at"],
}]}
```

**Unsplash feature images**: Use the built-in helpers to search Unsplash and set feature images with proper attribution in one call:

```python
results = g.unsplash_search("abstract flowing lines", per_page=5)
for r in results:
    print(f"{r['id']}  {r['width']}x{r['height']}  by {r['user_name']}  plus={r['is_plus']}")

# Set feature image with auto-generated attribution caption
post = g.set_unsplash_feature_image("POST_ID", results[0]["id"])
```

To build a caption without setting the feature image (e.g. for manual use):

```python
caption = g.unsplash_caption(photo_id="abc123")
# or skip the API call if you already have user info from search results:
caption = g.unsplash_caption(user_name="Author Name", user_username="author")
```

### Embedding YouTube Videos (Native Lexical Cards)

**Prefer native Lexical embed cards over raw HTML iframes.** Native embeds render correctly in Ghost's editor and frontend without sizing issues.

To embed a YouTube video, fetch oembed data and write a Lexical `embed` node directly:

```python
import json
import urllib.request

# Step 1: Fetch oembed metadata from YouTube
video_url = "https://www.youtube.com/watch?v=VIDEO_ID"
oembed_api = f"https://www.youtube.com/oembed?url={video_url}&format=json"
with urllib.request.urlopen(oembed_api) as resp:
    oembed = json.loads(resp.read())

# Step 2: GET the post as Lexical
post = g.get("admin/posts/POST_ID", formats="lexical")["posts"][0]
lexical = json.loads(post["lexical"])

# Step 3: Build the native embed node
embed_node = {
    "type": "embed",
    "version": 1,
    "url": video_url,
    "embedType": "video",
    "html": oembed["html"],
    "metadata": oembed
}

# Step 4: Insert or replace a node in the children array
lexical["root"]["children"].insert(1, embed_node)  # or replace: lexical["root"]["children"][N] = embed_node

# Step 5: PUT with Lexical JSON (no source="html")
g.put("admin/posts/POST_ID",
    {"posts": [{
        "lexical": json.dumps(lexical),
        "updated_at": post["updated_at"],
    }]})
```

This works for any oembed provider (YouTube, Vimeo, Twitter, etc.). The key differences from HTML-based updates:
- Use `formats="lexical"` when reading (not `formats="html"`)
- Send `"lexical": json.dumps(...)` in the PUT body (not `"html": ...`)
- Do NOT pass `source="html"` when updating via Lexical

## Other Resources

### Tags

```python
g.get("admin/tags", limit="all")                                              # List
g.post("admin/tags", {"tags": [{"name": "New Tag", "description": "..."}]})   # Create
g.delete("admin/tags/TAG_ID")                                                  # Delete
```

Internal tags use a `#` prefix in the name.

### Pages

Same as posts: replace `posts` with `pages` in all paths.

### Members

```python
g.get("admin/members", limit=15, include="labels")                            # List
g.get("admin/members", filter="status:paid")                                   # Filter
g.post("admin/members", {"members": [{"email": "a@b.com", "name": "Name"}]}) # Create
g.delete("admin/members/MEMBER_ID")                                            # Delete
```

### Newsletters

```python
g.get("admin/newsletters")                                                     # List
# Send post as email via newsletter
g.put("admin/posts/POST_ID",
    {"posts": [{"status": "published", "updated_at": post["updated_at"]}]},
    newsletter="newsletter-slug")
```

### Tiers, Site Info, Users

```python
g.get("admin/tiers", include="monthly_price,yearly_price,benefits")
g.get("content/settings")                     # Public settings
g.get("admin/site")                           # Admin site info
g.get("admin/users", include="roles,count.posts")
```

## Response Format

All browse responses return:

```json
{
  "posts": [ ... ],
  "meta": { "pagination": { "page": 1, "limit": 15, "pages": 3, "total": 42, "next": 2, "prev": null } }
}
```

Use `meta.pagination` to handle paging. Use `limit=all` sparingly; prefer pagination for large datasets.

## Error Handling

The `Ghost` class raises exceptions with HTTP status and Ghost's error message on failure:
- **401 Unauthorized**: JWT expired or invalid (auto-generated per request, so usually means bad key)
- **404 Not Found**: Resource ID or slug doesn't exist
- **422 Validation Error**: Missing `updated_at`, invalid field, etc.
- **429 Too Many Requests**: Rate limited, wait and retry

## Markdown Workflow

For editing posts as markdown instead of HTML, use `ghost_md.py` (requires [uv](https://docs.astral.sh/uv/)):

```bash
# Pull a post as markdown
<base_directory_of_this_skill>/ghost_md.py pull POST_ID /tmp/post.md

# Edit the markdown file, then push it back
<base_directory_of_this_skill>/ghost_md.py push POST_ID /tmp/post.md
```

This is the **preferred workflow for editing post content**. Pull the post as markdown, edit the `.md` file using standard text editing tools, then push it back. Ghost receives HTML converted from the markdown.

For creating new posts or updating metadata (title, tags, status, feature image, etc.), use the `ghost_api.py` module directly.

## Choosing the Right Content Format

| Approach | When to use |
|----------|-------------|
| **HTML with `source="html"`** | Default for creating/updating posts. Simple and works for most content. |
| **Markdown workflow** (`ghost_md.py`) | Preferred for editing existing post content. |
| **Lexical JSON** | Native embed cards (YouTube, Twitter, bookmarks) or surgical edits to specific nodes. Use `formats="lexical"` to read, send `"lexical": json.dumps(...)` to write, and do NOT pass `source="html"`. |
| **HTML cards** | When Ghost's HTML-to-Lexical conversion causes formatting issues (e.g., converting bold paragraphs back to headings). |

### HTML Cards (Raw HTML Escape Hatch)

When `source="html"` causes Ghost to reinterpret your markup (changing heading levels, merging paragraphs, etc.), wrap content in HTML card markers to preserve it exactly:

```html
<!--kg-card-begin: html-->
<div class="custom-section">
  <p><strong>Bold title that stays a paragraph</strong></p>
  <p>Supporting text that won't be merged or reformatted.</p>
</div>
<!--kg-card-end: html-->
```

Ghost stores this as a single opaque HTML card and won't convert it to Lexical nodes. Use inline `<style>` blocks inside the card for custom styling. Note that HTML card content is not editable in Ghost's visual editor (it shows as a code block).

## Guidelines

1. **Always use the `PYTHONPATH=... python3 << 'PY'` pattern** for all Ghost API operations
2. **Use `ghost_md.py pull/push` for editing post content** as markdown
3. **Use the Admin API** for writes and drafts; Content API for simple public reads
4. **Always GET before PUT** to obtain `updated_at` for collision detection
5. **Confirm destructive actions** (delete, unpublish) with the user first
6. **Use `source="html"`** when creating/updating posts with HTML content
7. **Use `formats="html"`** when reading posts via Admin API (defaults to Lexical only)
8. **Use `include="tags,authors"`** when listing posts for full context
9. **Always check `custom_excerpt` when updating a post's content or title.** Ghost uses `custom_excerpt` for cards, social previews, and SEO descriptions. If the post content or title changes significantly (e.g. translation, rewrite, new topic), the excerpt likely needs updating too. After any major edit, verify the excerpt still matches the current content and update it if not.
