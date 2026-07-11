# 群聊上下文感知 - 工作计划

## 功能概述

让 AI 能够感知群内最近的聊天内容，不仅限于 @触发，还能理解群聊上下文，提供更自然的回复。

## 技术方案

### 1. 消息缓存机制

在内存中维护每个群的消息历史：

```python
# aichat.py
group_messages = {}  # {group_id: [message_list]}
MAX_CONTEXT = 10  # 最多缓存10条消息

@sv.on_message('group')
async def cache_message(bot, context):
    """缓存群消息"""
    group_id = str(context['group_id'])
    if group_id not in group_messages:
        group_messages[group_id] = []
    
    msg = {
        "user_id": context['user_id'],
        "nickname": context.get('sender', {}).get('nickname', ''),
        "message": str(context['message']),
        "time": context['time']
    }
    group_messages[group_id].append(msg)
    
    # 保持缓存大小
    if len(group_messages[group_id]) > MAX_CONTEXT:
        group_messages[group_id] = group_messages[group_id][-MAX_CONTEXT:]
```

### 2. 上下文组装

在 AI 回复时，将缓存消息组装进 prompt：

```python
def build_context_prompt(group_id, user_message):
    """构建带上下文的prompt"""
    if group_id not in group_messages:
        return user_message
    
    context_lines = []
    for msg in group_messages[group_id][-5:]:  # 最近5条
        context_lines.append(f"{msg['nickname']}: {msg['message']}")
    
    context_text = "\n".join(context_lines)
    return f"以下是群内最近的对话：\n{context_text}\n\n现在{user_message}，请回复。"
```

### 3. 发言者识别

区分不同发言者，使用 QQ号→昵称 映射：

```python
def format_context(messages):
    """格式化上下文，区分发言者"""
    lines = []
    for msg in messages:
        # 使用群昵称或QQ号
        name = msg.get('nickname') or f"用户{msg['user_id']}"
        lines.append(f"[{name}]: {msg['message']}")
    return "\n".join(lines)
```

### 4. 配置化

在 `config.ini` 添加上下文相关配置：

```ini
[OPTION]
# 是否启用群聊上下文
context_enabled = true
# 上下文消息数量
context_size = 10
# 是否包含自己的消息
include_self = false
```

## 实现步骤

### Phase 1: 消息缓存（1-2天）
- [ ] 实现 `group_messages` 全局缓存
- [ ] 在 `@sv.on_message('group')` 中缓存消息
- [ ] 实现缓存大小控制（LRU或固定大小）
- [ ] 处理消息去重（避免重复缓存）

### Phase 2: 上下文组装（1-2天）
- [ ] 实现 `build_context_prompt()` 函数
- [ ] 在 `get_chat_response()` 中调用上下文组装
- [ ] 处理上下文 token 限制（避免过长）
- [ ] 支持配置开关

### Phase 3: 发言者识别（1天）
- [ ] 从 `CQEvent` 提取发送者信息
- [ ] 实现 QQ号→昵称 映射
- [ ] 格式化上下文消息（区分发言者）
- [ ] 处理匿名消息

### Phase 4: 优化与测试（1-2天）
- [ ] 优化上下文 token 消耗
- [ ] 测试多群并发场景
- [ ] 测试上下文对回复质量的影响
- [ ] 添加配置命令（如 `上下文大小 10`）

## 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `aichat.py` | 添加消息缓存、上下文组装逻辑 |
| `config.ini` | 添加上下文配置项 |
| `__init__.py` | 加载上下文配置 |

## 测试要点

1. 基本上下文：群内聊天后 @bot，AI 能理解上下文
2. 多发言者：不同人聊天，AI 能区分发言者
3. 上下文大小：配置不同大小，测试效果
4. Token 限制：上下文过长时的处理
5. 性能：高并发群的消息缓存性能

## 注意事项

- 上下文会占用额外 token，需要控制大小
- 不是所有消息都需要缓存（如命令消息）
- 需要考虑隐私问题（某些群可能不希望记录）
- 上下文组装的 prompt 需要精心设计，避免混淆 AI
- 建议添加群级开关，允许群主禁用上下文

## 进阶优化

- **智能过滤**: 只缓存有意义的消息（过滤表情、重复内容）
- **时间衰减**: 越久远的消息权重越低
- **主题相关**: 只缓存与当前话题相关的消息
- **摘要压缩**: 对长上下文进行摘要，减少 token 消耗
