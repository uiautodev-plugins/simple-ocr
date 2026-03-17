# coding: utf-8

import base64

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_image_base64() -> str:
    png_data = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("utf-8")
    return png_data


@pytest.mark.unit
class TestHealthCheck:
    def test_health_check_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.unit
class TestOCREndpointValidation:
    def test_missing_image_field(self, client: TestClient):
        response = client.post("/ocr", json={"image_format": "png"})
        assert response.status_code == 422

    def test_empty_image_returns_error(self, client: TestClient):
        response = client.post("/ocr", json={"image": "", "image_format": "png"})
        assert response.status_code in (400, 500)

    def test_invalid_base64_returns_error(self, client: TestClient):
        response = client.post("/ocr", json={"image": "not_valid_base64!!!", "image_format": "png"})
        assert response.status_code == 400

    def test_valid_request_structure(self, client: TestClient, sample_image_base64: str):
        response = client.post(
            "/ocr",
            json={"image": sample_image_base64, "image_format": "png"},
        )
        assert response.status_code in (200, 500)
