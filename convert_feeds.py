"""Convert feeds.md to Meridian JSON import format."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


def infer_source_type(url: str) -> str:
    lower = url.lower().rstrip("/")
    if lower.endswith(".json") or "mmsp" in lower:
        return "mfeed"
    if lower.endswith(".atom"):
        return "atom"
    if "youtube.com" in lower:
        return "atom"
    if "podcast" in lower:
        return "podcast"
    return "rss"


def derive_title(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path

    m = re.search(r"channel_id=([^&]+)", url)
    if "youtube.com" in host and m:
        return f"YouTube/{m.group(1)}"

    m = re.match(r"/r/([^/]+)", path)
    if "reddit.com" in host and m:
        return f"r/{m.group(1)}"

    if "feedburner.com" in host:
        slug = path.strip("/").split("/")[-1]
        return re.sub(r"([A-Z])", r" \1", slug).strip()

    for prefix in ("www.", "feeds.", "feed.", "rss.", "blog.", "api."):
        if host.startswith(prefix):
            host = host[len(prefix):]
            break

    parts = host.split(".")
    name = parts[-2] if len(parts) >= 2 else parts[0]
    return name.replace("-", " ").replace("_", " ").title()


def convert(md_path: Path, out_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    urls = re.findall(r"https?://\S+", text)
    feeds = [
        {"url": url, "source_type": infer_source_type(url), "title": derive_title(url)}
        for url in urls
    ]
    data = {"version": 1, "feeds": feeds}
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(feeds)} feeds to {out_path}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("feeds.md")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".json")
    convert(src, dst)
