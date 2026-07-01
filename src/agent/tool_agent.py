"""工具呼叫 agent：驅動 LLM 進行 function calling 的多步迴圈。

client 需為 OpenAI 相容用戶端（Groq 亦相容），具
`client.chat.completions.create(model, messages, tools, tool_choice)`。
"""
from src.utils.logger import get_logger

_DEFAULT_SYSTEM = (
    "你是 AIR Agent 的智慧助理。可使用提供的工具查論文、看趨勢、管理待辦。"
    "需要外部資料時務必呼叫工具，不要臆測。最後用繁體中文簡潔回覆使用者。"
)


class ToolAgent:
    def __init__(self, client, registry, model, system=None):
        self.logger = get_logger(self.__class__.__name__)
        self.client = client
        self.registry = registry
        self.model = model
        self.system = system or _DEFAULT_SYSTEM

    def _assistant_msg_to_dict(self, msg):
        out = {"role": "assistant", "content": msg.content or ""}
        if getattr(msg, "tool_calls", None):
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        return out

    def run(self, user_message, max_steps=5):
        """跑完工具呼叫迴圈，回傳最終文字回覆。"""
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": user_message},
        ]
        for _ in range(max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.registry.specs(),
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                return (msg.content or "").strip()

            messages.append(self._assistant_msg_to_dict(msg))
            for tc in tool_calls:
                result = self.registry.execute(tc.function.name, tc.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        # 達到步數上限仍未收斂，回傳最後內容
        return (getattr(msg, "content", "") or "已達工具呼叫步數上限。").strip()
