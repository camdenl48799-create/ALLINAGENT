"""Safe web-project generation for ALLINAGENT."""
from __future__ import annotations
from .tools import WorkspaceTools

class WebBuilder:
    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def detect(self) -> str:
        checks = [("next.config.js","nextjs"),("next.config.mjs","nextjs"),
                  ("vite.config.ts","vite"),("vite.config.js","vite"),
                  ("package.json","node"),("pyproject.toml","python"),
                  ("requirements.txt","python")]
        for name, kind in checks:
            if self.tools.file_exists(name):
                return kind
        return "unknown"

    def scaffold(self, title: str = "ALLINAGENT Website") -> str:
        if not self.tools.allow_write or self.tools.dry_run:
            return "WEB BUILDER: write permission is required."
        kind = self.detect()
        if kind == "nextjs":
            files = self._next(title)
        elif kind in {"node","vite"}:
            files = self._vite(title)
        else:
            files = self._static(title)
        output = ["ALLINAGENT WEB BUILDER", "Detected: " + kind]
        for path, content in files.items():
            output.append(self.tools.write_file(path, content))
        return "\n".join(output)

    def _static(self, title: str) -> dict[str,str]:
        return {
            "index.html": "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"
            + title + "</title><link rel='stylesheet' href='styles.css'></head><body><main class='shell'><p>ALLINAGENT</p><h1>"
            + title + "</h1><p>Built with a local-first agent workflow.</p><button id='action'>Get started</button><p id='status' aria-live='polite'></p></main><script src='app.js'></script></body></html>",
            "styles.css": "*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:#0d1117;color:#f5f7fa}.shell{min-height:100vh;display:grid;place-content:center;gap:16px;max-width:760px;margin:auto;padding:32px}.shell h1{font-size:clamp(2.5rem,8vw,6rem);margin:0}button{border:0;border-radius:12px;padding:12px 18px;font-weight:700;cursor:pointer}",
            "app.js": "document.querySelector('#action').addEventListener('click',()=>{document.querySelector('#status').textContent='Your site is ready for the next step.'});"
        }

    def _vite(self, title: str) -> dict[str,str]:
        return {
            "src/main.js": "import './style.css';\nconst app=document.querySelector('#app'); app.innerHTML='<main><p>ALLINAGENT</p><h1>"
            + title + "</h1><button id="start">Get started</button><p id="status"></p></main>'; document.querySelector('#start').onclick=()=>document.querySelector('#status').textContent='Ready.';",
            "src/style.css": "body{margin:0;background:#0d1117;color:#fff;font-family:system-ui,sans-serif}main{min-height:100vh;display:grid;place-content:center;padding:32px;gap:12px}h1{font-size:clamp(2.5rem,8vw,6rem);margin:0}button{padding:12px 18px;border-radius:10px;border:0;font-weight:700}"
        }

    def _next(self, title: str) -> dict[str,str]:
        return {
            "app/page.tsx": "export default function Home(){return <main style={{minHeight:'100vh',display:'grid',placeItems:'center',fontFamily:'system-ui'}}><section><p>ALLINAGENT</p><h1>"
            + title + "</h1><p>Your agent-built website starts here.</p></section></main>}"
        }
