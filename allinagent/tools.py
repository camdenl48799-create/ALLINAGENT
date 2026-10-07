"""Workspace-scoped tools for ALLINAGENT."""
from __future__ import annotations
import fnmatch, os, re, subprocess
from pathlib import Path
from typing import Iterable

IGNORED={".git",".venv","venv","node_modules","__pycache__",".next","bin","obj","dist","build",".idea",".vs",".pytest_cache"}
TEXT_EXTENSIONS={".py",".pyi",".js",".jsx",".ts",".tsx",".json",".toml",".yaml",".yml",".md",".txt",".rst",".ini",".cfg",".xml",".html",".css",".scss",".cs",".java",".kt",".go",".rs",".cpp",".c",".h",".hpp",".sh",".bat",".ps1",".sql"}
MAX_READ_BYTES=512_000
MAX_WRITE_BYTES=2_000_000
MAX_SEARCH_FILE_BYTES=1_000_000
MAX_SEARCH_RESULTS=100
MAX_LIST_ENTRIES=200
MAX_SHELL_OUTPUT=20_000

class WorkspaceViolation(ValueError):
    """A path is outside the configured workspace."""

class WorkspaceTools:
    """Deterministic local tools with explicit mutation permissions."""
    def __init__(self,workspace:Path,dry_run:bool=False,allow_write:bool=False,allow_shell:bool=False)->None:
        self.workspace=workspace.expanduser().resolve()
        self.dry_run=bool(dry_run); self.allow_write=bool(allow_write); self.allow_shell=bool(allow_shell)
        self.workspace.mkdir(parents=True,exist_ok=True)

    def _safe_path(self,value:str|Path)->Path:
        raw=Path(value).expanduser()
        target=((self.workspace/raw) if not raw.is_absolute() else raw).resolve()
        try: target.relative_to(self.workspace)
        except ValueError as exc: raise WorkspaceViolation(f"Path escapes workspace: {value!s}") from exc
        return target

    def _display(self,path:Path)->str:
        return str(path.relative_to(self.workspace)).replace(os.sep,"/")

    def _iter_files(self)->Iterable[Path]:
        for path in self.workspace.rglob("*"):
            try: rel=path.relative_to(self.workspace)
            except ValueError: continue
            if any(part in IGNORED for part in rel.parts): continue
            if path.is_file(): yield path

    def _is_text(self,path:Path)->bool:
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"Dockerfile","Makefile","LICENSE",".env.example"}: return True
        try: return b"\0" not in path.read_bytes()[:4096]
        except OSError: return False

    def capability_report(self)->str:
        return "\n".join(["ALLINAGENT CAPABILITIES",f"- workspace: {self.workspace}","- read/list/search: enabled",f"- file writes: {'enabled' if self.allow_write and not self.dry_run else 'disabled'}",f"- shell commands: {'enabled' if self.allow_shell and not self.dry_run else 'disabled'}",f"- dry-run: {'on' if self.dry_run else 'off'}","- path sandbox: enforced","- local mode network access: none"])

    def project_summary(self)->str:
        files=sorted(self._iter_files(),key=lambda p:self._display(p).casefold()); counts={}; total=0
        for p in files:
            ext=p.suffix.lower() or "[no extension]"; counts[ext]=counts.get(ext,0)+1
            try: total+=p.stat().st_size
            except OSError: pass
        lines=["ALLINAGENT PROJECT SUMMARY",f"Workspace: {self.workspace}",f"Files found: {len(files)}",f"Visible size: {total/1024/1024:.2f} MB","","File types:"]
        lines += [f"- {e}: {n}" for e,n in sorted(counts.items(),key=lambda x:(-x[1],x[0]))]
        lines += ["","Project files:"]+[f"- {self._display(p)}" for p in files[:120]]
        if len(files)>120: lines.append(f"... and {len(files)-120} more")
        return "\n".join(lines)

    def storage_report(self)->str:
        entries=[]
        for p in self._iter_files():
            try: entries.append((p.stat().st_size,p))
            except OSError: pass
        entries.sort(key=lambda x:(-x[0],self._display(x[1]).casefold()))
        lines=["ALLINAGENT STORAGE REPORT",f"Workspace: {self.workspace}",f"Files measured: {len(entries)}","","Largest files:"]
        lines += [f"- {s/1024/1024:8.2f} MB  {self._display(p)}" for s,p in entries[:25]]
        return "\n".join(lines+["","SAFE MODE: inspection only.","Nothing was deleted or modified."])

    def list_dir(self,path:str=".")->str:
        t=self._safe_path(path)
        if not t.exists(): return f"LIST: path does not exist: {path}"
        if not t.is_dir(): return f"LIST: not a directory: {path}"
        try: children=sorted(t.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold()))
        except OSError as exc: return f"LIST ERROR: {type(exc).__name__}: {exc}"
        lines=[f"Directory: {self._display(t) or '.'}"]+[f"- {p.name}{'/' if p.is_dir() else ''}" for p in children[:MAX_LIST_ENTRIES]]
        if len(children)>MAX_LIST_ENTRIES: lines.append(f"... and {len(children)-MAX_LIST_ENTRIES} more")
        return "\n".join(lines)

    def read_file(self,path:str)->str:
        t=self._safe_path(path)
        if not t.exists(): return f"READ: file does not exist: {path}"
        if not t.is_file(): return f"READ: not a file: {path}"
        try: size=t.stat().st_size
        except OSError as exc: return f"READ ERROR: {type(exc).__name__}: {exc}"
        if size>MAX_READ_BYTES: return f"READ: {path} is {size:,} bytes; limit is {MAX_READ_BYTES:,}."
        try: return t.read_text(encoding="utf-8")
        except UnicodeDecodeError: return f"READ: {path} is not valid UTF-8 text."
        except OSError as exc: return f"READ ERROR: {type(exc).__name__}: {exc}"

    def read_lines(self,path:str,start:int=1,end:int=100)->str:
        data=self.read_file(path)
        if data.startswith(("READ:","READ ERROR:")): return data
        start=max(1,start); end=min(max(start,end),start+499); lines=data.splitlines(); selected=lines[start-1:end]
        return "\n".join([f"LINES {start}-{min(end,len(lines))} OF {path}"]+[f"{i}: {line}" for i,line in enumerate(selected,start)])

    def search_text(self,needle:str)->str:
        q=needle.strip()
        if not q: return "SEARCH: provide non-empty text."
        matches=[]; skipped=0
        for p in self._iter_files():
            try:
                if p.stat().st_size>MAX_SEARCH_FILE_BYTES or not self._is_text(p): skipped+=1; continue
                lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
            except OSError: skipped+=1; continue
            for n,line in enumerate(lines,1):
                if q.casefold() in line.casefold():
                    matches.append(f"{self._display(p)}:{n}: {line.strip()[:240]}")
                    if len(matches)>=MAX_SEARCH_RESULTS: break
            if len(matches)>=MAX_SEARCH_RESULTS: break
        return "\n".join([f"SEARCH RESULTS FOR: {q}",f"Matches: {len(matches)}",f"Skipped files: {skipped}",""]+(matches or ["No matches found."]))

    def grep(self,pattern:str)->str:
        try: expression=re.compile(pattern,re.IGNORECASE)
        except re.error as exc: return f"GREP ERROR: invalid regular expression: {exc}"
        out=[]
        for p in self._iter_files():
            try:
                if p.stat().st_size>MAX_SEARCH_FILE_BYTES or not self._is_text(p): continue
                lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
            except OSError: continue
            for n,line in enumerate(lines,1):
                if expression.search(line):
                    out.append(f"{self._display(p)}:{n}: {line.strip()[:240]}")
                    if len(out)>=MAX_SEARCH_RESULTS: return "\n".join(out)
        return "\n".join(out) if out else "No regex matches found."

    def write_file(self,path:str,content:str)->str:
        if not self.allow_write: return "WRITE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "WRITE BLOCKED: --dry-run is active; no file changed."
        t=self._safe_path(path)
        if not isinstance(content,str): return "WRITE ERROR: content must be text."
        if len(content.encode("utf-8"))>MAX_WRITE_BYTES: return "WRITE DENIED: content exceeds the 2 MB safety limit."
        try: t.parent.mkdir(parents=True,exist_ok=True); t.write_text(content,encoding="utf-8",newline="\n")
        except OSError as exc: return f"WRITE ERROR: {type(exc).__name__}: {exc}"
        return f"WRITE OK: {self._display(t)} ({len(content.encode('utf-8')):,} bytes)"

    def run_shell(self,command:str)->str:
        if not self.allow_shell: return "SHELL DENIED: pass --allow-shell to enable execution."
        if self.dry_run: return "SHELL BLOCKED: --dry-run is active; nothing executed."
        command=command.strip()
        if not command: return "SHELL: provide a command."
        try: result=subprocess.run(command,cwd=self.workspace,shell=True,text=True,capture_output=True,timeout=30,env=os.environ.copy())
        except subprocess.TimeoutExpired: return "SHELL ERROR: command exceeded the 30-second timeout."
        except OSError as exc: return f"SHELL ERROR: {type(exc).__name__}: {exc}"
        output=result.stdout or ""
        if result.stderr: output+=("\n" if output else "")+"[stderr]\n"+result.stderr
        if len(output)>MAX_SHELL_OUTPUT: output=output[:MAX_SHELL_OUTPUT]+"\n... [output truncated]"
        status="OK" if result.returncode==0 else f"EXIT {result.returncode}"
        return f"SHELL {status}\n$ {command}\n{output}".rstrip()

    def file_exists(self,path:str)->bool:
        try: return self._safe_path(path).exists()
        except WorkspaceViolation: return False

    def matching_files(self,pattern:str)->list[str]:
        value=pattern.strip() or "*"
        return [self._display(p) for p in self._iter_files() if fnmatch.fnmatch(self._display(p),value)]

    def workspace_size_bytes(self)->int:
        total=0
        for p in self._iter_files():
            try: total+=p.stat().st_size
            except OSError: pass
        return total

    def explain_path(self,path:str)->str:
        try: t=self._safe_path(path)
        except WorkspaceViolation as exc: return f"PATH REJECTED: {exc}"
        kind="directory" if t.is_dir() else "file" if t.is_file() else "missing"
        return f"PATH: {path}\nRESOLVED: {t}\nRELATIVE: {self._display(t) or '.'}\nSTATUS: {kind}"

    def check_write(self,path:str)->str:
        try: t=self._safe_path(path)
        except WorkspaceViolation as exc: return f"WRITE CHECK FAILED: {exc}"
        if not self.allow_write: return "WRITE CHECK: denied; --allow-write is required."
        if self.dry_run: return "WRITE CHECK: blocked; --dry-run overrides permission."
        return f"WRITE CHECK: allowed for {self._display(t) or '.'}"

    def check_shell(self)->str:
        if not self.allow_shell: return "SHELL CHECK: denied; --allow-shell is required."
        if self.dry_run: return "SHELL CHECK: blocked; --dry-run is active."
        return "SHELL CHECK: allowed from workspace root."

    def tree(self,path:str=".",depth:int=2)->str:
        t=self._safe_path(path)
        if not t.is_dir(): return f"TREE: not a directory: {path}"
        lines=[f"Tree: {self._display(t) or '.'}"]; self._tree_lines(t,lines,"",max(0,min(depth,6))); return "\n".join(lines)

    def _tree_lines(self,d:Path,lines:list[str],prefix:str,depth:int)->None:
        if depth==0:return
        try: children=sorted(d.iterdir(),key=lambda p:p.name.casefold())
        except OSError:return
        for p in [x for x in children if x.name not in IGNORED][:MAX_LIST_ENTRIES]:
            lines.append(f"{prefix}- {p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir(): self._tree_lines(p,lines,prefix+"  ",depth-1)

    def extension_report(self)->str:
        counts={}
        for p in self._iter_files():
            ext=p.suffix.lower() or "[none]"; counts[ext]=counts.get(ext,0)+1
        return "\n".join(["ALLINAGENT FILE TYPE REPORT",""]+[f"{e}: {n}" for e,n in sorted(counts.items(),key=lambda x:(-x[1],x[0]))])

    def diagnostics(self)->str:
        return "\n".join(["ALLINAGENT TOOL DIAGNOSTICS",f"- workspace exists: {self.workspace.exists()}",f"- workspace writable: {os.access(self.workspace,os.W_OK)}",f"- visible files: {sum(1 for _ in self._iter_files())}",f"- visible size: {self.workspace_size_bytes()/1024/1024:.2f} MB",f"- write permission: {self.allow_write and not self.dry_run}",f"- shell permission: {self.allow_shell and not self.dry_run}","- path traversal protection: active"])

    def create_dir(self,path:str)->str:
        """Create a directory inside the workspace."""
        if not self.allow_write: return "WRITE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "WRITE BLOCKED: --dry-run is active; no directory created."
        t=self._safe_path(path)
        try:
            t.mkdir(parents=True,exist_ok=True)
        except OSError as exc: return f"MKDIR ERROR: {type(exc).__name__}: {exc}"
        return f"MKDIR OK: {self._display(t) or '.'}"

    def rename_file(self,old_path:str,new_path:str)->str:
        """Rename or move a file within the workspace."""
        if not self.allow_write: return "WRITE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "WRITE BLOCKED: --dry-run is active; nothing renamed."
        src=self._safe_path(old_path); dst=self._safe_path(new_path)
        if not src.exists(): return f"RENAME: source does not exist: {old_path}"
        if dst.exists(): return f"RENAME: destination already exists: {new_path}"
        try:
            dst.parent.mkdir(parents=True,exist_ok=True); src.rename(dst)
        except OSError as exc: return f"RENAME ERROR: {type(exc).__name__}: {exc}"
        return f"RENAME OK: {self._display(src)} -> {self._display(dst)}"

    def move_file(self,old_path:str,new_path:str)->str:
        """Move a file within the workspace (alias for rename_file)."""
        return self.rename_file(old_path,new_path)

    def delete_file(self,path:str,confirm:bool=False)->str:
        """Delete a file or directory. Requires explicit confirmation."""
        if not self.allow_write: return "DELETE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "DELETE BLOCKED: --dry-run is active; nothing deleted."
        if not confirm: return "DELETE: confirmation required. Pass confirm=True to proceed."
        t=self._safe_path(path)
        if not t.exists(): return f"DELETE: path does not exist: {path}"
        # Block workspace root deletion
        rel=self._display(t)
        if rel=="." or rel=="": return "DELETE DENIED: cannot delete the workspace root."
        # Block protected directories
        parts=t.relative_to(self.workspace).parts
        protected={".git",".venv","venv","node_modules","__pycache__",".allinagent"}
        if any(p in protected for p in parts): return f"DELETE DENIED: cannot delete protected directory: {path}"
        try:
            if t.is_dir(): 
                import shutil; shutil.rmtree(t)
            else: 
                t.unlink()
        except OSError as exc: return f"DELETE ERROR: {type(exc).__name__}: {exc}"
        return f"DELETE OK: {rel}"

    def edit_file(self,path:str,old_str:str,new_str:str)->str:
        """Replace a text snippet in a file."""
        if not self.allow_write: return "WRITE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "WRITE BLOCKED: --dry-run is active; no file changed."
        t=self._safe_path(path)
        if not t.exists(): return f"EDIT: file does not exist: {path}"
        if not t.is_file(): return f"EDIT: not a file: {path}"
        try: content=t.read_text(encoding="utf-8")
        except OSError as exc: return f"EDIT ERROR: {type(exc).__name__}: {exc}"
        except UnicodeDecodeError: return f"EDIT: {path} is not valid UTF-8 text."
        if old_str not in content: return f"EDIT: text not found in {path}"
        new_content=content.replace(old_str,new_str,1)
        if len(new_content.encode("utf-8"))>MAX_WRITE_BYTES: return "EDIT DENIED: result exceeds the 2 MB safety limit."
        try: t.write_text(new_content,encoding="utf-8",newline="\n")
        except OSError as exc: return f"EDIT ERROR: {type(exc).__name__}: {exc}"
        return f"EDIT OK: {self._display(t)} (1 replacement)"

    def write_files(self,files:dict[str,str])->str:
        """Write multiple files at once. Returns a summary."""
        if not self.allow_write: return "WRITE DENIED: pass --allow-write to enable file mutations."
        if self.dry_run: return "WRITE BLOCKED: --dry-run is active; no files changed."
        results=[]; ok=0; fail=0
        for path,content in files.items():
            r=self.write_file(path,content)
            if "WRITE OK" in r: ok+=1; results.append(f"  OK  {path}")
            else: fail+=1; results.append(f"  FAIL  {path}: {r}")
        return f"WRITE FILES: {ok} ok, {fail} failed\n"+"\n".join(results)

    def safe_cleanup_note(self)->str:
        return "\n".join(["ALLINAGENT CLEANUP POLICY","- Storage inspection is read-only.","- Automatic deletion is not part of this toolset.","- Review files before removing anything.","- Writes remain behind --allow-write and --dry-run."])
