from pathlib import Path

IGNORED={".git",".venv","node_modules","__pycache__",".next","bin","obj"}

class WorkspaceTools:
    def __init__(self, workspace: Path, dry_run=False):
        self.workspace=workspace
        self.dry_run=dry_run

    def project_summary(self):
        files=[]
        for p in self.workspace.rglob("*"):
            if any(part in IGNORED for part in p.parts):
                continue
            if p.is_file():
                files.append(p.relative_to(self.workspace))
        files.sort(key=lambda x: str(x).lower())
        preview=files[:80]
        lines=[f"Workspace: {self.workspace}",f"Files found: {len(files)}","","Project files:"]
        lines += [f"- {p}" for p in preview]
        if len(files)>80: lines.append(f"... and {len(files)-80} more")
        return "\n".join(lines)

    def storage_report(self):
        entries=[]
        for p in self.workspace.rglob("*"):
            if p.is_file():
                try: entries.append((p.stat().st_size,p.relative_to(self.workspace)))
                except OSError: pass
        entries.sort(reverse=True)
        lines=["ALLINAGENT storage report",f"Workspace: {self.workspace}","","Largest files:"]
        for size,path in entries[:25]:
            lines.append(f"- {size/1024/1024:.1f} MB  {path}")
        lines += ["","SAFE MODE: nothing was deleted.","Use an explicit approved cleanup action before removing anything."]
        return "\n".join(lines)
