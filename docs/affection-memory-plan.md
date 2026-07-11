# 好感度/长期记忆系统 - 工作计划

## 功能概述

为每个群成员建立长期记忆，包括好感度数值、关键信息记录、偏好等，让 AI 能够"记住"每个用户，提供更个性化的回复。

## 技术方案

### 1. 数据存储结构

创建独立的成员记忆文件 `members.json`：

```json
{
  "group_123456": {
    "user_789": {
      "nickname": "小明",
      "affection": 50,
      "created_at": "2024-01-01",
      "last_interaction": "2024-01-15",
      "interaction_count": 42,
      "traits": ["喜欢猫", "程序员", "熬夜党"],
      "memories": [
        {"date": "2024-01-10", "content": "提到喜欢养猫"},
        {"date": "2024-01-12", "content": "说自己是程序员"}
      ],
      "preferences": {
        "topic": ["技术", "游戏"],
        "style": "轻松幽默"
      }
    }
  }
}
```

### 2. 好感度系统

设计好感度数值系统（0-100）：

```python
AFFECTION_LEVELS = {
    (0, 20): "陌生",
    (21, 40): "熟悉",
    (41, 60): "友好",
    (61, 80): "亲密",
    (81, 100): "挚友"
}

def update_affection(group_id, user_id, delta):
    """更新好感度"""
    member = get_member(group_id, user_id)
    member['affection'] = max(0, min(100, member['affection'] + delta))
    save_member(group_id, user_id, member)
```

好感度变化规则：
- 每次互动 +1
- 连续互动（同一天多次） +2
- 长时间未互动（>7天） -1/天
- 被夸奖 +3
- 被骂 -5

### 3. 长期记忆提取

使用 AI 自动从对话中提取关键信息：

```python
async def extract_memory(user_message, ai_response):
    """从对话中提取记忆"""
    prompt = f"""
    从以下对话中提取用户的关键信息（兴趣、职业、偏好等）：
    用户: {user_message}
    AI: {ai_response}
    
    请返回JSON格式：
    {{"traits": ["特征1", "特征2"], "memory": "一句话总结"}}
    """
    result = await call_llm(prompt)
    return json.loads(result)
```

### 4. 记忆注入

在 system prompt 中注入相关记忆：

```python
def build_system_prompt_with_memory(group_id, user_id, base_prompt):
    """构建带记忆的system prompt"""
    member = get_member(group_id, user_id)
    if not member:
        return base_prompt
    
    # 注入好感度和特征
    memory_text = f"""
    当前对话用户信息：
    - 昵称: {member['nickname']}
    - 好感度: {member['affection']} ({get_affection_level(member['affection'])})
    - 特征: {', '.join(member['traits'][:5])}
    - 最近记忆: {member['memories'][-3:] if member['memories'] else '无'}
    
    请根据以上信息，以符合好感度的语气回复。
    """
    return base_prompt + memory_text
```

### 5. 定期总结

避免记忆无限增长，定期总结：

```python
async def summarize_memories(group_id, user_id):
    """总结用户记忆"""
    member = get_member(group_id, user_id)
    if len(member['memories']) > 20:
        # 使用AI总结旧记忆
        prompt = f"请总结以下记忆的关键信息：{member['memories'][:10]}"
        summary = await call_llm(prompt)
        member['memories'] = [summary] + member['memories'][10:]
        save_member(group_id, user_id, member)
```

## 实现步骤

### Phase 1: 数据模型（2天）
- [ ] 设计 `members.json` 数据结构
- [ ] 实现 `MemberManager` 类（CRUD操作）
- [ ] 实现好感度计算逻辑
- [ ] 实现数据持久化（自动保存）

### Phase 2: 记忆提取（2-3天）
- [ ] 实现对话记忆提取 prompt
- [ ] 在每次对话后自动提取记忆
- [ ] 实现记忆去重和合并
- [ ] 实现记忆总结机制

### Phase 3: 记忆注入（1-2天）
- [ ] 修改 `get_chat_response()` 注入记忆
- [ ] 根据好感度调整回复风格
- [ ] 实现记忆查询命令（如 `我的记忆`）
- [ ] 实现记忆管理命令（如 `删除记忆`）

### Phase 4: 好感度系统（1-2天）
- [ ] 实现好感度自动增减
- [ ] 实现好感度等级
- [ ] 实现好感度查询命令
- [ ] 根据好感度调整回复语气

### Phase 5: 测试与优化（2天）
- [ ] 测试记忆提取准确性
- [ ] 测试好感度变化
- [ ] 优化记忆注入 prompt
- [ ] 性能优化（大量成员时）

## 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `memory.py` | 新建，成员记忆管理 |
| `aichat.py` | 集成记忆系统，添加管理命令 |
| `client.py` | 修改 `send()` 支持记忆注入 |
| `config.ini` | 添加记忆系统配置 |
| `members.json` | 新建，成员数据存储 |

## 测试要点

1. 记忆提取：对话后自动提取关键信息
2. 记忆注入：AI 回复时引用用户记忆
3. 好感度变化：互动后好感度正确增减
4. 记忆总结：大量记忆时正确总结
5. 多群隔离：不同群的记忆独立

## 注意事项

- 记忆提取会消耗额外 token 和 API 调用
- 需要控制记忆大小，避免文件过大
- 好感度系统需要平衡，避免滥用
- 需要考虑隐私问题（用户可能不希望被记录）
- 建议添加全局开关和群级开关

## 进阶功能

- **记忆共享**: 群内成员记忆可以共享（如"大家都知道小明喜欢猫"）
- **记忆过期**: 旧记忆自动过期删除
- **记忆标签**: 给记忆打标签，方便检索
- **记忆搜索**: 搜索特定主题的记忆
- **好感度成就**: 达到特定好感度解锁特殊回复
