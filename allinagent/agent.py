"""ALLINAGENT v1.3.0 orchestration: intelligence layer over deterministic safety core.

Architecture:
  LLM/Analyzer -> Agent -> Planner/Loop -> Tool Registry -> Tools/Builders
  -> Validators -> Fixers -> Memory/Project -> Checkpoints -> Git
"""
from __future__ import annotations
from pathlib import Path
from .autoloop import AutonomousLoop, LoopConfig
from .browser_builder import BrowserBuilder
from .checkpoint import CheckpointManager
from .config import Config
from .creator import Creator
from .dashboard import DashboardGenerator
from .document_builder import DocumentBuilder
from .fixers import Fixers
from .game_builder import GameBuilder
from .git_tools import GitTools
from .inspector import Inspector
from .local_brain import LocalBrain
from .memory import LocalMemory
from .project import ProjectMemory
from .react_builder import ReactBuilder
from .repo_coder import RepoCoder
from .tools import WorkspaceTools
from .tool_registry import ToolRegistry
from .understanding import RequestAnalyzer
from .validators import Validators
from .website_builder import WebsiteBuilder


class Agent:
    def __init__(self, workspace: Path, *, dry_run=False, allow_write=False,
                 allow_shell=False, use_llm=False, config=None, max_steps=8):
        self.workspace = workspace.resolve()
        self.tools = WorkspaceTools(self.workspace, dry_run=dry_run,
                                    allow_write=allow_write, allow_shell=allow_shell)
        self.local_brain = LocalBrain(self.tools)
        self.creator = Creator(self.tools)
        self.browser_builder = BrowserBuilder(self.tools)
        self.memory = LocalMemory(self.workspace)
        self.project = ProjectMemory(self.workspace)
        self.inspector = Inspector(self.tools)
        self.checkpoints = CheckpointManager(self.tools)
        self.request_analyzer = RequestAnalyzer()
        self.validators = Validators(self.tools)
        self.website_builder = WebsiteBuilder(self.tools)
        self.game_builder = GameBuilder(self.tools)
        self.document_builder = DocumentBuilder(self.tools)
        self.react_builder = ReactBuilder(self.tools)
        self.repo_coder = RepoCoder(self.tools)
        self.git_tools = GitTools(self.tools)
        self.dashboard_gen = DashboardGenerator(self.tools)
        self.fixers = Fixers(self.tools)
        self.tool_registry = ToolRegistry(self.tools)
        self.config = config or Config.from_env()
        self.use_llm = use_llm
        self.max_steps = max(1, max_steps)
        self.memory_enabled = True
        self.version = "1.8.0"

    def run(self, prompt: str) -> str:
        if not prompt.strip():
            return "ALLINAGENT: give me a task."

        lower = prompt.strip().lower()

        # --- Checkpoint commands ---
        if lower in ("checkpoint", "snapshot"):
            cp = self.checkpoints.create(description=prompt[:100])
            return f"Checkpoint created: {cp.id}\n  Files snapshot: {len(cp.files)}\n  Use 'rollback' to undo, 'changes' to see what changed."

        if lower == "rollback":
            return self.checkpoints.rollback()

        if lower == "changes":
            return self.checkpoints.changes()

        if lower.startswith("diff "):
            path = prompt[5:].strip()
            return self.checkpoints.diff(path)

        if lower == "checkpoints":
            return self.checkpoints.list_checkpoints()

        # --- Inspect command ---
        if lower in ("inspect", "inspect project"):
            inspection = self.inspector.inspect()
            return inspection.summary()

        # --- Git commands ---
        if lower in ("git", "git status"):
            return self.git_tools.status().summary()

        if lower in ("git summary",):
            return self.git_tools.summary()

        if lower in ("git diff",) or lower.startswith("git diff "):
            path = prompt[8:].strip() if lower.startswith("git diff ") else None
            return self.git_tools.diff(path)

        # --- Dashboard command ---
        if lower in ("dashboard", "project dashboard"):
            path = self.dashboard_gen.generate()
            if path:
                return f"Dashboard generated: {path}\nOpen in your browser to view."
            return "Dashboard generation requires --allow-write."

        # --- Validate command ---
        if lower in ("validate", "validate project"):
            inspection = self.inspector.inspect()
            files = [self.tools._display(f) for f in self.tools._iter_files()]
            result = self.validators.validate_project(files)
            return result.summary()

        # --- Fix command ---
        if lower in ("fix", "fix errors"):
            files = [self.tools._display(f) for f in self.tools._iter_files()]
            result = self.fixers.fix_generated_files(files)
            return result.summary()

        # --- Project memory commands ---
        if lower in ("project", "project view", "project status"):
            return self.project.view() if "view" in lower else self.project.status()
        if lower == "project clear":
            if self.project.clear():
                return "Project memory cleared."
            return "Could not clear project memory."
        if lower == "project files":
            data = self.project._load()
            if not data:
                return "No project initialized."
            files = data.get("important_files", [])
            if not files:
                return "No tracked files."
            return "\n".join(f"- {f['path']}" for f in files)
        if lower == "project changes":
            data = self.project._load()
            if not data:
                return "No project initialized."
            changes = data.get("changes", [])
            if not changes:
                return "No changes recorded."
            lines = ["PROJECT CHANGES"]
            for c in changes[-10:]:
                lines.append(f"- {c.get('description', '')[:100]}")
            return "\n".join(lines)

        # --- Project task/bug/decision commands ---
        if lower == "project tasks":
            return self.project.tasks()
        if lower == "project bugs":
            return self.project.bugs()
        if lower == "project decisions":
            return self.project.decisions()
        if lower.startswith("project remember"):
            note = prompt[len("project remember"):].strip()
            if note:
                self.project.remember(note)
                return "Note saved to project memory."
            return "Usage: project remember <note>"

        # --- Repository coding mode ---
        if self.repo_coder.can_handle(prompt):
            return self._handle_repo_coding(prompt)

        # --- Payment guidance (before creation) ---
        if any(w in lower for w in ("sell", "payment", "stripe", "monetize",
                                     "pricing", "subscription", "env example", "env.example")):
            return self._payment_guidance(prompt)

        # --- Desktop browser creation (v1.8.0) ---
        browser_request = any(word in lower for word in ("browser", "web browser", "internet browser"))
        creation_request = any(word in lower for word in ("make", "build", "create", "generate", "scaffold"))
        if browser_request and creation_request:
            return self.browser_builder.build(prompt)

        # --- Creation and modification requests ---
        if self.creator.can_handle(prompt) or self.request_analyzer.is_creation_request(prompt):
            return self._handle_creation(prompt)

        # --- Follow-up modifications ---
        if self.project.exists():
            spec = self.request_analyzer.analyze(prompt, self.inspector.inspect())
            if spec.is_followup():
                return self.creator._handle_followup(spec.followup_type, dict(actions=spec.actions), prompt)

        # --- Existing local brain / LLM flow ---
        if self.local_brain.can_handle(prompt) or not self.use_llm or not self.config.has_llm:
            result = self.local_brain.run(prompt)
        else:
            try:
                from .llm import run_llm
                result = run_llm(prompt, tools=self.tools, config=self.config, max_steps=self.max_steps)
            except Exception as exc:
                result = ("ALLINAGENT external model failed safely; falling back to local brain.\n"
                          f"Reason: {exc}\n\n" + self.local_brain.run(prompt))

        if hasattr(self, 'memory_enabled') and self.memory_enabled:
            self.memory.remember(prompt, result)
        return result

    def _handle_repo_coding(self, prompt: str) -> str:
        """Code an existing repository through the optional model tool loop."""
        task = self.repo_coder.parse(prompt)
        if not self.tools.allow_write:
            return self.repo_coder.plan(task) + "\n\nWrite permission required: run with --allow-write."

        if self.tools.dry_run:
            return self.repo_coder.plan(task) + "\n\nDry-run is active; no files will be changed."

        checkpoint_msg = ""
        cp = self.checkpoints.create(description=f"Before repo coding: {prompt[:80]}")
        checkpoint_msg = f"Checkpoint created: {cp.id}"

        if not self.use_llm or not self.config.has_llm:
            return (
                self.repo_coder.plan(task)
                + "\n\n"
                + checkpoint_msg
                + "\n"
                + "Repository coding requires --llm with an API-compatible model in v1.4.0."
                + "\nNo repository files were changed."
            )

        try:
            from .llm import run_llm
            result = run_llm(
                self.repo_coder.coding_prompt(task),
                tools=self.tools,
                config=self.config,
                max_steps=self.max_steps,
            )
            return (
                "ALLINAGENT REPO CODING COMPLETE\n\n"
                + checkpoint_msg
                + "\n\n"
                + result
                + "\n\nReview with: git diff"
                + "\nUndo with: rollback"
            )
        except Exception as exc:
            return (
                "ALLINAGENT REPO CODING FAILED SAFELY\n\n"
                + checkpoint_msg
                + f"\nReason: {type(exc).__name__}: {exc}"
                + "\nNo claim of success was made. Use rollback if needed."
            )

    def _handle_creation(self, prompt: str) -> str:
        """Handle creation and modification requests with full workflow."""
        # Inspect existing project first
        inspection = self.inspector.inspect()

        # Analyze the request
        spec = self.request_analyzer.analyze(prompt, inspection)

        # Create checkpoint before changes (if write enabled)
        checkpoint_msg = ""
        if self.tools.allow_write and not self.tools.dry_run:
            cp = self.checkpoints.create(description=f"Before: {prompt[:80]}")
            checkpoint_msg = f"Checkpoint created: {cp.id}\n"

        # Route to appropriate builder
        if spec.kind == "modify" or spec.is_followup():
            return self._handle_modification(spec, prompt, checkpoint_msg)
        elif spec.kind == "website":
            # Check if React was explicitly requested
            if "react" in prompt.lower() or "vite" in prompt.lower():
                return self._build_react(spec, prompt, inspection, checkpoint_msg)
            return self._build_website(spec, prompt, inspection, checkpoint_msg)
        elif spec.kind == "app":
            # Check if React was explicitly requested
            if "react" in prompt.lower() or "vite" in prompt.lower():
                return self._build_react(spec, prompt, inspection, checkpoint_msg)
            return self._build_website(spec, prompt, inspection, checkpoint_msg)
        elif spec.kind == "game":
            return self._build_game(spec, prompt, inspection, checkpoint_msg)
        elif spec.kind == "document":
            return self._build_document(spec, prompt, inspection, checkpoint_msg)
        elif spec.kind == "script":
            return self._build_script(spec, prompt, inspection, checkpoint_msg)
        else:
            return self.creator.run(prompt, allow_write=self.tools.allow_write)

    def _build_website(self, spec, prompt, inspection, checkpoint_msg) -> str:
        """Build a website with full workflow."""
        if not self.tools.allow_write:
            from .website_builder import CreationSpec
            cs = CreationSpec(kind="website", name=spec.name, theme=spec.theme,
                             color_scheme=spec.color_scheme, features=spec.features,
                             tech=spec.tech, target_path=spec.target_path)
            return self.creator._plan_only_report(cs, prompt)

        lines = ["ALLINAGENT CREATION", ""]
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: website")
        lines.append(f"Theme: {spec.theme}")
        lines.append(f"Pages: {', '.join(spec.pages) or 'home'}")
        if spec.features:
            lines.append(f"Features: {', '.join(spec.features)}")
        lines.append("")
        lines.append("Inspecting project...")
        lines.append(f"  Found {inspection.total_files} existing files")
        lines.append("")
        if checkpoint_msg:
            lines.append(checkpoint_msg)
        lines.append("Planning...")
        lines.append("Creating project structure...")

        # Build the website
        created = self.website_builder.build_website(spec)
        lines.append(f"Writing website files ({len(created)} files)...")

        # Add feature pages
        for page in spec.pages:
            if page != "home" and f"{spec.name}/{page}.html" not in created:
                page_html = self.website_builder._generate_feature_page(spec, page)
                result = self.tools.write_file(f"{spec.name}/{page}.html", page_html)
                if "WRITE OK" in result:
                    created.append(f"{spec.name}/{page}.html")
                    lines.append(f"  + {page}.html")

        # Validate
        lines.append("Running validation...")
        validation = self.validators.validate_project(created)
        if validation.ok:
            lines.append("  Validation: ALL PASSED")
        else:
            for fail in validation.failed:
                lines.append(f"  ! {fail}")

        # Save project memory
        self.project.create(name=spec.name, purpose=prompt[:500], kind="website",
                            technologies=["HTML", "CSS", "JavaScript"])
        for f in created:
            self.project.add_file(f)
        self.project.add_change(f"Created website: {spec.name}", created)
        self.project.update(state="created", architecture="Static website with HTML/CSS/JS")

        # Report
        lines.append("Finishing up...")
        lines.append("")
        lines.append("=" * 50)
        lines.append("")
        lines.append("CREATION COMPLETE")
        lines.append(f"  Project: {spec.name}")
        lines.append(f"  Type: website")
        lines.append(f"  Files created: {len(created)}")
        for f in created:
            lines.append(f"    + {f}")
        if validation.ok:
            lines.append(f"  Validation: ALL PASSED")
        lines.append("")
        lines.append("Next steps:")
        lines.append(f"  - View files: list files {spec.name}")
        lines.append(f"  - Read a file: read file {spec.name}/index.html")
        lines.append(f"  - Make changes: describe what you want")
        lines.append(f"  - Project info: project view")
        lines.append(f"  - Checkpoint: checkpoint")
        lines.append(f"  - Undo: rollback")
        return "\n".join(lines)

    def _build_game(self, spec, prompt, inspection, checkpoint_msg) -> str:
        """Build a game with full workflow."""
        if not self.tools.allow_write:
            from .website_builder import CreationSpec
            cs = CreationSpec(kind="game", name=spec.name, theme=spec.theme,
                             color_scheme=spec.color_scheme, features=spec.features,
                             tech=spec.tech, target_path=spec.target_path)
            return self.creator._plan_only_report(cs, prompt)

        lines = ["ALLINAGENT CREATION", ""]
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: game")
        lines.append(f"Theme: {spec.theme}")
        if spec.features:
            lines.append(f"Features: {', '.join(spec.features)}")
        lines.append("")
        lines.append("Inspecting project...")
        lines.append(f"  Found {inspection.total_files} existing files")
        lines.append("")
        if checkpoint_msg:
            lines.append(checkpoint_msg)
        lines.append("Planning...")
        lines.append("Creating game files...")

        created = self.game_builder.build_game(spec)
        lines.append(f"Writing game files ({len(created)} files)...")

        # Validate
        lines.append("Running validation...")
        validation = self.validators.validate_project(created)
        if validation.ok:
            lines.append("  Validation: ALL PASSED")
        else:
            for fail in validation.failed:
                lines.append(f"  ! {fail}")

        # Save project memory
        self.project.create(name=spec.name, purpose=prompt[:500], kind="game",
                            technologies=["HTML5 Canvas", "JavaScript", "CSS"])
        for f in created:
            self.project.add_file(f)
        self.project.add_change(f"Created game: {spec.name}", created)
        self.project.update(state="created", architecture="Canvas-based browser game")

        lines.append("Finishing up...")
        lines.append("")
        lines.append("=" * 50)
        lines.append("")
        lines.append("CREATION COMPLETE")
        lines.append(f"  Project: {spec.name}")
        lines.append(f"  Type: game")
        lines.append(f"  Files created: {len(created)}")
        for f in created:
            lines.append(f"    + {f}")
        if validation.ok:
            lines.append(f"  Validation: ALL PASSED")
        lines.append("")
        lines.append("Next steps:")
        lines.append(f"  - Open {spec.name}/index.html in your browser")
        lines.append(f"  - View files: list files {spec.name}")
        lines.append(f"  - Make changes: describe what you want")
        return "\n".join(lines)

    def _build_document(self, spec, prompt, inspection, checkpoint_msg) -> str:
        """Build a document with full workflow."""
        if not self.tools.allow_write:
            return ("ALLINAGENT: Write permission required to create documents.\n"
                    "Run with --allow-write to create the file.")

        lines = ["ALLINAGENT CREATION", ""]
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: document")
        lines.append("")
        if checkpoint_msg:
            lines.append(checkpoint_msg)
        lines.append("Creating document...")

        created = self.document_builder.build_document(spec, prompt)
        lines.append(f"Document created: {len(created)} file(s)")
        for f in created:
            lines.append(f"  + {f}")

        # Validate
        lines.append("Running validation...")
        validation = self.validators.validate_project(created)
        if validation.ok:
            lines.append("  Validation: ALL PASSED")

        # Save project memory
        self.project.create(name=spec.name, purpose=prompt[:500], kind="document",
                            technologies=["Markdown"])
        for f in created:
            self.project.add_file(f)
        self.project.add_change(f"Created document: {spec.name}", created)

        lines.append("")
        lines.append("CREATION COMPLETE")
        lines.append(f"  Read the document: read file {created[0] if created else 'document'}")
        return "\n".join(lines)

    def _build_script(self, spec, prompt, inspection, checkpoint_msg) -> str:
        """Build a script with full workflow."""
        if not self.tools.allow_write:
            from .website_builder import CreationSpec
            cs = CreationSpec(kind="script", name=spec.name, theme="", color_scheme="",
                             features=[], tech="vanilla", target_path=spec.target_path)
            return self.creator._plan_only_report(cs, prompt)

        lines = ["ALLINAGENT CREATION", ""]
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: script")
        lines.append("")
        if checkpoint_msg:
            lines.append(checkpoint_msg)
        lines.append("Creating script...")

        created = self.creator._build_script(spec)
        lines.append(f"Script created: {len(created)} file(s)")
        for f in created:
            lines.append(f"  + {f}")

        # Validate
        lines.append("Running validation...")
        validation = self.validators.validate_project(created)
        if validation.ok:
            lines.append("  Validation: ALL PASSED")

        # Save project memory
        self.project.create(name=spec.name, purpose=prompt[:500], kind="script",
                            technologies=["Python"])
        for f in created:
            self.project.add_file(f)
        self.project.add_change(f"Created script: {spec.name}", created)

        lines.append("")
        lines.append("CREATION COMPLETE")
        return "\n".join(lines)

    def _build_react(self, spec, prompt, inspection, checkpoint_msg) -> str:
        """Build a React/Vite project with full workflow."""
        if not self.tools.allow_write:
            from .website_builder import CreationSpec
            cs = CreationSpec(kind="website", name=spec.name, theme=spec.theme,
                             color_scheme=spec.color_scheme, features=spec.features,
                             tech="react", target_path=spec.target_path)
            return self.creator._plan_only_report(cs, prompt)

        lines = ["ALLINAGENT CREATION", ""]
        lines.append(f"Project: {spec.name}")
        lines.append(f"Type: react")
        lines.append(f"Tech: Vite + React")
        lines.append(f"Theme: {spec.theme}")
        if spec.pages:
            lines.append(f"Pages: {', '.join(spec.pages)}")
        if spec.features:
            lines.append(f"Features: {', '.join(spec.features)}")
        lines.append("")
        lines.append("Inspecting project...")
        lines.append(f"  Found {inspection.total_files} existing files")
        lines.append("")
        if checkpoint_msg:
            lines.append(checkpoint_msg)
        lines.append("Planning...")
        lines.append("Creating React project structure...")

        # Build the React project
        created = self.react_builder.build_react_project(spec)
        lines.append(f"Writing React files ({len(created)} files)...")

        # Validate
        lines.append("Running validation...")
        validation = self.validators.validate_project(created)
        if validation.ok:
            lines.append("  Validation: ALL PASSED")
        else:
            for fail in validation.failed:
                lines.append(f"  ! {fail}")
            # Attempt auto-fix
            lines.append("  Attempting auto-fix...")
            fix_result = self.fixers.fix_generated_files(created)
            if fix_result.any_fixed:
                lines.append(f"  Fixed {len(fix_result.fixed)} issue(s)")
            for fail in fix_result.failed:
                lines.append(f"  ! Cannot auto-fix: {fail}")

        # Save project memory
        self.project.create(name=spec.name, purpose=prompt[:500], kind="react",
                            technologies=["React", "Vite", "JavaScript", "CSS"])
        for f in created:
            self.project.add_file(f)
        self.project.add_change(f"Created React project: {spec.name}", created)
        self.project.update(state="created", architecture="Vite + React SPA")

        lines.append("Finishing up...")
        lines.append("")
        lines.append("=" * 50)
        lines.append("")
        lines.append("CREATION COMPLETE")
        lines.append(f"  Project: {spec.name}")
        lines.append(f"  Type: React (Vite)")
        lines.append(f"  Files created: {len(created)}")
        for f in created:
            lines.append(f"    + {f}")
        if validation.ok:
            lines.append(f"  Validation: ALL PASSED")
        lines.append("")
        lines.append("Next steps:")
        lines.append(f"  - Run: cd {spec.name} && npm install && npm run dev")
        lines.append(f"  - View files: list files {spec.name}")
        lines.append(f"  - Project info: project view")
        lines.append(f"  - Checkpoint: checkpoint")
        lines.append(f"  - Undo: rollback")
        lines.append("")
        lines.append("NOTE: You need Node.js installed to run npm commands.")
        lines.append("ALLINAGENT generated the project files but did not run npm.")
        return "\n".join(lines)

    def _handle_modification(self, spec, prompt, checkpoint_msg) -> str:
        """Handle a follow-up modification to an existing project."""
        project_data = self.project._load()
        project_name = project_data.get("name", spec.name or "my-project")
        base = project_name

        lines = ["ALLINAGENT MODIFICATION", ""]
        lines.append(f"Modifying project: {project_name}")
        lines.append(f"Change: {spec.followup_type}")
        lines.append("")

        if not self.tools.allow_write:
            lines.append("Write permission required. Run with --allow-write.")
            lines.append(f"Planned change: {spec.followup_type}")
            return "\n".join(lines)

        if checkpoint_msg:
            lines.append(checkpoint_msg)

        # Extract params from the prompt
        import re
        params = {}
        if spec.followup_type == "add_page":
            page_match = re.search(r"\badd\b.*\b(\w+)\s+page\b", prompt, re.IGNORECASE)
            page_name = page_match.group(1).lower() if page_match else "new-page"
            params["page"] = page_name
        elif spec.followup_type == "increase_size":
            if "button" in prompt.lower():
                params["target"] = "button"
            elif "text" in prompt.lower() or "font" in prompt.lower():
                params["target"] = "text"
            else:
                params["target"] = "general"
        elif spec.followup_type == "change_color":
            colors = re.findall(r"\b(red|blue|green|purple|orange|yellow|pink|cyan|teal|black|white|navy|gray|grey)\b", prompt.lower())
            if colors:
                params["color"] = colors[0]

        lines.append("Applying changes...")
        modified = self.website_builder.modify_website(base, spec.followup_type, params)

        if modified:
            lines.append(f"Files modified: {len(modified)}")
            for f in modified:
                lines.append(f"  ~ {f}")
            self.project.add_change(f"{spec.followup_type}: {prompt[:100]}", modified)
            for f in modified:
                if ".html" in f or ".css" in f or ".js" in f:
                    self.project.add_file(f, "Modified file")
        else:
            lines.append("No files needed modification.")
            lines.append("Try being more specific.")
        lines.append("")
        lines.append("Modification complete.")
        lines.append("  Use 'rollback' to undo this change.")
        return "\n".join(lines)

    def _payment_guidance(self, prompt: str) -> str:
        """Provide safe payment/business guidance without handling credentials."""
        lower = prompt.lower()
        if "env" in lower and ("example" in lower or "create" in lower or "scaffold" in lower or "generate" in lower):
            if not self.tools.allow_write:
                return ("ALLINAGENT: Write permission required to create .env.example.\n"
                        "Run with --allow-write to create the file.")
            result = self.tools.write_file(".env.example", (
                "# Copy this file to .env and fill in your values.\n"
                "# NEVER commit your .env file.\n\n"
                "# Payment provider credentials (backend only)\n"
                "# STRIPE_SECRET_KEY=sk_test_your_key_here\n"
                "# STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here\n"
                "# PAYPAL_CLIENT_ID=your_client_id\n"
                "# PAYPAL_CLIENT_SECRET=your_client_secret\n\n"
                "# Application settings\n"
                "# APP_PORT=3000\n"
                "# APP_ENV=development\n"
            ))
            if "WRITE OK" in result:
                return "Created .env.example with safe placeholder values.\nRemember: copy to .env, fill in real values, and never commit .env."
            return result

        return """ALLINAGENT PAYMENT GUIDANCE

ALLINAGENT can help you set up payment/selling infrastructure for your project.
Payment is entirely optional — normal users do not need any payment setup.

IMPORTANT SECURITY RULES:
  - Never put API keys, secret keys, or passwords in frontend code.
  - Store all credentials in environment variables or a .env file.
  - Never commit .env files to version control.
  - Use backend-only endpoints for payment processing.

RECOMMENDED APPROACH:
  1. Create a .env file with your payment credentials (never commit it).
  2. Create a .env.example file with placeholder values (safe to commit).
  3. Use a payment provider's SDK on the backend only.
  4. Add .env to your .gitignore.

To create a .env.example file, run with --allow-write:
  allinagent --allow-write "create env example"

ALLINAGENT will never expose, transmit, or store your payment credentials.
All payment setup is done locally on your machine.

If you need a specific payment integration (Stripe, PayPal, etc.),
describe what you want to sell and ALLINAGENT can guide you through it."""
