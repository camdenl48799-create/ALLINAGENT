"""Generate a small desktop web browser powered by Qt WebEngine.

The generated app uses Chromium through PySide6.QtWebEngineWidgets; it is not a
new browser engine. Files are written only through WorkspaceTools permissions.
"""
from __future__ import annotations

import re

from .tools import WorkspaceTools


class BrowserBuilder:
    """Scaffold a desktop browser project."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    @staticmethod
    def project_name(prompt: str) -> str:
        match = re.search(r"\b(?:called|named)\s+([\w -]{2,50})", prompt, re.I)
        raw = match.group(1) if match else "my-browser"
        raw = re.sub(r"\b(with|that|which|and)\b.*$", "", raw, flags=re.I).strip()
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw.lower()).strip("-_")
        return (slug or "my-browser")[:40]

    def build(self, prompt: str) -> str:
        """Create browser source files or explain why no files were written."""
        if not self.tools.allow_write or self.tools.dry_run:
            return (
                "ALLINAGENT BROWSER BUILDER (PLAN ONLY)\n\n"
                "I can scaffold a desktop browser using Python + PySide6 Qt WebEngine "
                "(Chromium). It will include tabs, an address/search bar, Back, Forward, "
                "Reload, Home, and bookmarks.\n\n"
                "No files were written. Restart with --allow-write to create the project."
            )

        name = self.project_name(prompt)
        base = name
        main_py = r'''"""A minimal tabbed desktop browser built with Qt WebEngine."""
from __future__ import annotations

import sys
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QToolBar,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

HOME_URL = "https://www.google.com"


class BrowserTab(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUrl(QUrl(HOME_URL))


class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALLINAGENT Browser")
        self.resize(1200, 800)
        self.tabs = QTabWidget(movable=True, tabsClosable=True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_address)
        self.setCentralWidget(self.tabs)

        bar = QToolBar("Navigation")
        bar.setMovable(False)
        self.addToolBar(bar)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Enter a website or search the web")
        self.address.returnPressed.connect(self.navigate)
        for label, callback in (
            ("Back", self.go_back), ("Forward", self.go_forward),
            ("Reload", self.reload_page), ("Home", self.go_home),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        bar.addWidget(self.address)

        new_tab = QAction("New Tab", self)
        new_tab.setShortcut(QKeySequence("Ctrl+T"))
        new_tab.triggered.connect(lambda: self.add_tab())
        self.addAction(new_tab)
        close_tab = QAction("Close Tab", self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab)
        focus_address = QAction("Focus Address Bar", self)
        focus_address.setShortcut(QKeySequence("Ctrl+L"))
        focus_address.triggered.connect(self.address.setFocus)
        self.addAction(focus_address)
        bookmark = QAction("Bookmark Current Page", self)
        bookmark.setShortcut(QKeySequence("Ctrl+D"))
        bookmark.triggered.connect(self.bookmark_page)
        self.addAction(bookmark)
        self.bookmarks = []
        self.add_tab()

    def current_view(self):
        return self.tabs.currentWidget()

    def add_tab(self, url=None):
        view = BrowserTab()
        if url:
            view.setUrl(QUrl(url))
        index = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(index)
        view.titleChanged.connect(lambda title, v=view: self.update_title(v, title))
        view.urlChanged.connect(lambda qurl, v=view: self.update_address(v, qurl))
        return view

    def update_title(self, view, title):
        index = self.tabs.indexOf(view)
        if index >= 0:
            self.tabs.setTabText(index, (title or "New Tab")[:32])

    def update_address(self, view, url):
        if view is self.current_view():
            self.address.setText(url.toString())

    def sync_address(self, _index):
        view = self.current_view()
        if view:
            self.address.setText(view.url().toString())

    def navigate(self):
        text = self.address.text().strip()
        if not text:
            return
        if "://" not in text and "." in text.split("/")[0] and " " not in text:
            text = "https://" + text
        elif "://" not in text:
            text = "https://www.google.com/search?q=" + quote(text)
        self.current_view().setUrl(QUrl.fromUserInput(text))

    def go_back(self):
        self.current_view().back()

    def go_forward(self):
        self.current_view().forward()

    def reload_page(self):
        self.current_view().reload()

    def go_home(self):
        self.current_view().setUrl(QUrl(HOME_URL))

    def close_tab(self, index):
        if index < 0:
            return
        view = self.tabs.widget(index)
        self.tabs.removeTab(index)
        view.deleteLater()
        if self.tabs.count() == 0:
            self.add_tab()

    def bookmark_page(self):
        view = self.current_view()
        url = view.url().toString()
        if url and url not in self.bookmarks:
            self.bookmarks.append(url)
        QMessageBox.information(
            self, "Bookmarks",
            "Saved this session:\n" + (url or "No page loaded yet")
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ALLINAGENT Browser")
    window = BrowserWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
'''
        readme = f"""# {name.replace('-', ' ').title()}

A starter desktop web browser generated by ALLINAGENT v1.8.0.

## Features
- Chromium-based page rendering through Qt WebEngine
- Address bar with URL navigation and web search
- Back, Forward, Reload, and Home controls
- Multiple tabs (Ctrl+T / Ctrl+W)
- Bookmark-current-page action (Ctrl+D; in-memory for this starter)
- Focus address bar (Ctrl+L)

## Requirements
- Python 3.10+
- A desktop environment supported by PySide6

## Install and run

    python -m pip install -r requirements.txt
    python main.py

The first installation downloads PySide6 and Qt WebEngine, which can be large.
This is a browser application using the Chromium engine supplied by Qt WebEngine,
not a new browser engine. Bookmarks are currently kept for the current session.
Generated by ALLINAGENT.
"""
        files = {
            f"{base}/main.py": main_py,
            f"{base}/requirements.txt": "PySide6>=6.6\n",
            f"{base}/README.md": readme,
        }
        created = []
        for path, data in files.items():
            result = self.tools.write_file(path, data)
            if "WRITE OK" in result:
                created.append(path)
            else:
                return (
                    "ALLINAGENT BROWSER BUILDER stopped safely.\n"
                    f"Could not write {path}: {result}\n"
                    + ("Files created before the issue:\n" + "\n".join(created) if created else "No files were created.")
                )
        return (
            "ALLINAGENT BROWSER BUILDER COMPLETE\n\n"
            f"Project: {name}\nFiles created: {len(created)}\n"
            + "\n".join(f"  + {path}" for path in created)
            + "\n\nNext steps:\n"
            f"  cd {name}\n  python -m pip install -r requirements.txt\n  python main.py\n\n"
            "Note: Qt WebEngine uses Chromium; bookmarks are session-only in this starter."
        )
