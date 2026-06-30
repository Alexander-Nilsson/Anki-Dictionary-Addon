from __future__ import annotations

import base64
import os
import re
import shutil
import time
from os.path import exists, join
from urllib.request import Request, urlopen

from aqt.qt import QImage, QSize, Qt

from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/35.0.1916.47 Safari/537.36"
)


def image_ext_from_url(url: str, fallback: str = "avif") -> str:
    if url.startswith("data:"):
        return fallback
    cleaned = re.sub(r"\?.*$", "", url)
    _, ext = os.path.splitext(cleaned.strip().split("/")[-1])
    ext = ext.lower().lstrip(".")
    known = {"jpg", "jpeg", "png", "gif", "webp", "avif", "bmp"}
    return ext if ext in known else fallback


def _headers() -> dict[str, str]:
    return {"User-Agent": _USER_AGENT}


def download_file(url: str, dest_path: str, timeout: int = 30) -> bool:
    try:
        if url.startswith("data:"):
            return _save_data_uri(url, dest_path)
        req = Request(url, headers=_headers())
        data = urlopen(req, timeout=timeout).read()
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_image(
    url: str,
    dest_path: str,
    max_w: int = 1500,
    max_h: int = 400,
    auto_convert: bool = True,
) -> bool:
    try:
        if url.startswith("data:"):
            header, encoded = url.split(",", 1)
            file_data = base64.b64decode(encoded)
        else:
            req = Request(url, headers=_headers())
            file_data = urlopen(req, timeout=30).read()

        if auto_convert:
            image = QImage()
            image.loadFromData(file_data)
            if image.isNull():
                return False
            image = image.scaled(
                QSize(max_w, max_h),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            return image.save(dest_path)
        else:
            with open(dest_path, "wb") as f:
                f.write(file_data)
            return True
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")
        return False


def _save_data_uri(data_uri: str, dest_path: str) -> bool:
    try:
        _, encoded = data_uri.split(",", 1)
        data = base64.b64decode(encoded)
        with open(dest_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        logger.error(f"Failed to save data URI: {e}")
        return False


def scale_image(
    source_path: str,
    dest_path: str,
    max_w: int,
    max_h: int,
    fmt: str = "AVIF",
) -> bool:
    try:
        image = QImage(source_path)
        if image.isNull():
            return False
        image = image.scaled(
            QSize(max_w, max_h),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return image.save(dest_path, fmt)
    except Exception as e:
        logger.error(f"Failed to scale image {source_path}: {e}")
        return False


def copy_to_media(source: str, filename: str, media_dir: str) -> str | None:
    dest = join(media_dir, filename)
    if exists(source) and not exists(dest):
        try:
            shutil.copy2(source, dest)
            return dest
        except Exception as e:
            logger.error(f"Failed to copy {source} to media: {e}")
            return None
    return dest if exists(dest) else None


def copy_to_temp(
    source: str, temp_dir: str, ext: str = "mp3"
) -> tuple[str | None, str | None]:
    try:
        if not exists(source):
            return None, None
        filename = str(time.time()).replace(".", "") + f".{ext}"
        dest = join(temp_dir, filename)
        if not exists(dest):
            shutil.copy2(source, dest)
        return dest, filename
    except Exception as e:
        logger.error(f"Failed to copy {source} to temp: {e}")
        return None, None


def unique_filename(prefix: str = "", ext: str = "avif") -> str:
    ts = str(time.time())[:-4].replace(".", "")
    return f"{ts}{prefix}.{ext}"


def wait_for_file(path: str, timeout: float = 15.0) -> bool:
    start = time.time()
    while True:
        if exists(path):
            return True
        if time.time() - start > timeout:
            return False


def remove_file(path: str) -> None:
    try:
        os.remove(path)
    except Exception as e:
        logger.warning(f"Failed to remove {path}: {e}")


def load_image_from_url(url: str) -> QImage | None:
    try:
        if url.startswith("data:"):
            _, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
        else:
            req = Request(url, headers=_headers())
            data = urlopen(req, timeout=10).read()
        image = QImage()
        image.loadFromData(data)
        return image if not image.isNull() else None
    except Exception as e:
        logger.error(f"Failed to load image from {url}: {e}")
        return None
