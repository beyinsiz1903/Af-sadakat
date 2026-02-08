"""OpenAI provider with tool calling via LiteLLM + Emergent proxy.
Handles tool call loops: model -> tool -> model -> ... -> final text.
"""
import os
import json
import logging
import litellm
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')

logger = logging.getLogger("omnihub.ai_provider")

# Emergent proxy config
INTEGRATION_PROXY_URL = os.getenv("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com")
DEFAULT_MODEL = "gpt-4o-mini"
MAX_TOOL_ROUNDS = 5  # safety: max loops of tool calling


def _is_emergent_key(key: str) -> bool:
    return key.startswith("sk-emergent-")


def get_ai_key() -> Optional[str]:
    """Get AI key from environment. Returns None if not set."""
    key = os.getenv("EMERGENT_LLM_KEY", "").strip()
    if key:
        return key
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key if key else None


async def call_chat_with_tools(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_executor: Optional[Callable] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 260,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call OpenAI with optional tool calling support.
    Handles multi-round tool calls automatically.
    
    Returns:
        {
            "content": str,          # Final text response
            "tool_calls_made": [...], # List of tool calls executed
            "total_tokens": int,
            "model": str,
            "error": str | None
        }
    """
    key = api_key or get_ai_key()
    if not key:
        return {
            "content": None,
            "tool_calls_made": [],
            "total_tokens": 0,
            "model": model,
            "error": "NO_API_KEY"
        }

    # Build litellm params
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_key": key,
    }

    if _is_emergent_key(key):
        params["api_base"] = INTEGRATION_PROXY_URL + "/llm"
        params["custom_llm_provider"] = "openai"
        # For emergent key, use model name directly
        params["model"] = model
        app_url = os.getenv("APP_URL") or os.getenv("REACT_APP_BACKEND_URL", "")
        if app_url:
            params["extra_headers"] = {"X-App-ID": app_url}

    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"

    tool_calls_made = []
    total_tokens = 0
    working_messages = list(messages)  # Copy to avoid mutation

    for round_num in range(MAX_TOOL_ROUNDS + 1):
        try:
            response = litellm.completion(**params)
        except Exception as e:
            logger.error(f"LiteLLM call failed (round {round_num}): {e}")
            return {
                "content": None,
                "tool_calls_made": tool_calls_made,
                "total_tokens": total_tokens,
                "model": model,
                "error": f"LLM_CALL_FAILED: {str(e)[:200]}"
            }

        # Track tokens
        if hasattr(response, 'usage') and response.usage:
            total_tokens += getattr(response.usage, 'total_tokens', 0)

        choice = response.choices[0]
        message = choice.message

        # Check if model wants to call tools
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Add assistant message with tool calls to context
            assistant_msg = {"role": "assistant", "content": message.content or ""}
            tool_calls_list = []
            for tc in message.tool_calls:
                tool_calls_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
            assistant_msg["tool_calls"] = tool_calls_list
            working_messages.append(assistant_msg)

            # Execute each tool call
            for tc in message.tool_calls:
                func_name = tc.function.name
                try:
                    func_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                logger.info(f"AI tool call: {func_name}({json.dumps(func_args)[:200]})")

                # Execute tool
                if tool_executor:
                    try:
                        result = await tool_executor(func_name, func_args)
                    except Exception as e:
                        logger.error(f"Tool execution error {func_name}: {e}")
                        result = {"error": str(e)}
                else:
                    result = {"error": "No tool executor configured"}

                tool_calls_made.append({
                    "name": func_name,
                    "args": func_args,
                    "result": result
                })

                # Add tool result to messages
                working_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # Update params for next round
            params["messages"] = working_messages
            continue

        # No tool calls - final text response
        content = message.content or ""
        return {
            "content": content,
            "tool_calls_made": tool_calls_made,
            "total_tokens": total_tokens,
            "model": model,
            "error": None
        }

    # Exceeded max tool rounds
    return {
        "content": "I apologize, let me connect you with our team for further assistance.",
        "tool_calls_made": tool_calls_made,
        "total_tokens": total_tokens,
        "model": model,
        "error": "MAX_TOOL_ROUNDS_EXCEEDED"
    }
