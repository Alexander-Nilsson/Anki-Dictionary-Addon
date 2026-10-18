from __future__ import annotations

import base64
from io import BytesIO

import pytest
from aqt.qt import QImage
from PIL import Image, features

from anki_dictionary.utils import media_manager


@pytest.mark.skipif(not features.check("webp"), reason="Pillow lacks WebP support")
def test_download_image_decodes_webp(tmp_path):
    buffer = BytesIO()
    Image.new("RGB", (32, 24), (10, 20, 30)).save(buffer, format="WEBP")
    data_uri = "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()

    dest = tmp_path / f"image.{media_manager.preferred_image_ext()}"
    assert media_manager.download_image(data_uri, str(dest), 100, 100, True)

    assert dest.exists()
    assert not QImage(str(dest)).isNull()
