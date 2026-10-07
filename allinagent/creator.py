"""Universal creation system for ALLINAGENT.

Dispatches natural-language creation requests to the appropriate builder
(website, game, script, document, generic project). Integrates with the
planner, validators, project memory, and guardrails.
"""
from __future__ import annotations

import re
from pathlib import Path

from .guardrails import Guardrails, RiskLevel
from .planner import TaskPlanner, PlanStep
from .project import ProjectMemory
from .tools import WorkspaceTools
from .validators import Validators
from .website_builder import WebsiteBuilder, CreationSpec


class Creator:
    """Universal creation dispatcher for ALLINAGENT."""

    CREATE_PATTERNS = (
        r"\b(?:make|build|create|generate|scaffold|setup)\b",
        r"\bmake me\b",
        r"\bi want\b.*\b(?:website|game|app|script|tool)\b",
        r"\blet'?s make\b",
        r"\bcan you (make|build|create)\b",
    )

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self.website_builder = WebsiteBuilder(tools)
        self.planner = TaskPlanner(tools)
        self.validators = Validators(tools)
        self.guardrails = Guardrails(tools)
        self.project = ProjectMemory(tools.workspace)

    def can_handle(self, prompt: str) -> bool:
        """Check if a prompt is a creation request."""
        text = prompt.strip().lower()
        if not text:
            return False
        return any(re.search(p, text) for p in self.CREATE_PATTERNS)

    def run(self, prompt: str, allow_write: bool = False) -> str:
        """Process a creation request end-to-end.

        Returns a user-facing report with progress summaries.
        Does NOT expose hidden chain-of-thought.
        """
        # Detect follow-up vs new creation
        is_followup, action, params = self.website_builder.is_follow_up(prompt)

        if is_followup and self.project.exists():
            return self._handle_followup(action, params, prompt)

        # Parse the creation request
        spec = self.website_builder.parse_prompt(prompt)
        spec.purpose = prompt[:200]  # type: ignore

        # Check write permission
        if not allow_write:
            return self._plan_only_report(spec, prompt)

        # Build the plan
        steps = self.planner.plan_creation(
            spec.kind, spec.name, spec.theme, spec.features
        )

        # Show progress
        progress_lines = ["ALLINAGENT CREATION", ""]
        progress_lines.append(f"Project: {spec.name}")
        progress_lines.append(f"Type: {spec.kind}")
        progress_lines.append(f"Theme: {spec.theme}")
        progress_lines.append(f"Tech: {spec.tech}")
        if spec.features:
            progress_lines.append(f"Features: {', '.join(spec.features)}")
        progress_lines.append("")
        progress_lines.append("Plan:")
        for i, step in enumerate(steps, 1):
            progress_lines.append(f"  {i}. {step.label}")
        progress_lines.append("")

        # Execute
        created_files: list[str] = []
        errors: list[str] = []

        if spec.kind == "website":
            progress_lines.append("Creating project structure...")
            created = self.website_builder.build_website(spec)
            created_files.extend(created)
        elif spec.kind == "game":
            created = self._build_game(spec)
            created_files.extend(created)
        elif spec.kind == "script":
            created = self._build_script(spec)
            created_files.extend(created)
        elif spec.kind == "document":
            created = self._build_document(spec)
            created_files.extend(created)
        else:
            created = self._build_generic(spec)
            created_files.extend(created)

        # Validate
        progress_lines.append("Checking for errors...")
        validation = self.validators.validate_project(created_files)
        if validation.failed:
            for fail in validation.failed:
                errors.append(fail)

        # Save project context
        self.project.create(
            name=spec.name,
            purpose=prompt[:500],
            kind=spec.kind,
            technologies=["HTML", "CSS", "JavaScript"] if spec.kind in ("website", "game") else ["Python"],
        )
        for f in created_files:
            self.project.add_file(f)
        self.project.add_change(f"Created {spec.kind} project: {spec.name}", created_files)
        self.project.update(state="created")

        # Report
        progress_lines.append("Finishing up...")
        progress_lines.append("")
        progress_lines.append("=" * 50)
        progress_lines.append("")
        progress_lines.append("CREATION COMPLETE")
        progress_lines.append("")
        progress_lines.append(f"Project: {spec.name}")
        progress_lines.append(f"Type: {spec.kind}")
        progress_lines.append(f"Files created: {len(created_files)}")
        for f in created_files:
            progress_lines.append(f"  + {f}")
        if errors:
            progress_lines.append("")
            progress_lines.append(f"Validation errors: {len(errors)}")
            for e in errors:
                progress_lines.append(f"  ! {e}")
        else:
            progress_lines.append("")
            progress_lines.append("Validation: ALL PASSED")
        progress_lines.append("")
        progress_lines.append("Next steps:")
        progress_lines.append(f"  - View the project: list files {spec.name}")
        progress_lines.append(f"  - Read a file: read file {spec.name}/index.html")
        progress_lines.append("  - Make changes: just describe what you want")
        progress_lines.append(f"  - Project context: type 'project view'")

        return "\n".join(progress_lines)

    def _handle_followup(self, action: str, params: dict, prompt: str) -> str:
        """Handle a follow-up modification to an existing project."""
        project_data = self.project._load()
        project_name = project_data.get("name", "my-project")
        base = project_name

        lines = ["ALLINAGENT MODIFICATION", ""]
        lines.append(f"Modifying project: {project_name}")
        lines.append("")

        if not self.tools.allow_write:
            lines.append("Write permission is required to modify files.")
            lines.append("Restart with --allow-write to make changes.")
            lines.append("")
            lines.append("Planned change:")
            lines.append(f"  {action}: {params}")
            return "\n".join(lines)

        modified = self.website_builder.modify_website(base, params.get("action", action), params)

        lines.append("Applying changes...")
        lines.append("")
        if modified:
            lines.append(f"Files modified: {len(modified)}")
            for f in modified:
                lines.append(f"  ~ {f}")
            self.project.add_change(f"{action}: {params}", modified)
        else:
            lines.append("No files needed modification.")
            lines.append("Try being more specific, e.g., 'make the buttons bigger'")
        lines.append("")
        lines.append("Modification complete.")

        return "\n".join(lines)

    def _plan_only_report(self, spec: CreationSpec, prompt: str) -> str:
        """Return a plan without writing files (when --allow-write is not set)."""
        steps = self.planner.plan_creation(
            spec.kind, spec.name, spec.theme, spec.features
        )
        lines = ["ALLINAGENT CREATION (PLAN ONLY)", ""]
        lines.append("Write permission is not enabled.")
        lines.append("This is a preview of what ALLINAGENT would create.")
        lines.append("")
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: {spec.kind}")
        lines.append(f"Theme: {spec.theme}")
        lines.append(f"Tech: {spec.tech}")
        if spec.features:
            lines.append(f"Features: {', '.join(spec.features)}")
        lines.append("")
        lines.append("Plan:")
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step.summary}")
        lines.append("")
        lines.append("Files that would be created:")
        if spec.kind == "website":
            lines.append(f"  {spec.name}/index.html")
            lines.append(f"  {spec.name}/styles.css")
            lines.append(f"  {spec.name}/script.js")
            lines.append(f"  {spec.name}/README.md")
            lines.append(f"  {spec.name}/assets/.gitkeep")
            for f in spec.features:
                lines.append(f"  {spec.name}/{f}.html")
        elif spec.kind == "game":
            lines.append(f"  {spec.name}/index.html")
            lines.append(f"  {spec.name}/styles.css")
            lines.append(f"  {spec.name}/game.js")
            lines.append(f"  {spec.name}/README.md")
        elif spec.kind == "script":
            lines.append(f"  {spec.name}/main.py")
            lines.append(f"  {spec.name}/README.md")
        else:
            lines.append(f"  {spec.name}/README.md")
        lines.append("")
        lines.append("To actually create this project, run:")
        lines.append(f"  allinagent --allow-write \"{prompt}\"")
        return "\n".join(lines)

    def _build_game(self, spec: CreationSpec) -> list[str]:
        """Build a simple browser game project."""
        created: list[str] = []
        base = spec.target_path or spec.name

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{spec.name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="game-container">
    <h1>{spec.name.replace('-', ' ').title()}</h1>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <p class="score">Score: <span id="score">0</span></p>
    <p class="instructions">Use arrow keys to play</p>
  </div>
  <script src="game.js"></script>
</body>
</html>"""

        css = """:root {
  --bg: #1a1a2e;
  --accent: #e94560;
  --text: #e0e0e0;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, sans-serif;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}
.game-container {
  text-align: center;
}
h1 { color: var(--accent); }
canvas {
  border: 2px solid var(--accent);
  border-radius: 8px;
  background: #0a0a1a;
}
.score { font-size: 1.5rem; }
.instructions { opacity: 0.7; }
"""

        js = """// Simple game: catch the falling blocks
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');

let score = 0;
let player = { x: 375, y: 550, w: 50, h: 20, speed: 8 };
let blocks = [];
let keys = {};

document.addEventListener('keydown', e => keys[e.key] = true);
document.addEventListener('keyup', e => keys[e.key] = false);

function spawnBlock() {
  blocks.push({
    x: Math.random() * 750,
    y: 0,
    w: 30,
    h: 30,
    speed: 2 + Math.random() * 3
  });
}

function update() {
  if (keys['ArrowLeft']) player.x -= player.speed;
  if (keys['ArrowRight']) player.x += player.speed;
  player.x = Math.max(0, Math.min(750, player.x));

  blocks.forEach(b => b.y += b.speed);
  blocks = blocks.filter(b => b.y < 600);

  // Collision detection
  blocks.forEach((b, i) => {
    if (b.x < player.x + player.w &&
        b.x + b.w > player.x &&
        b.y < player.y + player.h &&
        b.y + b.h > player.y) {
      score++;
      scoreEl.textContent = score;
      blocks.splice(i, 1);
    }
  });

  if (Math.random() < 0.02) spawnBlock();
}

function draw() {
  ctx.clearRect(0, 0, 800, 600);
  ctx.fillStyle = '#e94560';
  ctx.fillRect(player.x, player.y, player.w, player.h);
  ctx.fillStyle = '#3498db';
  blocks.forEach(b => ctx.fillRect(b.x, b.y, b.w, b.h));
}

function loop() {
  update();
  draw();
  requestAnimationFrame(loop);
}

loop();
"""

        for path, content in [
            (f"{base}/index.html", html),
            (f"{base}/styles.css", css),
            (f"{base}/game.js", js),
            (f"{base}/README.md", f"# {spec.name}\n\nA browser game built with HTML5 Canvas.\n\n## How to Play\n\nUse arrow keys to catch falling blocks.\n\nGenerated by ALLINAGENT.\n"),
        ]:
            result = self.tools.write_file(path, content)
            if "WRITE OK" in result:
                created.append(path)

        return created

    def _build_script(self, spec: CreationSpec) -> list[str]:
        """Build a simple Python script project."""
        created: list[str] = []
        base = spec.target_path or spec.name

        script = f'''#!/usr/bin/env python3
"""{spec.name} - Generated by ALLINAGENT."""

import sys


def main():
    print("Hello from {spec.name}!")
    print("This script was generated by ALLINAGENT.")
    # TODO: Add your logic here
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

        readme = f"""# {spec.name}

A Python script generated by ALLINAGENT.

## Usage

```bash
python main.py
```

Generated by ALLINAGENT v1.1.0.
"""

        for path, content in [
            (f"{base}/main.py", script),
            (f"{base}/README.md", readme),
        ]:
            result = self.tools.write_file(path, content)
            if "WRITE OK" in result:
                created.append(path)

        return created

    def _build_document(self, spec: CreationSpec) -> list[str]:
        """Build a document project."""
        created: list[str] = []
        base = spec.target_path or spec.name

        doc = f"""# {spec.name.replace('-', ' ').title()}

Generated by ALLINAGENT.

## Overview

This document was created based on your request.

## Content

Add your content here.

## Notes

- Generated by ALLINAGENT v1.1.0
"""

        result = self.tools.write_file(f"{base}/README.md", doc)
        if "WRITE OK" in result:
            created.append(f"{base}/README.md")

        return created

    def _build_generic(self, spec: CreationSpec) -> list[str]:
        """Build a generic project scaffold."""
        created: list[str] = []
        base = spec.target_path or spec.name

        readme = f"""# {spec.name.replace('-', ' ').title()}

A project generated by ALLINAGENT.

## Overview

This project was created based on your request.

## Structure

- `README.md` - This file

## Usage

Add your project files here.

Generated by ALLINAGENT v1.1.0.
"""
        result = self.tools.write_file(f"{base}/README.md", readme)
        if "WRITE OK" in result:
            created.append(f"{base}/README.md")

        return created
