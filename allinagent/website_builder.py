"""Website builder for ALLINAGENT.

Generates real static website projects with HTML, CSS, JavaScript,
and supports follow-up modifications to existing projects.

Default technology: vanilla HTML/CSS/JS (no JS build system required).
React/Next.js is only used when the prompt explicitly requests it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .tools import WorkspaceTools


@dataclass
class CreationSpec:
    """Specification for a creation task."""
    kind: str = "website"
    name: str = "my-project"
    theme: str = ""
    color_scheme: str = ""
    features: list[str] = field(default_factory=list)
    tech: str = "vanilla"
    target_path: str = ""
    extra: dict = field(default_factory=dict)
    requirements: list[str] = field(default_factory=list)
    pages: list[str] = field(default_factory=list)


class WebsiteBuilder:
    """Builds and modifies static website projects."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def parse_prompt(self, prompt: str) -> CreationSpec:
        """Parse a natural-language creation request into a CreationSpec."""
        text = prompt.strip().lower()

        # Determine kind
        kind = "website"
        if any(w in text for w in ("game", "play", "arcade")):
            kind = "game"
        elif any(w in text for w in ("script", "automation", "tool", "cli")):
            kind = "script"
        elif any(w in text for w in ("document", "doc", "report", "guide", "manual")):
            kind = "document"
        elif any(w in text for w in ("app", "application", "dashboard")):
            kind = "app"

        # Determine theme
        theme = ""
        color_scheme = "dark"
        if "dark" in text:
            theme = "dark"
            color_scheme = "dark"
        elif "light" in text or "bright" in text:
            theme = "light"
            color_scheme = "light"
        elif "gaming" in text or "game" in text:
            theme = "gaming"
            color_scheme = "dark"

        # Determine name
        name = ""
        name_match = re.search(
            r"(?:called|named|for)\s+['\"]?([a-z0-9][a-z0-9\-_\s]*?)['\"]?(?:\.|$|\s+(?:website|site|game|app|page))",
            text,
            re.IGNORECASE,
        )
        if name_match:
            raw_name = name_match.group(1).strip().rstrip(".!")
            name = re.sub(r"[^a-z0-9\-]", "-", raw_name.lower()).strip("-")

        # Derive name from theme/kind if no explicit name
        if not name:
            # Try to extract descriptive words before the kind keyword
            kind_words = {
                "website": ["website", "site", "page"],
                "game": ["game", "games"],
                "script": ["script", "tool", "automation"],
                "document": ["document", "doc", "report", "guide"],
                "app": ["app", "application"],
            }
            keywords = kind_words.get(kind, ["project"])
            # Extract words before the kind keyword
            pattern = r"make me (?:a |an )?(.+?)\s+(?:" + "|".join(keywords) + r")"
            desc_match = re.search(pattern, text, re.IGNORECASE)
            if desc_match:
                desc = desc_match.group(1).strip()
                name = re.sub(r"[^a-z0-9\-]", "-", desc.lower()).strip("-")
                if kind == "website":
                    name = f"{name}-website"
                elif kind == "game":
                    name = f"{name}-game"
            if not name:
                if kind == "website":
                    if theme and theme != "default":
                        name = f"{theme}-website"
                    else:
                        name = "my-website"
                elif kind == "game":
                    name = "my-game"
                elif kind == "script":
                    name = "my-script"
                elif kind == "document":
                    name = "my-document"
                else:
                    name = "my-project"

        # Detect color mentions
        colors = re.findall(r"\b(red|blue|green|purple|orange|yellow|pink|cyan|teal|black|white)\b", text)
        if colors:
            color_scheme = colors[0]

        # Detect features
        features = []
        if "games page" in text or "games" in text:
            features.append("games")
        if "contact" in text:
            features.append("contact")
        if "about" in text:
            features.append("about")
        if "blog" in text:
            features.append("blog")
        if "store" in text or "shop" in text:
            features.append("store")
        if "gallery" in text:
            features.append("gallery")

        # Detect tech preference
        tech = "vanilla"
        if "react" in text or "next.js" in text or "nextjs" in text:
            tech = "react"
        if "tailwind" in text:
            tech = "tailwind"

        return CreationSpec(
            kind=kind,
            name=name or "my-project",
            theme=theme or "default",
            color_scheme=color_scheme,
            features=features,
            tech=tech,
            target_path=name or "my-project",
        )

    def is_follow_up(self, prompt: str) -> tuple[bool, str, dict]:
        """Detect if a prompt is a follow-up modification to an existing project.

        Returns (is_followup, action_type, params).
        """
        text = prompt.strip().lower()

        # Check specific patterns first (before general modification)

        # Add page/section
        if re.search(r"\badd\b.*\b(page|section|feature|button|form|table|image|gallery)\b", text):
            page_match = re.search(r"\badd\b.*\b(\w+)\s+page\b", text)
            page_name = page_match.group(1) if page_match else "new-page"
            return (True, "add_page", {"page": page_name})

        # Make responsive/mobile
        if "mobile" in text or "responsive" in text:
            return (True, "make_responsive", {})

        # Change navigation
        if ("navigation" in text or "nav" in text) and ("change" in text or "update" in text or "modify" in text):
            return (True, "modify_nav", {})

        # General modification (size, color, theme, etc.)
        if re.search(r"\b(make|change|update|modify|set|turn|enable|disable)\b.*\b(bigger|larger|smaller|darker|lighter|button|header|footer|sidebar|color|theme|background|font|text)\b", text):
            action = "modify"
            params = self._extract_modify_params(text)
            if params:
                return (True, action, params)

        return (False, "", {})

    def _extract_modify_params(self, text: str) -> dict:
        """Extract modification parameters from text."""
        params: dict = {}

        if "bigger" in text or "larger" in text:
            params["action"] = "increase_size"
            if "button" in text:
                params["target"] = "button"
            elif "text" in text or "font" in text:
                params["target"] = "text"
            else:
                params["target"] = "general"

        if "smaller" in text:
            params["action"] = "decrease_size"

        if "darker" in text:
            params["action"] = "darker"
        if "lighter" in text or "brighter" in text:
            params["action"] = "lighter"

        if "color" in text:
            colors = re.findall(r"\b(red|blue|green|purple|orange|yellow|pink|cyan|teal|black|white|navy|gray|grey)\b", text)
            if colors:
                params["action"] = "change_color"
                params["color"] = colors[0]

        return params

    def build_website(self, spec: CreationSpec) -> list[str]:
        """Create a complete website project. Returns list of created file paths."""
        created: list[str] = []
        base = spec.target_path or spec.name

        # HTML
        html_path = f"{base}/index.html"
        html = self._generate_html(spec)
        result = self.tools.write_file(html_path, html)
        if "WRITE OK" in result:
            created.append(html_path)

        # CSS
        css_path = f"{base}/styles.css"
        css = self._generate_css(spec)
        result = self.tools.write_file(css_path, css)
        if "WRITE OK" in result:
            created.append(css_path)

        # JavaScript
        js_path = f"{base}/script.js"
        js = self._generate_js(spec)
        result = self.tools.write_file(js_path, js)
        if "WRITE OK" in result:
            created.append(js_path)

        # README
        readme_path = f"{base}/README.md"
        readme = self._generate_readme(spec)
        result = self.tools.write_file(readme_path, readme)
        if "WRITE OK" in result:
            created.append(readme_path)

        # Assets placeholder
        gitkeep_path = f"{base}/assets/.gitkeep"
        result = self.tools.write_file(gitkeep_path, "")
        if "WRITE OK" in result:
            created.append(gitkeep_path)

        # Feature pages
        for feature in spec.features:
            page_path = f"{base}/{feature}.html"
            page_html = self._generate_feature_page(spec, feature)
            result = self.tools.write_file(page_path, page_html)
            if "WRITE OK" in result:
                created.append(page_path)

        return created

    def modify_website(self, base: str, action: str, params: dict) -> list[str]:
        """Modify an existing website project. Returns list of modified files."""
        modified: list[str] = []

        css_path = f"{base}/styles.css"
        html_path = f"{base}/index.html"

        if action == "increase_size":
            target = params.get("target", "general")
            css = self.tools.read_file(css_path)
            if not css.startswith("READ:"):
                if target == "button":
                    css = re.sub(r"(\.btn[^{]*\{[^}]*font-size:\s*)[\d.]+(?:px|rem|em)", r"\g<1>1.5em", css)
                    css = re.sub(r"(\.btn[^{]*\{[^}]*padding:\s*)[\d.]+(?:px|rem|em)\s+[\d.]+(?:px|rem|em)", r"\g<1>16px 32px", css)
                elif target == "text":
                    css = re.sub(r"(body\s*\{[^}]*font-size:\s*)[\d.]+(?:px|rem|em)", r"\g<1>20px", css)
                else:
                    css = re.sub(r"(body\s*\{[^}]*font-size:\s*)[\d.]+(?:px|rem|em)", r"\g<1>18px", css)
                result = self.tools.write_file(css_path, css)
                if "WRITE OK" in result:
                    modified.append(css_path)

        elif action == "change_color":
            color = params.get("color", "blue")
            color_map = {
                "red": "#e74c3c", "blue": "#3498db", "green": "#2ecc71",
                "purple": "#9b59b6", "orange": "#e67e22", "yellow": "#f1c40f",
                "pink": "#e91e63", "cyan": "#00bcd4", "teal": "#009688",
                "black": "#1a1a1a", "white": "#ffffff", "navy": "#1a237e",
                "gray": "#757575", "grey": "#757575",
            }
            color_val = color_map.get(color, "#3498db")
            css = self.tools.read_file(css_path)
            if not css.startswith("READ:"):
                css = re.sub(r"(--accent-color:\s*)#[a-f0-9]+", rf"\g<1>{color_val}", css)
                css = re.sub(r"(--primary:\s*)#[a-f0-9]+", rf"\g<1>{color_val}", css)
                result = self.tools.write_file(css_path, css)
                if "WRITE OK" in result:
                    modified.append(css_path)

        elif action == "darker":
            css = self.tools.read_file(css_path)
            if not css.startswith("READ:"):
                css = re.sub(r"(--bg-color:\s*)#[a-f0-9]+", r"\g<1>#0a0a0a", css)
                css = re.sub(r"(--card-bg:\s*)#[a-f0-9]+", r"\g<1>#161616", css)
                result = self.tools.write_file(css_path, css)
                if "WRITE OK" in result:
                    modified.append(css_path)

        elif action == "lighter":
            css = self.tools.read_file(css_path)
            if not css.startswith("READ:"):
                css = re.sub(r"(--bg-color:\s*)#[a-f0-9]+", r"\g<1>#f5f5f5", css)
                css = re.sub(r"(--card-bg:\s*)#[a-f0-9]+", r"\g<1>#ffffff", css)
                result = self.tools.write_file(css_path, css)
                if "WRITE OK" in result:
                    modified.append(css_path)

        elif action == "make_responsive":
            css = self.tools.read_file(css_path)
            if not css.startswith("READ:"):
                if "@media" not in css:
                    css += """

/* Mobile responsive */
@media (max-width: 768px) {
    .nav-links { flex-direction: column; gap: 0.5rem; }
    .hero h1 { font-size: 2rem; }
    .hero p { font-size: 1rem; }
    .features { grid-template-columns: 1fr; }
    .card { padding: 1.5rem; }
    .footer-content { flex-direction: column; }
}
"""
                    result = self.tools.write_file(css_path, css)
                    if "WRITE OK" in result:
                        modified.append(css_path)

        elif action == "add_page":
            page_name = params.get("page", "new-page")
            page_html = self._generate_feature_page(
                CreationSpec(name=base, theme="default", color_scheme="dark"),
                page_name,
            )
            result = self.tools.write_file(f"{base}/{page_name}.html", page_html)
            if "WRITE OK" in result:
                modified.append(f"{base}/{page_name}.html")

            # Update navigation in index.html
            html = self.tools.read_file(html_path)
            if not html.startswith("READ:"):
                nav_link = f'<li><a href="{page_name}.html">{page_name.title()}</a></li>'
                if page_name + ".html" not in html:
                    html = html.replace("</ul>\n      </nav>", f"      {nav_link}\n      </ul>\n      </nav>")
                    result = self.tools.write_file(html_path, html)
                    if "WRITE OK" in result:
                        modified.append(html_path)

        return modified

    def _generate_html(self, spec: CreationSpec) -> str:
        """Generate the main index.html for a website."""
        name = spec.name.replace("-", " ").title()
        theme = spec.theme or "default"

        nav_items = '<li><a href="index.html">Home</a></li>'
        for feat in spec.features:
            nav_items += f'\n        <li><a href="{feat}.html">{feat.title()}</a></li>'

        feature_cards = ""
        if spec.features:
            for feat in spec.features:
                feature_cards += f"""
        <div class="card">
          <h3>{feat.title()}</h3>
          <p>Explore our {feat} section.</p>
        </div>"""
        else:
            feature_cards = """
        <div class="card">
          <h3>Feature One</h3>
          <p>A key feature of {name}.</p>
        </div>
        <div class="card">
          <h3>Feature Two</h3>
          <p>Another great aspect of {name}.</p>
        </div>
        <div class="card">
          <h3>Feature Three</h3>
          <p>More about what makes {name} special.</p>
        </div>""".format(name=name)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <nav class="navbar">
    <div class="nav-brand">
      <a href="index.html">{name}</a>
    </div>
    <ul class="nav-links">
        {nav_items}
    </ul>
  </nav>

  <header class="hero">
    <h1>Welcome to {name}</h1>
    <p>{spec.purpose if hasattr(spec, 'purpose') else f'Your {theme} themed website'}</p>
    <button class="btn" onclick="handleClick()">Get Started</button>
  </header>

  <section class="features">
    {feature_cards}
  </section>

  <footer>
    <div class="footer-content">
      <p>&copy; {name}. All rights reserved.</p>
    </div>
  </footer>

  <script src="script.js"></script>
</body>
</html>"""

    def _generate_css(self, spec: CreationSpec) -> str:
        """Generate styles.css with theme support."""
        if spec.color_scheme == "dark" or spec.theme == "dark" or spec.theme == "gaming":
            bg = "#1a1a2e"
            card_bg = "#16213e"
            text_color = "#e0e0e0"
            accent = "#e94560"
            if spec.theme == "gaming":
                accent = "#0f3460"
                bg = "#0a0a1a"
                card_bg = "#1a1a3e"
        else:
            bg = "#f5f5f5"
            card_bg = "#ffffff"
            text_color = "#333333"
            accent = "#3498db"

        # Override with explicit color
        if spec.color_scheme and spec.color_scheme not in ("dark", "light"):
            color_map = {
                "red": "#e74c3c", "blue": "#3498db", "green": "#2ecc71",
                "purple": "#9b59b6", "orange": "#e67e22", "yellow": "#f1c40f",
                "pink": "#e91e63", "cyan": "#00bcd4", "teal": "#009688",
            }
            accent = color_map.get(spec.color_scheme, accent)

        return f""":root {{
  --bg-color: {bg};
  --card-bg: {card_bg};
  --text-color: {text_color};
  --accent-color: {accent};
  --primary: {accent};
  --max-width: 1200px;
}}

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background-color: var(--bg-color);
  color: var(--text-color);
  line-height: 1.6;
  font-size: 16px;
}}

.navbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: var(--card-bg);
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}}

.nav-brand a {{
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--accent-color);
  text-decoration: none;
}}

.nav-links {{
  display: flex;
  list-style: none;
  gap: 2rem;
}}

.nav-links a {{
  color: var(--text-color);
  text-decoration: none;
  transition: color 0.3s;
}}

.nav-links a:hover {{
  color: var(--accent-color);
}}

.hero {{
  text-align: center;
  padding: 4rem 2rem;
  max-width: var(--max-width);
  margin: 0 auto;
}}

.hero h1 {{
  font-size: 3rem;
  margin-bottom: 1rem;
  color: var(--accent-color);
}}

.hero p {{
  font-size: 1.2rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}}

.btn {{
  display: inline-block;
  padding: 0.8rem 2rem;
  font-size: 1rem;
  background: var(--accent-color);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}}

.btn:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}}

.features {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 2rem;
}}

.card {{
  background: var(--card-bg);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}}

.card:hover {{
  transform: translateY(-4px);
}}

.card h3 {{
  color: var(--accent-color);
  margin-bottom: 0.5rem;
}}

footer {{
  background: var(--card-bg);
  padding: 2rem;
  text-align: center;
  margin-top: 4rem;
}}

.footer-content {{
  max-width: var(--max-width);
  margin: 0 auto;
}}
"""

    def _generate_js(self, spec: CreationSpec) -> str:
        """Generate script.js with interactive functionality."""
        return f"""// {spec.name} - Interactive Script

document.addEventListener('DOMContentLoaded', function() {{
  console.log('{spec.name} loaded');

  // Smooth scroll for navigation links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
    anchor.addEventListener('click', function(e) {{
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {{
        e.preventDefault();
        target.scrollIntoView({{ behavior: 'smooth' }});
      }}
    }});
  }});

  // Card hover effect
  document.querySelectorAll('.card').forEach(card => {{
    card.addEventListener('mouseenter', function() {{
      this.style.transform = 'translateY(-4px)';
    }});
    card.addEventListener('mouseleave', function() {{
      this.style.transform = 'translateY(0)';
    }});
  }});
}});

function handleClick() {{
  const btn = document.querySelector('.btn');
  if (btn) {{
    btn.textContent = 'Welcome!';
    btn.style.transform = 'scale(1.1)';
    setTimeout(() => {{
      btn.textContent = 'Get Started';
      btn.style.transform = 'scale(1)';
    }}, 2000);
  }}
}}
"""

    def _generate_readme(self, spec: CreationSpec) -> str:
        """Generate README.md for the website project."""
        return f"""# {spec.name.replace('-', ' ').title()}

A {spec.theme} themed website generated by ALLINAGENT.

## Project Structure

```
{spec.name}/
├── index.html      Main page
├── styles.css      All styling
├── script.js        Interactive features
├── assets/          Images and media
└── README.md        This file
{chr(10).join(f"├── {f}.html       {f.title()} page" for f in spec.features)}
```

## Technologies

- HTML5
- CSS3 (CSS Variables, Flexbox, Grid)
- Vanilla JavaScript

## Usage

1. Open `index.html` in your browser.
2. Or serve locally:
   ```bash
   python -m http.server 8000
   ```
3. Visit `http://localhost:8000`

## Customization

Edit `styles.css` to change colors, fonts, and layout.
Edit `script.js` to add interactivity.

Generated by ALLINAGENT v1.1.0.
"""

    def _generate_feature_page(self, spec: CreationSpec, feature: str) -> str:
        """Generate a feature page (e.g., games.html, about.html)."""
        title = feature.replace("-", " ").title()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - {spec.name.replace('-', ' ').title()}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <nav class="navbar">
    <div class="nav-brand">
      <a href="index.html">{spec.name.replace('-', ' ').title()}</a>
    </div>
    <ul class="nav-links">
      <li><a href="index.html">Home</a></li>
      <li><a href="{feature}.html">{title}</a></li>
    </ul>
  </nav>

  <header class="hero">
    <h1>{title}</h1>
    <p>Welcome to the {title.lower()} page.</p>
  </header>

  <section class="features">
    <div class="card">
      <h3>{title} Content</h3>
      <p>This section contains {title.lower()} content. Customize it as needed.</p>
    </div>
  </section>

  <footer>
    <div class="footer-content">
      <p>&copy; {spec.name.replace('-', ' ').title()}. All rights reserved.</p>
    </div>
  </footer>

  <script src="script.js"></script>
</body>
</html>"""
