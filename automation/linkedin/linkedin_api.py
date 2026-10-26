"""Minimal LinkedIn REST client (stdlib only) for posting as a member with w_member_social."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.linkedin.com"
# Versioned API header (YYYYMM). LinkedIn supports each version for ~12 months; bump when nearing sunset.
API_VERSION = os.environ.get("LINKEDIN_API_VERSION", "202609")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif"}
VIDEO_EXT = {".mp4"}
VIDEO_PART = 4_194_304  # chunk size the Videos API hands out


class LinkedInError(RuntimeError):
    pass


class LinkedIn:
    def __init__(self, token: str, person_urn: str):
        self.token = token
        self.author = person_urn

    # ---- HTTP -------------------------------------------------------------
    def _request(self, method, url, body=None, headers=None, raw=None):
        h = {
            "Authorization": f"Bearer {self.token}",
            "LinkedIn-Version": API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        data = raw
        if body is not None:
            h["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode() or "{}"
                return resp.status, dict(resp.headers), json.loads(text) if text.strip().startswith("{") else {}
        except urllib.error.HTTPError as e:
            raise LinkedInError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read().decode()[:500]}") from None

    # ---- Media ------------------------------------------------------------
    def upload_image(self, path: Path) -> str:
        _, _, r = self._request("POST", f"{API}/rest/images?action=initializeUpload",
                                {"initializeUploadRequest": {"owner": self.author}})
        v = r["value"]
        self._put(v["uploadUrl"], path.read_bytes())
        return v["image"]

    def upload_video(self, path: Path) -> str:
        size = path.stat().st_size
        _, _, r = self._request("POST", f"{API}/rest/videos?action=initializeUpload", {
            "initializeUploadRequest": {"owner": self.author, "fileSizeBytes": size,
                                        "uploadCaptions": False, "uploadThumbnail": False}})
        v = r["value"]
        etags = []
        with path.open("rb") as f:
            for part in v["uploadInstructions"]:
                f.seek(part["firstByte"])
                chunk = f.read(part["lastByte"] - part["firstByte"] + 1)
                etags.append(self._put(part["uploadUrl"], chunk))
        self._request("POST", f"{API}/rest/videos?action=finalizeUpload", {
            "finalizeUploadRequest": {"video": v["video"], "uploadToken": v.get("uploadToken", ""),
                                      "uploadedPartIds": etags}})
        self._wait_video(v["video"])
        return v["video"]

    def _put(self, url, data) -> str | None:
        """Upload bytes; returns the part's ETag (needed to finalize video uploads)."""
        req = urllib.request.Request(url, data=data, method="PUT", headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/octet-stream"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.headers.get("ETag")
        except urllib.error.HTTPError as e:
            raise LinkedInError(f"upload -> {e.code}: {e.read().decode()[:300]}") from None

    def _wait_video(self, urn, timeout=600):
        """Poll until AVAILABLE. Read access may be blocked for w_member_social-only tokens; then just wait."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                _, _, r = self._request("GET", f"{API}/rest/videos/{urllib.parse.quote(urn)}")
            except LinkedInError as e:
                if "-> 403" in str(e):
                    time.sleep(60)
                    return
                raise
            status = r.get("status")
            if status == "AVAILABLE":
                return
            if status == "PROCESSING_FAILED":
                raise LinkedInError(f"video processing failed: {r}")
            time.sleep(10)
        raise LinkedInError("video still processing after 10 minutes")

    # ---- Posts ------------------------------------------------------------
    def create_post(self, text: str, media: list[Path] | None = None, alt: str = "") -> str:
        body = {
            "author": self.author,
            "commentary": to_little_text(text),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        media = media or []
        videos = [m for m in media if m.suffix.lower() in VIDEO_EXT]
        images = [m for m in media if m.suffix.lower() in IMAGE_EXT]
        if videos and images or len(videos) > 1:
            raise LinkedInError("a post can have one video, or 1-20 images, not both")
        if videos:
            body["content"] = {"media": {"id": self.upload_video(videos[0]), "title": alt or videos[0].stem}}
        elif len(images) == 1:
            body["content"] = {"media": {"id": self.upload_image(images[0]), "altText": alt or images[0].stem}}
        elif len(images) > 1:
            if len(images) > 20:
                raise LinkedInError("max 20 images per post")
            # alt may hold one text per image, in file order, separated by " | "
            alts = alt.split(" | ") if alt.count(" | ") == len(images) - 1 else [alt] * len(images)
            body["content"] = {"multiImage": {"images": [
                {"id": self.upload_image(p), "altText": a or p.stem} for p, a in zip(images, alts)]}}
        _, headers, _ = self._request("POST", f"{API}/rest/posts", body)
        urn = headers.get("x-restli-id") or headers.get("X-RestLi-Id")
        if not urn:
            raise LinkedInError("post created but no id returned")
        return urn

    def delete_post(self, urn: str):
        self._request("DELETE", f"{API}/rest/posts/{urllib.parse.quote(urn, safe='')}")


def post_url(urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{urn}/"


_RESERVED = re.compile(r"([\\|{}@\[\]()<>*_~#])")


def to_little_text(text: str) -> str:
    """Escape LinkedIn 'little text' reserved chars (unescaped ones truncate the post); keep #hashtags as tags."""
    out, last = [], 0
    for m in re.finditer(r"(?<![\w&])#(\w+)", text):
        out.append(_RESERVED.sub(r"\\\1", text[last:m.start()]))
        out.append("{hashtag|\\#|" + m.group(1) + "}")
        last = m.end()
    out.append(_RESERVED.sub(r"\\\1", text[last:]))
    return "".join(out)


def from_env() -> LinkedIn:
    try:
        return LinkedIn(os.environ["LINKEDIN_ACCESS_TOKEN"], os.environ["LINKEDIN_PERSON_URN"])
    except KeyError as e:
        raise SystemExit(f"missing env var {e}") from None
