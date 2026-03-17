# 说明

这个文件是给AI来读的，通过这个文件可以知道项目的结构，作者期望AI的一些编码风格。

# OCR Server 项目

## 项目概述

基于 FastAPI 和 ocrmac 的简单 OCR 服务，提供 RESTful API 进行图片文字识别。

## 技术栈

- **FastAPI** - Web 框架
- **ocrmac** - macOS 原生 OCR 库
- **PIL/Pillow** - 图片处理
- **pytest** - 测试框架
- **uv** - Python 包管理器

## 项目结构

```
server/
├── main.py              # 主应用文件
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # pytest 配置和共享 fixtures
│   ├── fixtures/        # 测试资源
│   ├── test_api.py      # API 端点测试
│   ├── test_main.py     # 核心函数单元测试
│   └── test_integration.py  # 集成测试
└── pyproject.toml       # 项目配置
```

## 运行服务

```bash
# 开发模式运行
uv run python main.py

# 服务地址: http://localhost:31515
```

## 运行测试

```bash
# 所有测试
uv run pytest tests/ -v

# 只运行单元测试
uv run pytest tests/ -m unit

# 只运行集成测试（需要先启动服务）
uv run pytest tests/ -m integration

# 代码检查
uv run ruff check .
```

## 代码质量要点

### 1. 函数设计原则

- **公开函数**：核心业务逻辑函数（如 `base64_to_image`, `ocrmac_to_ocr_node`）设为公开，便于测试
- **依赖注入**：`process_ocr_request` 接受 `ocr_func` 参数，测试时可 mock
- **单一职责**：每个函数只做一件事，如 `create_root_node` 只负责创建根节点

### 2. 临时文件管理

使用 `TemporaryDirectory` 和 `with` 语句确保自动清理：

```python
def process_ocr_request(...):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(Path(temp_dir) / "image.png")
        image.save(temp_path, format="PNG")
        # ... 处理逻辑
        # with 块结束时自动清理
```

### 3. 测试组织

- **conftest.py**：共享配置（路径设置、fixtures）
- **test_api.py**：API 端点验证测试（使用 FastAPI TestClient）
- **test_main.py**：核心函数单元测试（使用 mock）
- **test_integration.py**：完整集成测试

### 4. 代码风格

- 使用 ruff 进行代码检查
- 所有导入按标准库、第三方库、本地模块排序
- 测试文件使用 `@pytest.mark.unit` 或 `@pytest.mark.integration` 标记

## API 端点

### POST /ocr

执行 OCR 识别。

**请求：**
```json
{
  "image": "base64编码的图片",
  "image_format": "png"
}
```

**响应：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "root",
    "tagName": "root",
    "rect": {"x": 0, "y": 0, "width": 800, "height": 600},
    "confidence": 1.0,
    "children": [
      {
        "id": "root_0",
        "tagName": "text",
        "rect": {...},
        "confidence": 0.95,
        "props": {"text": "识别的文字"}
      }
    ]
  }
}
```

### GET /health

健康检查端点。

**响应：**
```json
{"status": "ok"}
```

## 开发注意事项

1. **macOS 限制**：ocrmac 库仅在 macOS 上可用
2. **临时文件**：始终使用 `with tempfile.TemporaryDirectory()` 管理临时文件
3. **测试隔离**：单元测试使用 mock，集成测试需要真实服务
4. **路径设置**：测试文件通过 conftest.py 自动设置项目路径
