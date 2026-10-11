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
 {"type":"function","function":{"name":"edit_file","description":"Replace text in a file; requires write permission","parameters":{"type":"object","properties":{"path":{"type":"string"},"old_str":{"type":"string"},"new_str":{"type":"string"}},"required":["path","old_str","new_str"]}}},
 {"type":"function","function":{"name":"write_files","description":"Write multiple files at once","parameters":{"type":"object","properties":{"files":{"type":"object","additionalProperties":{"type":"string"}}},"required":["files"]}}},
 {"type":"function","function":{"name":"create_dir","description":"Create a directory","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"rename_file","description":"Rename or move a file","parameters":{"type":"object","properties":{"old_path":{"type":"string"},"new_path":{"type":"string"}},"required":["old_path","new_path"]}}},
 {"type":"function","function":{"name":"delete_file","description":"Delete a file or directory","parameters":{"type":"object","properties":{"path":{"type":"string"},"confirm":{"type":"boolean","default":false}},"required":["path"]}}},
 {"type":"function","function":{"name":"search_text","description":"Search workspace text","parameters":{"type":"object","properties":{"needle":{"type":"string"}},"required":["needle"]}}},
 {"type":"function","function":{"name":"run_shell","description":"Run a workspace command; requires shell permission","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},

 {"type":"function","function":{"name":"you_search","description":"Search the live web using You.com and return source URLs and summaries. Use for current facts and research; cite returned URLs in your answer.","parameters":{"type":"object","properties":{"query":{"type":"string","description":"Question or topic to search for"},"count":{"type":"integer","description":"Maximum number of results (1-10)","minimum":1,"maximum":10}},"required":["query"]}}},
]

def call_tool(t, name, args):
    if name == "you_search":
        from .you_search import search_web
        return search_web(args.get("query", ""), count=args.get("count", 5))
    if name == "project_summary": return t.project_summary()
    if name == "storage_report": return t.storage_report()
    if name == "list_dir": return t.list_dir(args.get("path", "."))
    if name == "read_file": return t.read_file(args["path"])
    if name == "write_file": return t.write_file(args["path"], args["content"])
    if name == "edit_file": return t.edit_file(args["path"], args["old_str"], args["new_str"])
    if name == "write_files": return t.write_files(args["files"])
    if name == "create_dir": return t.create_dir(args["path"])
    if name == "rename_file": return t.rename_file(args["old_path"], args["new_path"])
    if name == "delete_file": return t.delete_file(args["path"], args.get("confirm", False))
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
