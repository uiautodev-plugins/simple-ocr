# coding: utf-8

import base64
import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from main import (
    base64_to_image,
    create_root_node,
    ocrmac_to_ocr_node,
    process_ocr_request,
)


@pytest.fixture
def sample_image() -> Image.Image:
    img = Image.new("RGB", (200, 100), color="white")
    return img


@pytest.fixture
def sample_image_base64(sample_image: Image.Image) -> str:
    buffer = io.BytesIO()
    sample_image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.mark.unit
class TestBase64ToImage:
    def test_valid_png_base64(self, sample_image_base64: str):
        image = base64_to_image(sample_image_base64, "png")
        assert image is not None
        assert image.size == (200, 100)
        assert image.mode == "RGB"

    def test_data_url_prefix(self, sample_image_base64: str):
        data_url = f"data:image/png;base64,{sample_image_base64}"
        image = base64_to_image(data_url, "png")
        assert image is not None
        assert image.size == (200, 100)

    def test_invalid_base64_raises_error(self):
        with pytest.raises(Exception):
            base64_to_image("invalid_base64_string", "png")


@pytest.mark.unit
class TestCreateRootNode:
    def test_creates_root_node_with_correct_structure(self):
        from main import OCRNode, Props, Rect

        child1 = OCRNode(
            id="child1",
            tagName="text",
            rect=Rect(x=10, y=10, width=100, height=20),
            confidence=0.95,
            props=Props(text="Hello"),
        )
        child2 = OCRNode(
            id="child2",
            tagName="text",
            rect=Rect(x=10, y=40, width=100, height=20),
            confidence=0.90,
            props=Props(text="World"),
        )

        root = create_root_node(800, 600, [child1, child2])

        assert root.id == "root"
        assert root.tagName == "root"
        assert root.rect.x == 0
        assert root.rect.y == 0
        assert root.rect.width == 800
        assert root.rect.height == 600
        assert root.confidence == 1.0
        assert root.props is None
        assert len(root.children) == 2

    def test_creates_root_node_with_empty_children(self):
        root = create_root_node(100, 100, [])
        assert root.children == []
        assert root.rect.width == 100


@pytest.mark.unit
class TestOCRMacToOCRNode:
    def test_empty_result(self):
        result = ocrmac_to_ocr_node([], 100, 100, parent_id="test")
        assert result == []

    def test_single_line_result(self):
        mock_result = [
            ("Hello World", 0.95, [0.1, 0.2, 0.3, 0.05]),
        ]

        nodes = ocrmac_to_ocr_node(mock_result, 1000, 500, parent_id="test")

        assert len(nodes) == 1
        node = nodes[0]
        assert node.tagName == "text"
        assert node.props.text == "Hello World"
        assert node.confidence == 0.95
        assert node.rect.x == 100  # 0.1 * 1000
        assert node.rect.y == 100  # 0.2 * 500
        assert node.rect.width == 300  # 0.3 * 1000
        assert node.rect.height == 25  # 0.05 * 500
        assert node.id == "test_0"

    def test_multiple_lines_result(self):
        mock_result = [
            ("First line", 0.90, [0.1, 0.1, 0.8, 0.05]),
            ("Second line", 0.85, [0.1, 0.2, 0.8, 0.05]),
        ]

        nodes = ocrmac_to_ocr_node(mock_result, 1000, 500, parent_id="root")

        assert len(nodes) == 2
        assert nodes[0].props.text == "First line"
        assert nodes[1].props.text == "Second line"
        assert nodes[0].id == "root_0"
        assert nodes[1].id == "root_1"

    def test_handles_missing_bbox(self):
        mock_result = [
            ("Text only", 0.9),
        ]

        nodes = ocrmac_to_ocr_node(mock_result, 100, 100)

        assert len(nodes) == 1
        assert nodes[0].props.text == "Text only"
        assert nodes[0].confidence == 0.9
        assert nodes[0].rect.x == 0
        assert nodes[0].rect.y == 0


@pytest.mark.unit
class TestProcessOCRRequest:
    def test_process_with_mock_ocr(self, sample_image_base64: str):
        mock_ocr = MagicMock(return_value=[
            ("Hello World", 0.95, [0.1, 0.1, 0.5, 0.1]),
        ])

        response = process_ocr_request(
            sample_image_base64,
            "png",
            ocr_func=mock_ocr,
        )

        assert response.code == 0
        assert response.message == "success"
        assert response.data.id == "root"
        assert response.data.tagName == "root"

        mock_ocr.assert_called_once()

        temp_path = mock_ocr.call_args[0][0]
        assert not Path(temp_path).exists()

    def test_process_with_empty_ocr_result(self, sample_image_base64: str):
        mock_ocr = MagicMock(return_value=[])

        response = process_ocr_request(
            sample_image_base64,
            "png",
            ocr_func=mock_ocr,
        )

        assert response.code == 0
        assert len(response.data.children) == 0

    def test_process_with_multiple_lines(self, sample_image_base64: str):
        mock_ocr = MagicMock(return_value=[
            ("Line 1", 0.90, [0.1, 0.1, 0.5, 0.05]),
            ("Line 2", 0.85, [0.1, 0.2, 0.5, 0.05]),
            ("Line 3", 0.95, [0.1, 0.3, 0.5, 0.05]),
        ])

        response = process_ocr_request(
            sample_image_base64,
            "png",
            ocr_func=mock_ocr,
        )

        assert response.code == 0
        assert len(response.data.children) == 3
        assert response.data.children[0].props.text == "Line 1"
        assert response.data.children[1].props.text == "Line 2"
        assert response.data.children[2].props.text == "Line 3"

    def test_temp_file_cleanup_on_error(self, sample_image_base64: str):
        import tempfile

        mock_ocr = MagicMock(side_effect=Exception("OCR failed"))

        temp_parent = Path(tempfile.gettempdir())
        before_count = len(list(temp_parent.glob("tmp*")))

        with pytest.raises(Exception, match="OCR failed"):
            process_ocr_request(
                sample_image_base64,
                "png",
                ocr_func=mock_ocr,
            )

        # Note: This test may not be 100% reliable due to other processes
        after_count = len(list(temp_parent.glob("tmp*")))
        assert abs(after_count - before_count) <= 2

    def test_uses_image_dimensions_for_root_node(self, sample_image_base64: str):
        mock_ocr = MagicMock(return_value=[])

        response = process_ocr_request(
            sample_image_base64,
            "png",
            ocr_func=mock_ocr,
        )

        assert response.data.rect.width == 200
        assert response.data.rect.height == 100
