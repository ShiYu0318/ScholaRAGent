"""工具註冊表：把本地 Python 函式暴露成 OpenAI 相容的 tool schema，
供 Groq function calling 呼叫。"""
import json

from src.utils.logger import get_logger


class Tool:
    def __init__(self, name, description, parameters, func):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON schema（properties/required）
        self.func = func

    def spec(self):
        """OpenAI/Groq tools 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", []),
                },
            },
        }


class ToolRegistry:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._tools = {}

    def register(self, name, description, parameters, func):
        self._tools[name] = Tool(name, description, parameters, func)
        return self

    def specs(self):
        return [t.spec() for t in self._tools.values()]

    def names(self):
        return list(self._tools)

    def execute(self, name, arguments):
        """執行工具，arguments 可為 dict 或 JSON 字串；回傳字串結果。"""
        tool = self._tools.get(name)
        if tool is None:
            return f"（未知工具：{name}）"
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                return f"（工具參數解析失敗：{arguments}）"
        try:
            result = tool.func(**arguments)
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"工具 {name} 執行失敗：{e}")
            return f"（工具 {name} 執行錯誤：{e}）"
