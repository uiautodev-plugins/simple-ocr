# coding: utf-8

import base64
import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_image_path() -> Path:
    path = Path(__file__).parent / "fixtures" / "sample.png"
    return path


@pytest.fixture
def sample_text_image() -> Image.Image:
    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except Exception:
        font = ImageFont.load_default()

    draw.text((50, 50), "Hello World!", fill="black", font=font)
    draw.text((50, 100), "OCR Test", fill="black", font=font)

    return img


@pytest.fixture
def sample_text_image_base64(sample_text_image: Image.Image) -> str:
    buffer = io.BytesIO()
    sample_text_image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.fixture
def sample_text_image_png_bytes(sample_text_image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    sample_text_image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def ocr_request_payload(sample_text_image_base64: str) -> dict:
    return {
        "image": sample_text_image_base64,
        "image_format": "png",
    }


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: Integration tests (require running server)")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "slow: Slow tests")
