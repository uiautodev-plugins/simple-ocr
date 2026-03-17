# coding: utf-8

import base64
import binascii
import io
import logging
import tempfile
from pathlib import Path
from typing import Callable, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ocrmac import ocrmac
from PIL import Image
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Rect(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Props(BaseModel):
    text: str


class OCRNode(BaseModel):
    id: str
    tagName: str
    rect: Rect
    confidence: float
    props: Optional[Props] = None
    children: Optional[List["OCRNode"]] = None


class OCRResponse(BaseModel):
    code: int
    message: str
    data: OCRNode


class ImageRequest(BaseModel):
    image: str
    image_format: str = "png"


OCRFunc = Callable[[str], list]


def base64_to_image(base64_string: str, image_format: str = "png") -> Image.Image:
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    image_data = base64.b64decode(base64_string)
    image = Image.open(io.BytesIO(image_data))
    return image


def perform_ocr_livetext(image_path: str) -> list:
    """Perform OCR using macOS native framework."""
    ocr_instance = ocrmac.OCR(
        image_path,
        framework="livetext",
        unit="line",
        language_preference=["en-US", "zh-Hans"],
    )
    return ocr_instance.recognize()


def ocrmac_to_ocr_node(
    ocr_result, image_width: int, image_height: int, parent_id: str = ""
) -> List[OCRNode]:
    """
    Convert ocrmac result to OCRNode format.

    ocrmac returns: [(text, confidence, [x, y, w, h]), ...]
    bbox coordinates are normalized (0-1), need to convert to pixels.
    """
    nodes = []

    for idx, line in enumerate(ocr_result):
        text = line[0] if len(line) > 0 else ""
        confidence = line[1] if len(line) > 1 else 0.0
        bbox = line[2] if len(line) > 2 else [0, 0, 0, 0]

        node_id = f"{parent_id}_{idx}" if parent_id else str(uuid4())

        rect = Rect(
            x=int(bbox[0] * image_width),
            y=int(bbox[1] * image_height),
            width=int(bbox[2] * image_width),
            height=int(bbox[3] * image_height),
        )

        props = Props(text=text)

        node = OCRNode(
            id=node_id,
            tagName="text",
            rect=rect,
            confidence=float(confidence),
            props=props,
            children=None,
        )

        nodes.append(node)

    return nodes


def create_root_node(
    image_width: int, image_height: int, children: List[OCRNode]
) -> OCRNode:
    return OCRNode(
        id="root",
        tagName="root",
        rect=Rect(x=0, y=0, width=image_width, height=image_height),
        confidence=1.0,
        props=None,
        children=children,
    )


def process_ocr_request(
    image_base64: str,
    image_format: str,
    ocr_func: OCRFunc = perform_ocr_livetext,
) -> OCRResponse:
    image = base64_to_image(image_base64, image_format)
    image_width, image_height = image.size

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(Path(temp_dir) / f"image{image_format or '.png'}")
        image.save(temp_path, format="PNG")

        ocr_result = ocr_func(temp_path)

        children = ocrmac_to_ocr_node(
            ocr_result, image_width, image_height, parent_id="root"
        )

        root_node = create_root_node(image_width, image_height, children)
        return OCRResponse(code=0, message="success", data=root_node)


@app.post("/ocr", response_model=OCRResponse)
async def ocr_endpoint(request: ImageRequest) -> OCRResponse:
    try:
        return process_ocr_request(request.image, request.image_format)
    except binascii.Error as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR recognition failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting OCR server on http://localhost:31515")
    uvicorn.run(app, host="0.0.0.0", port=31515)
