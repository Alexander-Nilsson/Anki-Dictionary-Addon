"""Convert raw captures into web-optimized media under site/assets/media.

Screenshots:  PNG -> AVIF + WebP at 1920px wide (2x source downscaled).
Clips:        WebM -> h264 MP4 (faststart, 1280px) + VP9 WebM (no audio).
              A JPEG poster is extracted for every clip.

Both formats are emitted so ``<picture>`` / ``<video>`` can fall back when
AVIF or VP9 is unavailable. The raw captures (site/media/raw) stay
gitignored; only the outputs in site/assets/media are committed.

Usage::

    uv run python scripts/docs_media/optimize.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "site" / "media" / "raw"
OUT = REPO / "site" / "assets" / "media"
MAX_W = 1920
VIDEO_W = 1280


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def optimize_images() -> list[str]:
    names: list[str] = []
    for png in sorted(RAW.glob("*.png")):
        stem = png.stem
        names.append(stem)
        scaled = png.with_suffix(".tmp.png")
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(png),
                "-vf",
                f"scale={MAX_W}:-1:flags=lanczos",
                str(scaled),
            ]
        )
        # q55: text-heavy screenshots keep crisp glyph edges; q25 (the
        # deprecated --min 40/--max 55 equivalent) visibly smears CJK.
        run(["avifenc", "-q", "55", "-j", "8", str(scaled), str(OUT / f"{stem}.avif")])
        # WebP at the full 1920px width so text stays crisp on retina
        # displays and wide gallery layouts.
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(scaled),
                "-quality",
                "82",
                str(OUT / f"{stem}.webp"),
            ]
        )
        scaled.unlink()
    return names


def duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return float(out)


def optimize_videos() -> list[str]:
    names: list[str] = []
    for webm in sorted(RAW.glob("*.webm")):
        stem = webm.stem
        names.append(stem)
        # Playwright starts each capture on the welcome screen; the useful
        # frame is near the end (results / theme applied / both tabs open).
        poster_at = max(duration(webm) * 0.85, 1.0)
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(webm),
                "-vf",
                f"scale={VIDEO_W}:-2:flags=lanczos",
                "-c:v",
                "libx264",
                "-crf",
                "29",
                "-preset",
                "slow",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                str(OUT / f"{stem}.mp4"),
            ]
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(webm),
                "-vf",
                f"scale={VIDEO_W}:-2:flags=lanczos",
                "-c:v",
                "libvpx-vp9",
                "-crf",
                "38",
                "-b:v",
                "0",
                "-row-mt",
                "1",
                "-an",
                str(OUT / f"{stem}.webm"),
            ]
        )
        run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{poster_at:.2f}",
                "-i",
                str(webm),
                "-frames:v",
                "1",
                "-vf",
                f"scale={VIDEO_W}:-2:flags=lanczos",
                "-q:v",
                "3",
                str(OUT / f"{stem}-poster.jpg"),
            ]
        )
    return names


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [cmd for cmd in ("ffmpeg", "avifenc") if not have(cmd)]
    if missing:
        print(f"missing tools: {', '.join(missing)}", file=sys.stderr)
        return 1
    images = optimize_images()
    videos = optimize_videos()
    manifest = {"images": images, "videos": videos}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"images: {images}")
    print(f"videos: {videos}")
    du = subprocess.run(["du", "-sh", str(OUT)], capture_output=True, text=True)
    print(du.stdout.strip())
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
