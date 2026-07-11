import configparser
import json
import os

class Config:
    _config = configparser.ConfigParser()
    api_keys: list = []  # api key
    model: str = "qwen3.6-flash"  # 模型
    record: bool = True  # 是否记录对话
    conversations: dict = {}  # 会话列表
    groups: dict = {}  # 群组列表
    interval: int = 5  # 存档间隔
    max_tokens: int = 1000  # 最大字符数
    proxy: str = ""  # 代理
    api_base : str = ""
    api_type : str = "open_ai"
    api_version : str = ""
    vision_model: str = "qwen3.6-flash"  # 视觉理解模型
    max_images: int = 3  # 单次最大图片数量
    enable_thinking: bool = False  # 是否开启思考模式

    def __init__(self):
        self._config.read(os.path.join(os.path.dirname(__file__), 'config.ini'), encoding='utf-8')
        self.load_conversations()
        api_keys = self._config.get("OPTION", "api_key", fallback="")
        self.api_keys = api_keys.split(",")
        self.model = self._config.get("OPTION", "model", fallback="qwen3.6-flash")
        self.record = self._config.getboolean("OPTION", "record", fallback=True)
        self.interval = self._config.getint("OPTION", "interval", fallback=5)
        self.max_tokens = self._config.getint("OPTION", "max_tokens", fallback=1000)
        self.proxy = self._config.get("OPTION", "proxy", fallback="")
        self.api_base = self._config.get("OPTION", "api_base", fallback="")
        self.api_type = self._config.get("OPTION", "api_type", fallback="open_ai")
        self.api_version = self._config.get("OPTION", "api_version", fallback="")
        self.vision_model = self._config.get("OPTION", "vision_model", fallback="qwen3.6-flash")
        self.max_images = self._config.getint("OPTION", "max_images", fallback=3)
        self.enable_thinking = self._config.getboolean("OPTION", "enable_thinking", fallback=False)
        items = self._config.items("GROUP")
        for item in items:
            if item[1] in self.conversations:
                self.groups[item[0]] = item[1]
            else:
                self.groups[item[0]] = "default"

    def save_conversations(self):
        with open(os.path.join(os.path.dirname(__file__), 'conversations.json'), 'w', encoding='utf-8') as f:
            json.dump(self.conversations, f, ensure_ascii=False, indent=4)

    def load_conversations(self):
        with open(os.path.join(os.path.dirname(__file__), 'conversations.json'), 'r', encoding='utf-8') as f:
            self.conversations = json.load(f)

    def save_config(self):
        for group in self.groups:
            if self.groups[group] not in self.conversations:
                self._config.set("GROUP", group, "default")
            else:
                self._config.set("GROUP", group, self.groups[group])
        self._config.set("OPTION", "record", str(self.record).lower())
        self._config.set("OPTION", "enable_thinking", str(self.enable_thinking).lower())
        with open(os.path.join(os.path.dirname(__file__), 'config.ini'), 'w', encoding='utf-8') as f:
            self._config.write(f)
