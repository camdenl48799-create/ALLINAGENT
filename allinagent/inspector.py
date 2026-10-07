"""Project inspection for ALLINAGENT.

Analyzes a workspace to determine project type, languages, frameworks,
dependencies, entry points, tests, and important files before making changes.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .tools import WorkspaceTools


@dataclass
class ProjectInspection:
    """Structured result of inspecting a project."""
    project_type: str = "unknown"
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    important_files: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    total_files: int = 0
    total_size_mb: float = 0.0
    has_tests: bool = False
    has_git: bool = False
    has_docs: bool = False

    def summary(self) -> str:
        lines = ["ALLINAGENT PROJECT INSPECTION", ""]
        lines.append(f"  Type: {self.project_type}")
        lines.append(f"  Languages: {', '.join(self.languages) or 'none detected'}")
        if self.frameworks:
            lines.append(f"  Frameworks: {', '.join(self.frameworks)}")
        if self.entry_points:
            lines.append(f"  Entry points: {', '.join(self.entry_points)}")
        if self.config_files:
            lines.append(f"  Config files: {', '.join(self.config_files)}")
        lines.append(f"  Total files: {self.total_files}")
        lines.append(f"  Total size: {self.total_size_mb:.2f} MB")
        lines.append(f"  Has tests: {self.has_tests}")
        lines.append(f"  Has git: {self.has_git}")
        lines.append(f"  Has docs: {self.has_docs}")
        if self.important_files:
            lines.append("")
            lines.append("  Important files:")
            for f in self.important_files[:20]:
                lines.append(f"    - {f}")
        return "\n".join(lines)


# Framework detection rules
FRAMEWORK_MARKERS = {
    "react": ("package.json", "node_modules"),
    "next.js": ("next.config.js", "next.config.mjs"),
    "vue": ("vue.config.js",),
    "angular": ("angular.json",),
    "svelte": ("svelte.config.js",),
    "django": ("manage.py", "settings.py"),
    "flask": ("app.py", "wsgi.py"),
    "fastapi": ("main.py",),
    "express": ("server.js", "app.js"),
    "rails": ("Gemfile", "config.ru"),
    "laravel": ("artisan",),
    "spring": ("pom.xml", "build.gradle"),
    "dotnet": (".csproj", ".sln"),
}

CONFIG_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "Cargo.toml", "go.mod", "Gemfile", "composer.json",
    "pom.xml", "build.gradle", "CMakeLists.txt", "Makefile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "tsconfig.json", "webpack.config.js",
    "vite.config.js", "vite.config.ts",
}

DOC_FILES = {"README.md", "README.rst", "README.txt", "CHANGELOG.md",
             "CONTRIBUTING.md", "LICENSE", "docs", "documentation"}


class Inspector:
    """Inspects a workspace to understand the project structure."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def inspect(self) -> ProjectInspection:
        """Perform a full project inspection."""
        result = ProjectInspection()

        files = list(self.tools._iter_files())
        result.total_files = len(files)

        total_size = 0
        for f in files:
            try:
                total_size += f.stat().st_size
            except OSError:
                pass
        result.total_size_mb = total_size / (1024 * 1024)

        # Detect languages
        ext_counts: dict[str, int] = {}
        for f in files:
            ext = f.suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
        result.languages = self._detect_languages(ext_counts)

        # Detect frameworks
        file_names = {f.name for f in files}
        file_paths = [self.tools._display(f) for f in files]
        result.frameworks = self._detect_frameworks(file_names, file_paths)

        # Detect project type
        result.project_type = self._detect_project_type(result.languages, result.frameworks, file_names)

        # Find config files
        for f in files:
            if f.name in CONFIG_FILES:
                result.config_files.append(self.tools._display(f))
            if f.name in DOC_FILES or f.parent.name == "docs":
                result.has_docs = True
                result.important_files.append(self.tools._display(f))

        # Find entry points
        result.entry_points = self._find_entry_points(files, file_names)

        # Find test files
        result.test_files = [self.tools._display(f) for f in files
                             if "test" in f.name.lower() or f.parent.name == "tests"]
        result.has_tests = len(result.test_files) > 0

        # Check for git
        result.has_git = (self.tools.workspace / ".git").is_dir()

        # Parse dependencies
        result.dependencies = self._parse_dependencies(files)

        # Important files
        important = set()
        for f in files:
            if f.name in CONFIG_FILES or f.name in DOC_FILES:
                important.add(self.tools._display(f))
            if f.name in ("main.py", "app.py", "index.js", "server.js", "main.go"):
                important.add(self.tools._display(f))
            if f.name in ("__init__.py",) and self.tools._display(f).count("/") <= 1:
                important.add(self.tools._display(f))
        result.important_files = sorted(important)[:30]

        return result

    def _detect_languages(self, ext_counts: dict[str, int]) -> list[str]:
        lang_map = {
            ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
            ".ts": "TypeScript", ".tsx": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
            ".java": "Java", ".kt": "Kotlin", ".go": "Go",
            ".rs": "Rust", ".cpp": "C++", ".c": "C", ".h": "C/C++",
            ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
            ".sh": "Shell", ".bat": "Batch", ".sql": "SQL",
            ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
            ".toml": "TOML", ".xml": "XML", ".md": "Markdown",
        }
        languages = []
        for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
            lang = lang_map.get(ext)
            if lang and lang not in languages and count > 0:
                languages.append(lang)
        return languages[:10]

    def _detect_frameworks(self, file_names: set, file_paths: list) -> list[str]:
        frameworks = []
        for fw, markers in FRAMEWORK_MARKERS.items():
            for marker in markers:
                if marker in file_names:
                    frameworks.append(fw)
                    break
        return frameworks

    def _detect_project_type(self, languages, frameworks, file_names) -> str:
        if "next.js" in frameworks:
            return "Next.js web application"
        if "react" in frameworks:
            return "React web application"
        if "django" in frameworks:
            return "Django web application"
        if "flask" in frameworks:
            return "Flask web application"
        if "fastapi" in frameworks:
            return "FastAPI web application"
        if "express" in frameworks:
            return "Express.js web application"
        if "rails" in frameworks:
            return "Rails web application"
        if "Python" in languages and "HTML" in languages:
            return "Python web project"
        if "Python" in languages:
            if "main.py" in file_names or "cli.py" in file_names:
                return "Python CLI application"
            return "Python project"
        if "JavaScript" in languages or "TypeScript" in languages:
            if "HTML" in languages:
                return "JavaScript web project"
            return "JavaScript project"
        if "HTML" in languages:
            return "Static website"
        if "Go" in languages:
            return "Go project"
        if "Rust" in languages:
            return "Rust project"
        if "C++" in languages or "C" in languages:
            return "C/C++ project"
        if "Java" in languages:
            return "Java project"
        if not languages:
            return "empty workspace"
        return "unknown"

    def _find_entry_points(self, files, file_names) -> list[str]:
        entry_candidates = []
        for f in files:
            name = f.name
            if name in ("main.py", "app.py", "cli.py", "__main__.py",
                        "index.js", "index.ts", "server.js", "main.go",
                        "main.rs", "src/main.rs", "Program.cs", "main.java"):
                entry_candidates.append(self.tools._display(f))
            elif name == "index.html":
                entry_candidates.append(self.tools._display(f))
        return sorted(set(entry_candidates))[:10]

    def _parse_dependencies(self, files) -> dict[str, str]:
        deps = {}
        for f in files:
            if f.name == "pyproject.toml":
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith('"') or line.startswith("'"):
                            dep = line.strip("\"'").split("=")[0].split(">")[0].split("<")[0].strip()
                            if dep and dep not in ("setuptools", "wheel"):
                                deps[dep] = "python"
                except OSError:
                    pass
            elif f.name == "package.json":
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    for key in ("dependencies", "devDependencies"):
                        if key in data:
                            for dep in data[key]:
                                deps[dep] = "npm"
                except (OSError, ValueError):
                    pass
            elif f.name == "requirements.txt":
                try:
                    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            dep = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
                            if dep:
                                deps[dep] = "python"
                except OSError:
                    pass
        return dict(sorted(deps.items())[:30])
