import base64
import os
import openai


class Client:
    chat = openai.ChatCompletion()
    model: str = "qwen3.6-flash"
    vision_model: str = "qwen3.6-flash"
    enable_thinking: bool = False
    conversation: str = ""
    messages: list = []
    max_tokens: int = 1000


    def __init__(self, api_key="", model="qwen3.6-flash", max_tokens=1000, proxy="", api_base="", api_type="open_ai", api_version="", vision_model="qwen-vl-plus", enable_thinking=False):
        self.chat.api_key = api_key

        if proxy.strip() != "":
            openai.proxy = {'http': proxy}
        if api_base.strip() != "":
            openai.verify_ssl_certs = False
            openai.api_base = api_base
        if api_version.strip() != "":
            openai.api_version = api_version
        openai.api_type = api_type
        self.model = model
        self.vision_model = vision_model
        self.enable_thinking = enable_thinking
        self.max_tokens = max_tokens
        self.conversation = "default"
        self.messages = [
            {"role": "system", "content": "你是一个AI助手"},
        ]

    def load_conversation(self, conversation, message):
        self.conversation = conversation
        self.messages = message

    def _request_kwargs(self, model_name):
        kwargs = {
            "model": model_name,
            "engine": model_name if openai.api_type == "azure" else None,
            "messages": self.messages,
            "max_tokens": self.max_tokens,
        }
        if openai.api_type != "azure" and self.enable_thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        return kwargs

    @staticmethod
    def _extract_model_output(response):
        choice = response.choices[0]
        message = choice.message
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content", "")
        reasoning = getattr(message, "reasoning_content", None)
        if reasoning is None and isinstance(message, dict):
            reasoning = message.get("reasoning_content", "")
        return (content or "").strip(), (reasoning or "").strip()

    def _format_output(self, content, reasoning):
        if self.enable_thinking and reasoning:
            if content:
                return f"思考内容：\n{reasoning}\n\n回复：\n{content}"
            return f"思考内容：\n{reasoning}"
        return content

    async def send(self, message, record=True):
        openai.api_key = self.chat.api_key
        self.messages.append({"role": "user", "content": message})
        try:
            response = await self.chat.acreate(
                **self._request_kwargs(self.model),
                timeout=30
            )
            if response.choices[0]['finish_reason'] == "content_filter":
                self.messages = self.messages[:-1]
                return "由于敏感内容被过滤，未返回消息"
            content, reasoning = self._extract_model_output(response)
            msg = self._format_output(content, reasoning)
            if content and record:
                self.messages.append({"role": "assistant", "content": content})
            else:
                self.messages = self.messages[:-1]

            #token过长删除最早两条对话
            if response['usage']['total_tokens'] > 3800 - self.max_tokens:
                del self.messages[1:5]

            return msg.strip()
        except Exception as e:
            self.messages = self.messages[:-1]
            if "This model's maximum context length is" in str(e):
                del self.messages[1:5]
                return "对话过长，已删除部分对话"
            if "Rate limit reached for" in str(e):
                return "API请求过于频繁，请稍后再试"
            if "You exceeded your current quota" in str(e):
                return f"api key({openai.api_key[0:len(openai.api_key)-8]}********)配额已用完，请更换api key"
            return f"发生错误: {str(e).strip()}"

    async def send_with_images(self, text, image_urls, record=True):
        """发送包含图片的多模态消息
        
        Args:
            text: 文本内容
            image_urls: 图片URL列表（支持http URL和base64 data URI）
            record: 是否记录对话
        """
        openai.api_key = self.chat.api_key
        
        # 构建多模态消息内容
        content = []
        if text:
            content.append({"type": "text", "text": text})
        for img_url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })
        
        user_message = {"role": "user", "content": content}
        self.messages.append(user_message)
        
        try:
            response = await self.chat.acreate(
                **self._request_kwargs(self.vision_model),
                timeout=60
            )
            if response.choices[0]['finish_reason'] == "content_filter":
                self.messages = self.messages[:-1]
                return "由于敏感内容被过滤，未返回消息"
            content, reasoning = self._extract_model_output(response)
            msg = self._format_output(content, reasoning)
            if content and record:
                # 存储时只记录最终回复，避免把推理内容写入上下文
                self.messages.append({"role": "assistant", "content": content})
            else:
                self.messages = self.messages[:-1]
            
            # token过长删除最早两条对话
            if response['usage']['total_tokens'] > 3800 - self.max_tokens:
                del self.messages[1:5]
            
            return msg.strip()
        except Exception as e:
            self.messages = self.messages[:-1]
            err_str = str(e)
            if "This model's maximum context length is" in err_str:
                del self.messages[1:5]
                return "对话过长，已删除部分对话"
            if "Rate limit reached for" in err_str:
                return "API请求过于频繁，请稍后再试"
            if "You exceeded your current quota" in err_str:
                return f"api key({openai.api_key[0:len(openai.api_key)-8]}********)配额已用完，请更换api key"
            return f"发生错误: {err_str.strip()}"
