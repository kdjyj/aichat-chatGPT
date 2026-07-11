import re
import os
import base64
import random
import urllib.request
from hoshino import Service
from hoshino.typing import CQEvent
from . import Config
from .client import Client
from hoshino.tools import anti_conflict

help_text = """命令(人格可以替换为会话)
1. `创建人格/新建人格/设置人格+人格名+空格+设定`: 创建新人格或修改现有人格，注意人格名不能大于24位
2. `查询人格/人格列表/获取人格`: 获取当前所有人格及当前人格
3. `选择人格/切换人格/默认人格+人格名`: 切换到对应人格，不填则使用默认人格
4. `/t+消息或@bot+消息`: 前面加上记住两字可以让关闭记忆功能的bot记住对话，记住两字不会放入对话。支持发送图片进行识别。
5. `重置人格/重置会话+人格名`: 重置人格，不填则重置当前人格，无当前人格则重置默认人格
6. `对话记忆+on/off`: 开启/关闭对话记忆，不加则返回当前状态
7. `删除会话+会话名` : 删除会话，不填则删除当前会话，默认会话不可删除
8. `删除对话+条数`: 删除倒数N条对话，负数则是从第N条开始删除，不加条数则删除上一条。1条对话指一次问与答，不需要乘2。
9. `ai配置重载`: 重新加载配置文件，更新key等配置后使用
"""

sv = Service('ai对话', enable_on_default=False, help_=help_text)

black_word = ['今天我是什么少女', 'ba来一井']  # 如果有不想触发的词可以填在这里

cq_code_pattern = re.compile(r'\[CQ:\w+,.+\]')
image_pattern = re.compile(r'\[CQ:image[^\]]*\]')
image_tag_pattern = re.compile(r'\[CQ:image(?:,([^\]]+))?\]')
config = Config()
group_clients = {}
count = 0


def extract_images_from_message(message_str):
    """从CQ码消息字符串中提取图片信息
    
    Returns:
        list: 图片信息列表，每项为 dict，包含 'url' 或 'file' 字段
    """
    images = []
    matches = image_tag_pattern.finditer(message_str)
    for match in matches:
        params_str = match.group(1) or ""
        params = {}
        for param in params_str.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value
        
        file_id = params.get("file", "")
        url = params.get("url", "")
        
        image_info = {}
        if url:
            image_info["url"] = url
        if file_id:
            image_info["file"] = file_id
        if image_info:
            images.append(image_info)
    return images


def _to_data_uri(raw_bytes, file_name=""):
    """将图片字节转换为 data URI。"""
    ext = os.path.splitext(file_name)[1].lower()
    mime = "image/jpeg"
    if ext == ".png":
        mime = "image/png"
    elif ext == ".webp":
        mime = "image/webp"
    elif ext == ".gif":
        mime = "image/gif"
    encoded = base64.b64encode(raw_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _download_as_data_uri(url):
    """下载远程图片并转换为 data URI。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
        return _to_data_uri(data)
    except Exception:
        return None


async def get_image_data(bot, image_info):
    """将图片信息转换为API可用的格式
    
    Returns:
        str: 图片URL或base64 data URI
    """
    image_url = image_info.get("url", "")
    file_id = image_info.get("file", "")

    # 优先使用可下载 URL，转换为 data URI，避免模型端下载失败
    if image_url and image_url.startswith("http"):
        data_uri = _download_as_data_uri(image_url)
        if data_uri:
            return data_uri

    # 通过 OneBot 接口获取图片真实路径/URL
    if file_id and bot is not None:
        try:
            image_info_resp = await bot.get_image(file=file_id)
            local_file = image_info_resp.get("file", "")
            remote_url = image_info_resp.get("url", "")

            if local_file and os.path.exists(local_file):
                with open(local_file, "rb") as f:
                    return _to_data_uri(f.read(), local_file)

            if remote_url and remote_url.startswith("http"):
                data_uri = _download_as_data_uri(remote_url)
                if data_uri:
                    return data_uri
        except Exception:
            pass

    # 回退本地路径尝试
    if file_id:
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "data", "image", file_id),
            os.path.join(os.path.dirname(__file__), file_id),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return _to_data_uri(f.read(), path)

    # 最后回退 URL 直传（若为公网可访问地址仍可用）
    if image_url and image_url.startswith("http"):
        return image_url
    if file_id.startswith("http"):
        return file_id
    return None


async def process_images(bot, message_str, max_images=3):
    """从消息中提取并处理图片
    
    Args:
        message_str: 原始CQ码消息字符串
        max_images: 最大图片数量
        
    Returns:
        tuple: (图片URL列表, 去除图片CQ码后的纯文本)
    """
    images_info = extract_images_from_message(message_str)
    
    if not images_info:
        return [], message_str
    
    # 限制图片数量
    if len(images_info) > max_images:
        images_info = images_info[:max_images]
    
    image_urls = []
    for img_info in images_info:
        url = await get_image_data(bot, img_info)
        if url:
            image_urls.append(url)
    
    # 去除图片CQ码，保留纯文本
    text = image_pattern.sub("", message_str).strip()
    
    return image_urls, text


@sv.on_fullmatch('AI配置重载')
async def get_config(bot, ev):
    global config
    config = Config()

def create_client(group_id):
    client = Client(
        random.choice(config.api_keys),
        config.model,
        config.max_tokens,
        config.proxy,
        config.api_base,
        config.api_type,
        config.api_version,
        config.vision_model
    )
    conversation = "default"
    if group_id in config.groups:
        conversation = config.groups[group_id]
        if conversation not in config.conversations:
            conversation = "default"
    client.conversation = conversation
    client.messages = config.conversations[client.conversation]
    group_clients[group_id] = client
    return


async def get_chat_response(group_id, prompt, image_urls=None):
    group_id = str(group_id)
    record = config.record
    if not record and prompt.startswith("记住"):
        # prompt = prompt.removeprefix("记住")
        prompt = prompt[2:]
        record = True
    api_key = random.choice(config.api_keys)
    if group_id not in group_clients:
        create_client(group_id)
    client: Client = group_clients[group_id]
    client.chat.api_key = api_key
    try:
        if image_urls:
            msg = await client.send_with_images(prompt, image_urls, record)
        else:
            msg = await client.send(prompt, record)
        if record:
            config.conversations[client.conversation] = client.messages
            config.groups[group_id] = client.conversation
            global count
            count += 1
            if config.interval > 0 and count % config.interval == 0:
                config.save_conversations()
                config.save_config()
        return msg
    except Exception as e:
        print(e)
        err = str(e) if len(str(e)) < 133 else str(e)[:133]
        return f"发生错误: {err}"


@sv.on_message('group')
@anti_conflict
async def ai_reply(bot, context):
    msg = str(context['message'])
    if msg.startswith(f'[CQ:at,qq={context["self_id"]}]'):
        # 提取图片
        image_urls, text = await process_images(bot, msg, config.max_images)
        text = re.sub(cq_code_pattern, '', text).strip()
        if text == '' and not image_urls:
            return
        if text in black_word:
            return
        try:
            prompt = text if text else "图片是"
            msg = await get_chat_response(context["group_id"], prompt, image_urls if image_urls else None)
            if msg:
                await bot.send(context, msg, at_sender=False)
        except Exception as err:
            print(err)


@sv.on_prefix('/t')
async def ai_reply_prefix(bot, ev: CQEvent):
    raw_msg = str(ev['message'])
    # 提取图片
    image_urls, text = await process_images(bot, raw_msg, config.max_images)
    text = text.strip()
    if text == '' and not image_urls:
        return
    if text in black_word:
        return
    try:
        prompt = text if text else "请描述这张图片"
        msg = await get_chat_response(ev.group_id, prompt, image_urls if image_urls else None)
        if msg:
            await bot.send(ev, msg)
    except Exception as err:
        print(err)


@sv.on_prefix(('新建人格', '创建人格', '新建会话', '创建会话', '设置人格', '设置会话'))
async def set_conversation(bot, ev: CQEvent):
    args = str(ev.message.extract_plain_text()).strip().split(" ", 1)
    if len(args) != 2:
        await bot.send(ev, "参数错误，请输入人格名+空格+预设语句")
        return
    name = args[0]
    text = args[1]
    if len(name) > 24:
        await bot.send(ev, "人格名过长")
        return
    msg = [{"role": "system", "content": text}]
    config.conversations[name] = msg
    config.save_conversations()
    if str(ev.group_id) in group_clients:
        group_clients[str(ev.group_id)].conversation = name
        group_clients[str(ev.group_id)].messages = msg
    await bot.send(ev, f"{name}创建完成")


@sv.on_prefix(('删除人格', '删除会话'))
async def delete_conversation(bot, ev: CQEvent):
    name = str(ev.message.extract_plain_text()).strip()
    if name == "":
        if str(ev.group_id) in group_clients:
            name = group_clients[str(ev.group_id)].conversation
            if name != "default":
                group_clients[str(ev.group_id)].conversation = "default"
                group_clients[str(ev.group_id)].messages = config.conversations["default"]
        else:
            await bot.send(ev, "当前无会话，请指定要删除的会话")
            return
    if name == "default":
        await bot.send(ev, "默认会话不可删除")
        return
    if name not in config.conversations:
        await bot.send(ev, "人格不存在")
        return
    del config.conversations[name]
    config.save_conversations()
    await bot.send(ev, f"{name}删除成功")


def save_data(group_id, conversation, messages):
    global config
    config.conversations[conversation] = messages
    config.groups[str(group_id)] = conversation
    config.save_conversations()
    config.save_config()


@sv.on_prefix(('选择人格', '选择会话', '切换人格', '切换会话', '默认人格', '默认会话'))
async def change_conversation(bot, ev: CQEvent):
    name = str(ev.message.extract_plain_text()).strip()
    if name == "":
        name = "default"
    group_id = str(ev.group_id)
    if group_id not in group_clients:
        create_client(group_id)
    if name in config.conversations:
        save_data(group_id, name, config.conversations[name])
        client = group_clients[group_id]
        client.conversation = name
        client.messages = config.conversations[name]
        await bot.send(ev, "切换完成")
    else:
        await bot.send(ev, "此人格不存在，可以使用`人格列表`命令获取现有人格。")


@sv.on_fullmatch(('查询人格', '获取人格', '人格列表', '会话列表', '获取会话', '查询会话'))
async def list_conversation(bot, ev: CQEvent):
    group_id = str(ev.group_id)
    name = config.groups[group_id] if group_id in config.groups else "default"
    msg = f"当前人格：{name}\n人格列表({len(config.conversations)})：\n"
    for k in config.conversations:
        msg += f"{k}、"
    await bot.send(ev, msg.strip("、"))


@sv.on_prefix(('重置人格', '重置会话'))
async def reset_conversation(bot, ev: CQEvent):
    group_id = str(ev.group_id)
    name = str(ev.message.extract_plain_text()).strip()
    if name == "":
        if group_id in config.groups:
            name = config.groups[group_id]
        else:
            name = "default"
    if name in config.conversations:
        config.conversations[name] = config.conversations[name][:1]
        config.save_conversations()
        for client in group_clients.values():
            if client.conversation == name:
                client.messages = config.conversations[name]
        await bot.send(ev, "重置成功")


@sv.on_prefix('删除对话')
async def del_msg(bot, ev: CQEvent):
    group_id = str(ev.group_id)
    p = str(ev.message.extract_plain_text()).strip()
    num = 2
    if p != "" and p.lstrip('-').isdigit():
        num = int(p) * 2
    if num == 0:
        await bot.send(ev, "禁止删除设定")
        return
    if group_id not in group_clients:
        create_client(group_id)
    client = group_clients[group_id]
    m = len(client.messages) - 1
    if m % 2 == 1:
        m = m - 1
    if m < 1:
        await bot.send(ev, "没有可以删除的对话")
        return
    if num < m:
        if -num > m:
            await bot.send(ev, f"只能从第{str(int(m / 2))}条对话开始删除")
            return
        del client.messages[-num:]
        config.conversations[client.conversation] = client.messages
        config.save_conversations()
        # 覆盖其他Client
        for gid,c in group_clients.items():
            if gid == group_id:
                continue
            if c.conversation == client.conversation:
                c.messages = client.messages
        await bot.send(ev, "删除成功")
    else:
        await bot.send(ev, f"最多只能删除{str(int(m / 2) - 1)}条对话")


@sv.on_prefix('对话记忆')
async def set_record(bot, ev: CQEvent):
    cfg = str(ev.message.extract_plain_text()).strip()
    if cfg == "on":
        config.record = True
        await bot.send(ev, "对话记忆已开启")
    elif cfg == "off":
        config.record = False
        await bot.send(ev, "对话记忆已关闭")
    else:
        if config.record:
            await bot.send(ev, "当前对话记忆状态：开启")
        else:
            await bot.send(ev, "当前对话记忆状态：关闭")
        return
    config.save_config()
