"""Optional OpenAI-compatible tool loop. Not required for local mode."""
from __future__ import annotations
import json
from .config import Config
from .prompts import SYSTEM_PROMPT
from .tools import WorkspaceTools

TOOLS = [
 {"type":"function","function":{"name":"project_summary","description":"Summarize workspace files","parameters":{"type":"object","properties":{}}}},
 {"type":"function","function":{"name":"storage_report","description":"Report large files without deleting","parameters":{"type":"object","properties":{}}}},
 {"type":"function","function":{"name":"list_dir","description":"List a workspace directory","parameters":{"type":"object","properties":{"path":{"type":"string"}}}}},
 {"type":"function","function":{"name":"read_file","description":"Read a UTF-8 workspace file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"write_file","description":"Write a workspace file; requires write permission","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"search_text","description":"Search workspace text","parameters":{"type":"object","properties":{"needle":{"type":"string"}},"required":["needle"]}}},
 {"type":"function","function":{"name":"run_shell","description":"Run a workspace command; requires shell permission","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
]

def call_tool(t, name, args):
    if name == "project_summary": return t.project_summary()
    if name == "storage_report": return t.storage_report()
    if name == "list_dir": return t.list_dir(args.get("path", "."))
    if name == "read_file": return t.read_file(args["path"])
    if name == "write_file": return t.write_file(args["path"], args["content"])
    if name == "search_text": return t.search_text(args["needle"])
    if name == "run_shell": return t.run_shell(args["command"])
    return "Unknown tool: " + name

def run_llm(prompt, *, tools, config: Config, max_steps=8):
    from openai import OpenAI
    client = OpenAI(api_key=config.api_key, base_url=config.base_url or None)
    messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}]
    for _ in range(max(1, max_steps)):
        response = client.chat.completions.create(model=config.model or "default", messages=messages, tools=TOOLS, tool_choice="auto")
        message = response.choices[0].message
        calls = message.tool_calls or []
        assistant = {"role":"assistant","content":message.content or ""}
        if calls:
            assistant["tool_calls"] = [{"id":c.id,"type":"function","function":{"name":c.function.name,"arguments":c.function.arguments}} for c in calls]
        messages.append(assistant)
        if not calls:
            return message.content or "The model returned no text."
        for c in calls:
            try:
                result = call_tool(tools, c.function.name, json.loads(c.function.arguments or "{}"))
            except Exception as exc:
                result = "TOOL ERROR: " + str(exc)
            messages.append({"role":"tool","tool_call_id":c.id,"content":result})
    return "ALLINAGENT stopped after the configured step limit."
