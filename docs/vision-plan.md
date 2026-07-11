# Vision 图片理解 - 工作计划

## 功能概述

支持用户发送图片，AI 能够理解图片内容并进行描述、分析、问答等操作。

## 技术方案

### 1. CQ码图片解析

从消息中提取 `[CQ:image,file=xxx]` 数据：

```python
import re
import base64
import aiohttp

async def extract_images(message):
    """从消息中提取图片"""
    pattern = r'\[CQ:image,file=([^\]]+)\]'
    matches = re.findall(pattern, message)
    images = []
    for file_id in matches:
        # 获取图片数据（URL或本地路径）
        image_data = await get_image_data(file_id)
        images.append(image_data)
    return images
```

### 2. 图片数据处理

支持两种图片来源：
- **URL图片**: 直接传递给 API
- **本地图片**: 读取并 base64 编码

```python
async def get_image_data(file_id):
    """获取图片数据"""
    # 如果是URL
    if file_id.startswith('http'):
        return {"url": file_id}
    # 如果是本地文件（需要HoshinoBot的文件管理API）
    else:
        # 读取文件并base64编码
        with open(file_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        return {"base64": data}
```

### 3. 多模态消息构建

构建 OpenAI Vision API 的消息格式：

```python
def build_vision_message(text, images):
    """构建多模态消息"""
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for img in images:
        if "url" in img:
            content.append({
                "type": "image_url",
                "image_url": {"url": img["url"]}
            })
        elif "base64" in img:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img['base64']}"}
            })
    return {"role": "user", "content": content}
```


## 实现步骤

### Phase 1: 图片解析（1-2天）
- [ ] 实现 CQ码图片正则提取
- [ ] 实现 URL 图片处理
- [ ] 实现本地图片 base64 编码
- [ ] 处理多图场景

### Phase 2: API集成（1-2天）
- [ ] 修改 `client.py` 支持多模态消息
- [ ] 添加 vision 模型配置
- [ ] 处理图片 token 计算（图片占用 token 较多）
- [ ] 错误处理（不支持的模型、图片过大等）

### Phase 3: 命令与交互（1天）
- [ ] 自动检测图片并调用 vision 模型
- [ ] 或添加显式命令（如 `/img 描述这张图片`）
- [ ] 更新 `help_text`

### Phase 4: 测试与优化（1天）
- [ ] 测试单图/多图场景
- [ ] 测试大图片处理
- [ ] 优化图片 token 消耗
- [ ] 添加使用示例

## 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `client.py` | 支持多模态消息格式，添加 vision 模型配置 |
| `aichat.py` | 图片消息处理逻辑 |
| `config.ini` | 添加 `vision_model` 配置 |
| `__init__.py` | 加载 vision 配置 |

## 测试要点

1. 单图描述：发送一张图片，AI 描述内容
2. 多图对比：发送多张图片，AI 对比分析
3. 图文混合：文字+图片，AI 理解上下文
4. 大图片：超过尺寸限制时的处理
5. 模型降级：vision 模型不可用时的提示

## 注意事项

- 图片 token 消耗较大（一张图约 1000+ tokens）
- 需要限制单次图片数量（建议最多3张）
- 本地图片需要 HoshinoBot 的文件管理 API 支持
- 某些图片格式可能不支持（建议统一转 JPEG）
- Vision API 响应较慢，需要提示用户等待
