"""Project dashboard generator for ALLINAGENT.

Generates a static HTML dashboard with real project data:
project summary, file tree, important files, recent changes,
checkpoints, validation status, and next steps.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .tools import WorkspaceTools
from .inspector import Inspector
from .project import ProjectMemory
from .checkpoint import CheckpointManager


class DashboardGenerator:
    """Generates a static HTML project dashboard with real data."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools
        self.inspector = Inspector(tools)
        self.project = ProjectMemory(tools.workspace)
        self.checkpoints = CheckpointManager(tools)

    def generate(self) -> str:
        """Generate the dashboard HTML and return the file path."""
        inspection = self.inspector.inspect()
        project_data = self.project._load()
        checkpoint_data = self.checkpoints._load_all()

        # Build the dashboard HTML
        lines: list[str] = []
        lines.append("<!DOCTYPE html>")
        lines.append('<html lang="en">')
        lines.append("<head>")
        lines.append('<meta charset="UTF-8">')
        lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        lines.append("<title>ALLINAGENT Project Dashboard</title>")
        lines.append("<style>")
        lines.append(self._generate_css())
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")
        lines.append('<div class="dashboard">')

        # Header
        lines.append('<header class="header">')
        lines.append('<h1>ALLINAGENT Project Dashboard</h1>')
        lines.append(f'<p class="generated">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</p>')
        lines.append("</header>")

        # Project Summary
        lines.append('<section class="card">')
        lines.append('<h2>Project Summary</h2>')
        lines.append('<table class="info-table">')
        lines.append(f'<tr><td>Type</td><td>{html.escape(inspection.project_type)}</td></tr>')
        lines.append(f'<tr><td>Languages</td><td>{html.escape(", ".join(inspection.languages) or "none")}</td></tr>')
        if inspection.frameworks:
            lines.append(f'<tr><td>Frameworks</td><td>{html.escape(", ".join(inspection.frameworks))}</td></tr>')
        lines.append(f'<tr><td>Total Files</td><td>{inspection.total_files}</td></tr>')
        lines.append(f'<tr><td>Total Size</td><td>{inspection.total_size_mb:.2f} MB</td></tr>')
        lines.append(f'<tr><td>Has Tests</td><td>{"Yes" if inspection.has_tests else "No"}</td></tr>')
        lines.append(f'<tr><td>Has Git</td><td>{"Yes" if inspection.has_git else "No"}</td></tr>')
        lines.append(f'<tr><td>Has Docs</td><td>{"Yes" if inspection.has_docs else "No"}</td></tr>')
        if inspection.entry_points:
            lines.append(f'<tr><td>Entry Points</td><td>{html.escape(", ".join(inspection.entry_points))}</td></tr>')
        if inspection.dependencies:
            dep_str = ", ".join(f"{k} ({v})" for k, v in list(inspection.dependencies.items())[:10])
            lines.append(f'<tr><td>Dependencies</td><td>{html.escape(dep_str)}</td></tr>')
        lines.append("</table>")
        lines.append("</section>")

        # File Tree
        lines.append('<section class="card">')
        lines.append("<h2>File Tree</h2>")
        lines.append('<pre class="tree">')
        lines.append(html.escape(self.tools.tree(".", depth=3)))
        lines.append("</pre>")
        lines.append("</section>")

        # Important Files
        if inspection.important_files:
            lines.append('<section class="card">')
            lines.append("<h2>Important Files</h2>")
            lines.append("<ul>")
            for f in inspection.important_files:
                lines.append(f'<li><code>{html.escape(f)}</code></li>')
            lines.append("</ul>")
            lines.append("</section>")

        # Project Memory
        if project_data:
            lines.append('<section class="card">')
            lines.append("<h2>Project Context</h2>")
            lines.append('<table class="info-table">')
            lines.append(f'<tr><td>Name</td><td>{html.escape(project_data.get("name", ""))}</td></tr>')
            lines.append(f'<tr><td>Kind</td><td>{html.escape(project_data.get("kind", ""))}</td></tr>')
            lines.append(f'<tr><td>State</td><td>{html.escape(project_data.get("state", ""))}</td></tr>')
            techs = project_data.get("technologies", [])
            if techs:
                lines.append(f'<tr><td>Technologies</td><td>{html.escape(", ".join(techs))}</td></tr>')
            changes = project_data.get("changes", [])
            if changes:
                lines.append(f'<tr><td>Changes</td><td>{len(changes)}</td></tr>')
            lines.append("</table>")

            # Recent changes
            if changes:
                lines.append("<h3>Recent Changes</h3>")
                lines.append("<ul>")
                for c in changes[-5:]:
                    desc = c.get("description", "")[:100]
                    lines.append(f"<li>{html.escape(desc)}</li>")
                lines.append("</ul>")
            lines.append("</section>")

        # Checkpoints
        if checkpoint_data:
            lines.append('<section class="card">')
            lines.append("<h2>Checkpoints</h2>")
            lines.append("<ul>")
            for cp in checkpoint_data[-5:]:
                cp_id = cp.get("id", "?")
                cp_desc = cp.get("description", "")[:80]
                cp_time = cp.get("timestamp", "")[:19]
                lines.append(f"<li><strong>{html.escape(cp_id)}</strong> - {html.escape(cp_desc)} ({html.escape(cp_time)})</li>")
            lines.append("</ul>")
            lines.append("</section>")

        # Next Steps
        lines.append('<section class="card">')
        lines.append("<h2>Next Steps</h2>")
        lines.append("<ul>")
        if not inspection.has_tests:
            lines.append("<li>Consider adding tests for your project.</li>")
        if not inspection.has_git:
            lines.append("<li>Initialize a git repository for version control.</li>")
        if not inspection.has_docs:
            lines.append("<li>Add documentation (README, guide).</li>")
        if inspection.total_files == 0:
            lines.append("<li>Start by creating some files or ask ALLINAGENT to create a project.</li>")
        lines.append("<li>Run <code>allinagent doctor</code> for diagnostics.</li>")
        lines.append("<li>Run <code>allinagent inspect</code> for project inspection.</li>")
        lines.append("<li>Use <code>allinagent checkpoint</code> before major changes.</li>")
        lines.append("</ul>")
        lines.append("</section>")

        # Footer
        lines.append('<footer class="footer">')
        lines.append("<p>Generated by ALLINAGENT v1.3.0 — Independent. Local-first. Honest.</p>")
        lines.append("</footer>")

        lines.append("</div>")
        lines.append("</body>")
        lines.append("</html>")

        content = "\n".join(lines)

        # Write the dashboard file
        dashboard_path = ".allinagent/dashboard.html"
        if self.tools.allow_write and not self.tools.dry_run:
            result = self.tools.write_file(dashboard_path, content)
            if "WRITE OK" in result:
                return dashboard_path
        return ""

    def _generate_css(self) -> str:
        return """
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0a0a1a;
  color: #e0e0e0;
  margin: 0;
  padding: 0;
}
.dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}
.header {
  text-align: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: #16213e;
  border-radius: 12px;
}
.header h1 {
  color: #e94560;
  font-size: 2rem;
  margin: 0;
}
.generated {
  color: #757575;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
.card {
  background: #16213e;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}
.card h2 {
  color: #e94560;
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.3rem;
}
.card h3 {
  color: #3498db;
  margin-top: 1rem;
  font-size: 1.1rem;
}
.info-table {
  width: 100%;
  border-collapse: collapse;
}
.info-table td {
  padding: 0.5rem;
  border-bottom: 1px solid #1a1a3e;
}
.info-table td:first-child {
  font-weight: bold;
  color: #757575;
  width: 30%;
}
.tree {
  background: #0a0a1a;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  font-family: monospace;
  font-size: 0.9rem;
}
ul {
  list-style: none;
  padding: 0;
}
ul li {
  padding: 0.3rem 0;
}
code {
  background: #0a0a1a;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}
.footer {
  text-align: center;
  padding: 2rem;
  color: #757575;
}
"""
