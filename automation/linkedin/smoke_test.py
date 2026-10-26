"""Post-and-delete test of every format: text, image, multi-image, GIF, MP4.

Run via the 'LinkedIn smoke test' workflow (manual trigger). Each post is deleted right after creation.
Needs ffmpeg for the GIF/MP4 fixtures.
"""
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

from linkedin_api import LinkedInError, from_env


def png(path: Path, rgb, size=400):
    row = b"\x00" + bytes(rgb) * size
    raw = zlib.compress(row * size)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def main():
    tmp = Path(tempfile.mkdtemp())
    png(tmp / "a.png", (37, 99, 235))
    png(tmp / "b.png", (16, 185, 129))
    ff = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi"]
    subprocess.run(ff + ["-i", "testsrc=duration=3:size=320x240:rate=10", str(tmp / "c.gif")], check=True)
    subprocess.run(ff + ["-i", "testsrc=duration=5:size=640x360:rate=25", "-pix_fmt", "yuv420p",
                         str(tmp / "d.mp4")], check=True)

    cases = [
        ("text", []),
        ("image", [tmp / "a.png"]),
        ("multi-image", [tmp / "a.png", tmp / "b.png"]),
        ("gif", [tmp / "c.gif"]),
        ("mp4", [tmp / "d.mp4"]),
    ]
    client = from_env()
    failed = 0
    for name, media in cases:
        try:
            urn = client.create_post(f"Automated API test ({name}), deleting now. #test", media, alt=name)
            time.sleep(3)
            client.delete_post(urn)
            print(f"✓ {name}: posted and deleted ({urn})")
        except LinkedInError as e:
            failed += 1
            print(f"✗ {name}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
