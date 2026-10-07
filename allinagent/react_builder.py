"""React/Vite project builder for ALLINAGENT.

Generates real Vite + React project scaffolds when explicitly requested.
Does NOT claim npm install or build success unless actually run.
"""
from __future__ import annotations

from .tools import WorkspaceTools
from .website_builder import CreationSpec


class ReactBuilder:
    """Builds Vite + React project scaffolds."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def can_handle(self, prompt: str) -> bool:
        """Check if the prompt requests React."""
        text = prompt.strip().lower()
        return any(w in text for w in ("react", "vite", "jsx", "spa", "single page app"))

    def build_react_project(self, spec: CreationSpec) -> list[str]:
        """Create a Vite + React project scaffold. Returns list of created files."""
        created: list[str] = []
        base = spec.target_path or spec.name

        # package.json
        pkg = self._generate_package_json(spec)
        result = self.tools.write_file(f"{base}/package.json", pkg)
        if "WRITE OK" in result:
            created.append(f"{base}/package.json")

        # index.html (Vite entry point)
        html = self._generate_index_html(spec)
        result = self.tools.write_file(f"{base}/index.html", html)
        if "WRITE OK" in result:
            created.append(f"{base}/index.html")

        # vite.config.js
        vite = self._generate_vite_config(spec)
        result = self.tools.write_file(f"{base}/vite.config.js", vite)
        if "WRITE OK" in result:
            created.append(f"{base}/vite.config.js")

        # src/main.jsx
        main_jsx = self._generate_main_jsx(spec)
        result = self.tools.write_file(f"{base}/src/main.jsx", main_jsx)
        if "WRITE OK" in result:
            created.append(f"{base}/src/main.jsx")

        # src/App.jsx
        app_jsx = self._generate_app_jsx(spec)
        result = self.tools.write_file(f"{base}/src/App.jsx", app_jsx)
        if "WRITE OK" in result:
            created.append(f"{base}/src/App.jsx")

        # src/styles.css
        css = self._generate_styles_css(spec)
        result = self.tools.write_file(f"{base}/src/styles.css", css)
        if "WRITE OK" in result:
            created.append(f"{base}/src/styles.css")

        # Additional pages
        for page in spec.pages:
            if page != "home":
                page_jsx = self._generate_page_component(spec, page)
                result = self.tools.write_file(f"{base}/src/pages/{page.title()}.jsx", page_jsx)
                if "WRITE OK" in result:
                    created.append(f"{base}/src/pages/{page.title()}.jsx")

        # README
        readme = self._generate_readme(spec)
        result = self.tools.write_file(f"{base}/README.md", readme)
        if "WRITE OK" in result:
            created.append(f"{base}/README.md")

        # .gitignore
        gitignore = self._generate_gitignore()
        result = self.tools.write_file(f"{base}/.gitignore", gitignore)
        if "WRITE OK" in result:
            created.append(f"{base}/.gitignore")

        return created

    def _generate_package_json(self, spec: CreationSpec) -> str:
        return f"""{{
  "name": "{spec.name}",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }}
}}
"""

    def _generate_index_html(self, spec: CreationSpec) -> str:
        name = spec.name.replace("-", " ").title()
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

    def _generate_vite_config(self, spec: CreationSpec) -> str:
        return """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
  },
})
"""

    def _generate_main_jsx(self, spec: CreationSpec) -> str:
        return """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

    def _generate_app_jsx(self, spec: CreationSpec) -> str:
        name = spec.name.replace("-", " ").title()
        pages = spec.pages or ["home"]
        nav_items = "\n".join(
            f"          <a href="#" key="{p}">{p.title()}</a>"
            for p in pages
        )
        feature_cards = "\n".join(
            f"""        <div className="card">
          <h3>{p.title()}</h3>
          <p>Explore our {p} section.</p>
        </div>"""
            for p in (pages if pages else ["Feature One"])
        )

        return f"""import React, {{ useState }} from 'react'
import './styles.css'

function App() {{
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <nav className="navbar">
        <div className="brand">{name}</div>
        <div className="nav-links">
{nav_items}
        </div>
      </nav>

      <header className="hero">
        <h1>Welcome to {name}</h1>
        <p>A React application built with Vite</p>
        <button className="btn" onClick={{() => setCount(count + 1)}}>
          Clicked {{count}} times
        </button>
      </header>

      <section className="features">
{feature_cards}
      </section>

      <footer>
        <p>&copy; {name}. All rights reserved.</p>
      </footer>
    </div>
  )
}}

export default App
"""

    def _generate_page_component(self, spec: CreationSpec, page: str) -> str:
        title = page.replace("-", " ").title()
        return f"""import React from 'react'

function {page.title()}Page() {{
  return (
    <div className="page">
      <h1>{title}</h1>
      <p>Welcome to the {title.lower()} page.</p>
    </div>
  )
}}

export default {page.title()}Page
"""

    def _generate_styles_css(self, spec: CreationSpec) -> str:
        if spec.color_scheme == "dark" or spec.theme == "dark":
            bg = "#1a1a2e"
            card_bg = "#16213e"
            text = "#e0e0e0"
            accent = "#e94560"
        else:
            bg = "#f5f5f5"
            card_bg = "#ffffff"
            text = "#333333"
            accent = "#3498db"

        return f""":root {{
  --bg-color: {bg};
  --card-bg: {card_bg};
  --text-color: {text};
  --accent: {accent};
}}

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg-color);
  color: var(--text-color);
}}

.app {{
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

.navbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: var(--card-bg);
}}

.brand {{
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--accent);
}}

.nav-links {{
  display: flex;
  gap: 2rem;
}}

.nav-links a {{
  color: var(--text-color);
  text-decoration: none;
  transition: color 0.3s;
}}

.nav-links a:hover {{
  color: var(--accent);
}}

.hero {{
  text-align: center;
  padding: 4rem 2rem;
}}

.hero h1 {{
  font-size: 3rem;
  color: var(--accent);
  margin-bottom: 1rem;
}}

.hero p {{
  font-size: 1.2rem;
  margin-bottom: 2rem;
}}

.btn {{
  padding: 0.8rem 2rem;
  font-size: 1rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}}

.btn:hover {{
  transform: translateY(-2px);
}}

.features {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}}

.card {{
  background: var(--card-bg);
  padding: 2rem;
  border-radius: 12px;
}}

.card h3 {{
  color: var(--accent);
  margin-bottom: 0.5rem;
}}

footer {{
  text-align: center;
  padding: 2rem;
  margin-top: auto;
}}
"""

    def _generate_readme(self, spec: CreationSpec) -> str:
        name = spec.name.replace("-", " ").title()
        return f"""# {name}

A React application built with Vite. Generated by ALLINAGENT v1.3.0.

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
{spec.name}/
├── index.html          Vite entry point
├── package.json        Dependencies and scripts
├── vite.config.js       Vite configuration
├── src/
│   ├── main.jsx        React entry point
│   ├── App.jsx          Main App component
│   ├── styles.css      Global styles
│   └── pages/          Page components
├── .gitignore
└── README.md
```

## Technologies

- React 18
- Vite 5
- JavaScript (JSX)
- CSS3

## Notes

- Run `npm install` before starting development.
- The dev server runs on http://localhost:3000.
- This scaffold was generated by ALLINAGENT. You need Node.js installed to build and run it.

Generated by ALLINAGENT v1.3.0.
"""

    def _generate_gitignore(self) -> str:
        return """node_modules/
dist/
.env
.env.local
.DS_Store
*.log
.vite/
"""
