"""
LiteLLM pre-call hook: strip Claude-specific fields before forwarding to non-Claude models.

Removes:
  - content blocks of type "thinking" or "redacted_thinking" from message content arrays
  - top-level "thinking_blocks" arrays from assistant messages

These are injected by the Claude Agent SDK into session history and cause 422 errors
on non-Claude providers (Mistral, Gemini, OpenAI, etc.).
"""

from litellm.integrations.custom_logger import CustomLogger


class StripThinkingBlocks(CustomLogger):
    def _is_claude(self, model: str) -> bool:
        return "anthropic" in model or "claude" in model

    def _strip(self, messages: list) -> list:
        cleaned = []
        for msg in messages:
            msg = dict(msg)
            # Strip thinking_blocks field from assistant messages
            msg.pop("thinking_blocks", None)
            # Strip thinking content blocks from content arrays
            if isinstance(msg.get("content"), list):
                msg["content"] = [
                    block for block in msg["content"]
                    if not (isinstance(block, dict) and block.get("type") in ("thinking", "redacted_thinking"))
                ]
                # If content is now empty, replace with empty string to avoid API errors
                if not msg["content"]:
                    msg["content"] = ""
            cleaned.append(msg)
        return cleaned

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if self._is_claude(data.get("model", "")):
            return data
        if "messages" in data:
            data["messages"] = self._strip(data["messages"])
        return data


proxy_handler_instance = StripThinkingBlocks()
