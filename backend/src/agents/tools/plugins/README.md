# Plugin tools

Drop custom tool modules here and they auto-register on backend startup. This is the recommended destination for [CrewDefine](https://github.com/lab-zee/CrewDefine)-generated tool stubs (`crewdefine new` emits them under `<crew>/tools/`).

## Module contract

Each `*.py` file must export:

- `TOOL_DEFINITION` — a dict in OpenAI function-calling format (`{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}`).
- A callable whose name matches `TOOL_DEFINITION["function"]["name"]`. It receives the tool's parameters as keyword arguments and returns a JSON-serializable result (the result is `str()`-cast before reaching the agent).

Files beginning with `_` are skipped. Tool names that collide with a built-in are skipped with a warning — built-ins win.

Minimal example:

```python
# plugins/my_tool.py
from typing import Any

TOOL_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "..."}},
            "required": ["query"],
        },
    },
}

def my_tool(query: str) -> dict[str, Any]:
    return {"result": ...}
```

Drop the file, restart the backend, reference `my_tool` from any agent's `tools:` list.
