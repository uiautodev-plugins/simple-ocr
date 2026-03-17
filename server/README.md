# OCR Server

基于 FastAPI 和 ocrmac 的 OCR 文字识别服务。

## 快速开始

```sh
# 启动服务
uv run python main.py
```

服务地址：`http://localhost:31515`

API 文档：`http://localhost:31515/docs`

## API

### POST /ocr

OCR 文字识别

```json
// 请求
{
  "image": "base64编码的图片",
  "image_format": "png"
}

// 响应
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "root",
    "tagName": "root",
    "rect": {"x": 0, "y": 0, "width": 600, "height": 200},
    "confidence": 1.0,
    "children": [
      {
        "id": "root_0",
        "tagName": "text",
        "rect": {...},
        "confidence": 0.95,
        "props": {"text": "识别到的文字"}
      }
    ]
  }
}
```

### GET /health

健康检查

## 测试

```bash
# 单元测试
uv run pytest tests/ -m unit

# 集成测试（需先启动服务）
uv run pytest tests/ -m integration
```

## 注意事项

- **仅支持 macOS** - 使用 macOS 原生 OCR 框架
- **默认语言** - 英文 + 简体中文
