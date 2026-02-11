#!/usr/bin/env python3
"""Ghost API client. Stdlib only, no dependencies. Use as a module or CLI."""

import hmac, hashlib, base64, json, time, os, sys, urllib.request, urllib.parse, urllib.error


class Ghost:
    def __init__(self):
        self.url = os.environ.get("GHOST_API_URL", "").rstrip("/")
        self.content_key = os.environ.get("GHOST_CONTENT_API_KEY", "")
        self.admin_key = os.environ.get("GHOST_ADMIN_API_KEY", "")
        if not self.url:
            raise EnvironmentError("GHOST_API_URL is not set")

    def _jwt(self):
        if not self.admin_key or ":" not in self.admin_key:
            raise EnvironmentError("GHOST_ADMIN_API_KEY is not set or invalid (expected id:secret)")
        kid, secret = self.admin_key.split(":", 1)
        now = int(time.time())
        def b64url(data):
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        header = b64url(json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}).encode())
        payload = b64url(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}).encode())
        signing_input = f"{header}.{payload}"
        sig = b64url(hmac.new(bytes.fromhex(secret), signing_input.encode(), hashlib.sha256).digest())
        return f"{signing_input}.{sig}"

    def _request(self, method, path, data=None, params=None):
        if path.startswith("content/"):
            if not self.content_key:
                raise EnvironmentError("GHOST_CONTENT_API_KEY is not set")
            params = dict(params or {})
            params["key"] = self.content_key
            headers = {}
        elif path.startswith("admin/"):
            headers = {"Authorization": f"Ghost {self._jwt()}"}
        else:
            raise ValueError(f"Path must start with content/ or admin/: {path}")

        url = f"{self.url}/ghost/api/{path}"
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                err = json.loads(error_body)
                msg = err.get("errors", [{}])[0].get("message", error_body)
                raise Exception(f"HTTP {e.code}: {msg}")
            except (json.JSONDecodeError, IndexError, KeyError):
                raise Exception(f"HTTP {e.code}: {error_body}")

    def get(self, path, **params):
        return self._request("GET", path, params=params or None)

    def post(self, path, data, **params):
        return self._request("POST", path, data=data, params=params or None)

    def put(self, path, data, **params):
        return self._request("PUT", path, data=data, params=params or None)

    def delete(self, path):
        return self._request("DELETE", path)

    def create_post(self, post_data):
        """Create a post. Automatically adds source=html when html key is present."""
        params = {}
        if "html" in post_data:
            params["source"] = "html"
        result = self.post("admin/posts", {"posts": [post_data]}, **params)
        return result["posts"][0]

    def update_post(self, post_id, post_data, updated_at=None):
        """Update a post. Fetches updated_at if not provided. Adds source=html when html key is present."""
        if updated_at is None:
            current = self.get(f"admin/posts/{post_id}")["posts"][0]
            updated_at = current["updated_at"]
        post_data["updated_at"] = updated_at
        params = {}
        if "html" in post_data:
            params["source"] = "html"
        result = self.put(f"admin/posts/{post_id}", {"posts": [post_data]}, **params)
        return result["posts"][0]

    def upload(self, file_path, ref=None):
        boundary = f"----GhostUpload{int(time.time() * 1000)}"
        filename = os.path.basename(file_path)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ct = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
              "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            file_data = f.read()

        parts = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {ct}\r\n\r\n".encode() + file_data + b"\r\n")
        if ref:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"ref\"\r\n\r\n{ref}\r\n".encode())
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)

        url = f"{self.url}/ghost/api/admin/images/upload/"
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Ghost {self._jwt()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        })
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())["images"][0]["url"]


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: ghost_api.py <get|post|put|delete|upload> <path> [key=value ...]", file=sys.stderr)
        sys.exit(1)

    method, path = args[0].upper(), args[1]
    g = Ghost()

    if method == "UPLOAD":
        url = g.upload(path, ref=os.path.basename(path))
        print(json.dumps({"url": url}, indent=2))
    elif method == "DELETE":
        g.delete(path)
        print("Deleted.")
    elif method == "GET":
        params = dict(kv.split("=", 1) for kv in args[2:] if "=" in kv)
        print(json.dumps(g.get(path, **params), indent=2))
    elif method in ("POST", "PUT"):
        params = dict(kv.split("=", 1) for kv in args[2:] if "=" in kv)
        data = json.load(sys.stdin)
        fn = g.post if method == "POST" else g.put
        print(json.dumps(fn(path, data, **params), indent=2))
    else:
        print(f"Unknown method: {method}", file=sys.stderr)
        sys.exit(1)
