"""Project workspaces and persistent project metadata for ALLINAGENT 1.1.0."""
from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = ".allinagent"
PROJECTS_FILE = "projects.json"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    tags: list[str] = field(default_factory=list)
    selling_enabled: bool = False
    provider: str | None = None
    status: str = "active"

class ProjectStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.root = self.workspace / PROJECTS_DIR
        self.path = self.root / PROJECTS_FILE
        self.root.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def list(self) -> list[Project]:
        data = self._load()
        return [Project(**item) for item in data.values()
                if isinstance(item, dict) and "id" in item and "name" in item]

    def get(self, project_id: str) -> Project | None:
        return next((p for p in self.list() if p.id == project_id), None)

    def create(self, name: str, description: str = "", tags: list[str] | None = None) -> Project:
        clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-_").lower() or "project"
        base = clean[:64]
        candidate, index = base, 2
        while self.get(candidate):
            suffix = "-" + str(index)
            candidate = base[:64-len(suffix)] + suffix
            index += 1
        project = Project(id=candidate, name=name.strip() or "Untitled Project",
                          description=description.strip(), tags=sorted(set(tags or [])))
        data = self._load()
        data[project.id] = asdict(project)
        self._save(data)
        (self.root / project.id).mkdir(parents=True, exist_ok=True)
        return project

    def update(self, project_id: str, **changes) -> Project:
        project = self.get(project_id)
        if not project:
            raise KeyError(project_id)
        allowed = {"name","description","tags","selling_enabled","provider","status"}
        data = self._load()
        raw = data[project_id]
        for key, value in changes.items():
            if key in allowed:
                raw[key] = value
        raw["updated_at"] = utc_now()
        self._save(data)
        return Project(**raw)

    def delete(self, project_id: str) -> bool:
        data = self._load()
        if project_id not in data:
            return False
        del data[project_id]
        self._save(data)
        return True

    def project_path(self, project_id: str) -> Path:
        if not self.get(project_id):
            raise KeyError(project_id)
        return self.root / project_id

    def summary(self) -> str:
        projects = self.list()
        lines = ["ALLINAGENT PROJECTS", "Count: " + str(len(projects)), ""]
        if not projects:
            lines.append("No projects created yet.")
        for p in projects:
            provider = ", provider=" + p.provider if p.provider else ""
            lines += [f"- {p.id}", f"  name: {p.name}", f"  status: {p.status}",
                      f"  selling={p.selling_enabled}{provider}", f"  updated: {p.updated_at}"]
        return "\n".join(lines)
