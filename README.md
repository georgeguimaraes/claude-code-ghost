# claude-code-ghost

A [Claude Code](https://code.claude.com) plugin marketplace for managing [Ghost](https://ghost.org) blogs.

## Plugins

### ghost-blog

Manage your Ghost blog directly from Claude Code: create, update, publish, schedule posts, upload images, manage tags, members, and newsletters.

Uses Ghost's Content API (read-only) and Admin API (read/write) with a zero-dependency Python client (stdlib only).

## Setup

### 1. Install the marketplace

```
/plugin marketplace add georgeguimaraes/claude-code-ghost
```

### 2. Install the plugin

```
/plugin install ghost-blog@claude-code-ghost
```

### 3. Set environment variables

Create a Custom Integration in your Ghost Admin (Settings > Integrations) and export the keys:

```bash
export GHOST_API_URL="https://yourblog.ghost.io"
export GHOST_CONTENT_API_KEY="your-content-api-key"
export GHOST_ADMIN_API_KEY="your-admin-api-key-id:secret"
```

### 4. Use it

Just ask Claude Code to interact with your blog:

- "list my recent blog posts"
- "create a draft about topic X"
- "publish my draft"
- "schedule a post for tomorrow at 9am"
- "upload this image to my blog"
- "show me my blog tags"
- "filter posts by tag"

## License

MIT
