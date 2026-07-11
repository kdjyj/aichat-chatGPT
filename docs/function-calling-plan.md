# Function Calling 工具调用 - 工作计划

## 功能概述

让 AI 能够调用外部工具（天气查询、网页搜索、数学计算等），在对话中自动识别需要工具辅助的场景并执行相应操作。

## 技术方案

### 1. 工具定义结构

在 `client.py` 中定义工具描述（JSON Schema 格式）：

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    },
    # 更多工具...
]
```

### 2. 工具执行器

创建 `tools.py` 模块，实现工具注册和执行：

```python
class ToolExecutor:
    def __init__(self):
        self.tools = {}
    
    def register(self, name, func):
        self.tools[name] = func
    
    async def execute(self, name, args):
        if name in self.tools:
            return await self.tools[name](**args)
        return None
```

### 3. 内置工具实现

- **天气查询**: 调用天气 API（如和风天气、OpenWeatherMap）
- **数学计算**: 使用 `sympy` 或 `eval`（安全沙箱）
- **时间查询**: 返回当前时间/日期
- **网页搜索**: 调用搜索 API（可选，需要 API key）

### 4. 消息流改造

修改 `Client.send()` 处理 `finish_reason: "tool_calls"`：

```python
async def send(self, message, record=True):
    # ... 现有代码 ...
    response = await self.chat.acreate(..., tools=TOOLS)
    
    if response.choices[0].finish_reason == "tool_calls":
        # 执行工具调用
        tool_calls = response.choices[0].message.tool_calls
        for tool_call in tool_calls:
            result = await tool_executor.execute(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )
            # 将结果追加到 messages
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })
        # 再次调用 API 获取最终回复
        response = await self.chat.acreate(..., messages=self.messages)
```

## 实现步骤

### Phase 1: 基础架构（2-3天）
- [ ] 创建 `tools.py`，实现 `ToolExecutor` 类
- [ ] 定义工具 JSON Schema 结构
- [ ] 修改 `client.py` 支持 `tools` 参数
- [ ] 处理 `finish_reason: "tool_calls"` 响应

### Phase 2: 内置工具（2-3天）
- [ ] 实现天气查询工具（需要 API key）
- [ ] 实现数学计算工具
- [ ] 实现时间查询工具
- [ ] 测试工具执行和错误处理

### Phase 3: 配置与管理（1-2天）
- [ ] 在 `config.ini` 添加工具开关配置
- [ ] 在 `aichat.py` 添加工具管理命令（如 `工具列表`、`启用工具`）
- [ ] 更新 `help_text` 和 `README.md`

### Phase 4: 测试与优化（1-2天）
- [ ] 测试多工具并发调用
- [ ] 测试工具调用失败降级
- [ ] 优化 token 消耗（工具描述占用 token）
- [ ] 添加使用示例文档

## 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `client.py` | 添加 `tools` 参数支持，处理 tool_calls 响应 |
| `tools.py` | 新建，工具注册和执行器 |
| `aichat.py` | 添加工具管理命令 |
| `config.ini` | 添加工具配置项 |
| `__init__.py` | 加载工具配置 |

## 测试要点

1. 单工具调用：用户问"北京天气怎么样"，AI 调用天气工具并返回结果
2. 多工具调用：用户问"计算 123*456 并告诉我现在几点"
3. 工具失败降级：API 不可用时返回友好提示
4. Token 限制：工具描述过长时的处理

## 注意事项

- 工具描述会占用 token，需要控制工具数量
- 工具执行可能有延迟，考虑超时机制
- 某些工具需要 API key，需要在配置中管理
- 工具结果需要格式化，避免过长
