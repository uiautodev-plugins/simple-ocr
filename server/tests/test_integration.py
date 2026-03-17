# coding: utf-8

import base64

import pytest
import requests


@pytest.fixture(scope="module")
def server_url() -> str:
    return "http://localhost:31515"


@pytest.fixture(scope="module")
def server_running(server_url: str) -> bool:
    try:
        response = requests.get(f"{server_url}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def require_server(server_running: bool, server_url: str):
    if not server_running:
        pytest.skip(f"Server not running: {server_url}")


@pytest.mark.integration
@pytest.mark.slow
class TestHealthCheckIntegration:
    def test_server_is_running(self, require_server, server_url: str):
        response = requests.get(f"{server_url}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.integration
@pytest.mark.slow
class TestOCREndpointIntegration:
    def test_ocr_with_text_image(
        self,
        require_server,
        server_url: str,
        sample_text_image_base64: str,
    ):
        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": sample_text_image_base64,
                "image_format": "png",
            },
            timeout=30,
        )

        assert response.status_code == 200
        result = response.json()

        assert result["code"] == 0
        assert result["message"] == "success"
        assert "data" in result

        data = result["data"]
        assert data["id"] == "root"
        assert data["tagName"] == "root"
        assert "rect" in data
        assert "confidence" in data
        assert "children" in data

        children = data["children"]
        if children:
            first_child = children[0]
            assert "id" in first_child
            assert "tagName" in first_child
            assert "rect" in first_child
            assert "confidence" in first_child
            assert "props" in first_child
            assert "text" in first_child["props"]

    def test_ocr_response_format(self, require_server, server_url: str, sample_text_image_base64: str):
        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": sample_text_image_base64,
                "image_format": "png",
            },
            timeout=30,
        )

        assert response.status_code == 200
        result = response.json()

        expected_keys = {"code", "message", "data"}
        assert set(result.keys()) == expected_keys

        data = result["data"]
        expected_data_keys = {"id", "tagName", "rect", "confidence", "children", "props"}
        assert set(data.keys()).issubset(expected_data_keys)

        rect = data["rect"]
        expected_rect_keys = {"x", "y", "width", "height"}
        assert set(rect.keys()) == expected_rect_keys

    def test_ocr_with_jpeg_format(
        self,
        require_server,
        server_url: str,
        sample_text_image,
    ):
        import io
        buffer = io.BytesIO()
        sample_text_image.save(buffer, format="JPEG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": img_base64,
                "image_format": "jpeg",
            },
            timeout=30,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    def test_ocr_invalid_base64(self, require_server, server_url: str):
        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": "not_valid_base64!!!",
                "image_format": "png",
            },
            timeout=10,
        )

        assert response.status_code == 400

    def test_ocr_empty_image(self, require_server, server_url: str):
        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": "",
                "image_format": "png",
            },
            timeout=10,
        )

        assert response.status_code in (400, 500)

    def test_ocr_missing_image_field(self, require_server, server_url: str):
        response = requests.post(
            f"{server_url}/ocr",
            json={"image_format": "png"},
            timeout=10,
        )

        assert response.status_code == 422

    def test_ocr_timeout_handling(self, require_server, server_url: str):
        from PIL import Image, ImageDraw
        large_img = Image.new("RGB", (5000, 5000), color="white")
        draw = ImageDraw.Draw(large_img)
        for i in range(0, 5000, 50):
            draw.text((10, i), f"Line {i}", fill="black")

        import io
        buffer = io.BytesIO()
        large_img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        response = requests.post(
            f"{server_url}/ocr",
            json={
                "image": img_base64,
                "image_format": "png",
            },
            timeout=60,
        )

        assert response.status_code in (200, 500, 504)

    def test_concurrent_requests(
        self,
        require_server,
        server_url: str,
        sample_text_image_base64: str,
    ):
        import concurrent.futures

        def make_request():
            return requests.post(
                f"{server_url}/ocr",
                json={
                    "image": sample_text_image_base64,
                    "image_format": "png",
                },
                timeout=30,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [
                future.result()
                for future in concurrent.futures.as_completed(futures)
            ]

        for response in results:
            assert response.status_code == 200
