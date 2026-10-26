"""Post folders: posts/{drafts,published}/YYYY-MM-DD-<slug>/post.md (+ media/)."""
import datetime as dt
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = ROOT / "posts" / "drafts"
PUBLISHED = ROOT / "posts" / "published"
ET = ZoneInfo("America/New_York")
SLOT_DAYS = {1, 3}  # Tue, Thu (Mon=0)
SLOT_HOUR = 9

FIELDS = ["publish_at", "status", "topic", "source", "attempts", "url", "published_at", "error", "feedback", "alt"]
TEXT_FIELDS = {"alt", "feedback", "error"}  # free text: kept verbatim, so " #" isn't read as a comment


class Post:
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / "post.md"
        raw = self.path.read_text()
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
        if not m:
            raise ValueError(f"{self.path}: missing front matter")
        self.meta = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                k, v = line.split(":", 1)
                k = k.strip()
                self.meta[k] = v.strip() if k in TEXT_FIELDS else v.split(" #", 1)[0].strip()
        self.body = m.group(2).strip()

    @property
    def status(self):
        return self.meta.get("status", "draft")

    @property
    def publish_at(self) -> dt.datetime | None:
        v = self.meta.get("publish_at")
        return dt.datetime.strptime(v, "%Y-%m-%d %H:%M").replace(tzinfo=ET) if v else None

    @property
    def media(self) -> list[Path]:
        d = self.folder / "media"
        return sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith(".")) if d.exists() else []

    def save(self):
        keys = FIELDS + [k for k in self.meta if k not in FIELDS]
        head = "\n".join(f"{k}: {self.meta.get(k, '')}" for k in keys if k in self.meta)
        self.path.write_text(f"---\n{head}\n---\n\n{self.body}\n")


def drafts() -> list[Post]:
    return [Post(p.parent) for p in sorted(DRAFTS.glob("*/post.md"))]


def next_slot(after: dt.datetime, taken: set[dt.datetime]) -> dt.datetime:
    d = after.astimezone(ET)
    day = d.replace(hour=SLOT_HOUR, minute=0, second=0, microsecond=0)
    if day <= d:
        day += dt.timedelta(days=1)
    while day.weekday() not in SLOT_DAYS or day in taken:
        day += dt.timedelta(days=1)
    return day


def fmt(t: dt.datetime) -> str:
    return t.astimezone(ET).strftime("%Y-%m-%d %H:%M")
