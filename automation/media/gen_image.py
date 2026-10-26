"""Generate an image with OpenAI (ChatGPT Images): python gen_image.py <prompt.md> <out.png> [size] [quality]

Needs OPENAI_API_KEY in the environment. Model defaults to gpt-image-2.5-flare; override with OPENAI_IMAGE_MODEL.
The prompt file is plain text (front matter-free); keep it next to the post in source/ so the image is reproducible.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://api.openai.com/v1/images/generations"


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    prompt_file, out = Path(sys.argv[1]), Path(sys.argv[2])
    size = sys.argv[3] if len(sys.argv) > 3 else "1536x1024"
    quality = sys.argv[4] if len(sys.argv) > 4 else "high"
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY is not set (export it in your shell profile)")

    payload = {
        "model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare"),
        "prompt": prompt_file.read_text().strip(),
        "size": size,
        "quality": quality,
        "n": 1,
    }
    req = urllib.request.Request(URL, json.dumps(payload).encode(), {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"OpenAI error {e.code}: {e.read().decode()[:500]}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
    print(f"wrote {out} ({payload['model']}, {size}, {quality})")


if __name__ == "__main__":
    main()
