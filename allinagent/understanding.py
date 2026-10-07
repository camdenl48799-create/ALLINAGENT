"""Request understanding for ALLINAGENT.

Converts natural-language requests into structured task specifications.
Uses deterministic parsing with optional LLM enhancement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .inspector import ProjectInspection


@dataclass
class TaskSpec:
    """Structured specification for a task."""
    kind: str = "unknown"  # website, game, script, document, modify, inspect, unknown
    name: str = ""
    theme: str = ""
    color_scheme: str = ""
    pages: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)  # for modify: increase_size, change_color, etc.
    target_path: str = ""
    tech: str = "vanilla"
    requirements: list[str] = field(default_factory=list)
    followup_type: str = ""  # new, modify, add_page, make_responsive, change_color, etc.
    raw_prompt: str = ""

    def is_followup(self) -> bool:
        return self.followup_type != "" and self.followup_type != "new"


CREATE_VERBS = (r"\b(?:make|build|create|generate|scaffold|setup|design)\b",
                r"\bmake me\b", r"\blet'?s make\b", r"\bcan you (?:make|build|create)\b",
                r"\bi want\b.*\b(?:website|game|app|script|tool|document)\b")

MODIFY_VERBS = (r"\bmake\b.*\b(?:bigger|larger|smaller|darker|lighter|modern|cleaner)\b",
                r"\bchange\b.*\b(?:color|colour|theme|background|font|navigation|nav|menu|layout)\b",
                r"\badd\b.*\b(?:page|section|feature|button|form|table|image|gallery|level|page)\b",
                r"\bmake it\b.*\b(?:mobile|responsive|dark|light|modern)\b",
                r"\bundo\b", r"\bfix\b.*\b(?:error|bug|issue)\b")


class RequestAnalyzer:
    """Understands natural-language requests and converts them to TaskSpecs."""

    # Website page types
    PAGE_KEYWORDS = {
        "home": (r"\bhome(?:page)?\b", r"\blanding\b"),
        "products": (r"\bproducts?\b", r"\bshop\b", r"\bstore\b"),
        "about": (r"\babout\b", r"\babout us\b"),
        "contact": (r"\bcontact\b", r"\bcontact form\b"),
        "login": (r"\blogin\b", r"\bsign in\b", r"\bsignup\b", r"\bregister\b"),
        "dashboard": (r"\bdashboard\b", r"\badmin\b", r"\bsettings\b"),
        "blog": (r"\bblog\b", r"\bposts?\b", r"\barticles?\b"),
        "gallery": (r"\bgallery\b", r"\bphotos?\b", r"\bimages?\b"),
        "games": (r"\bgames?\b", r"\bplay\b"),
        "pricing": (r"\bpricing\b", r"\bplans\b", r"\bsubscription\b"),
        "services": (r"\bservices?\b",),
        "team": (r"\bteam\b", r"\bstaff\b"),
        "faq": (r"\bfaq\b", r"\bquestions?\b"),
        "settings": (r"\bsettings\b", r"\bpreferences\b"),
        "portfolio": (r"\bportfolio\b", r"\bprojects\b"),
    }

    # Feature keywords
    FEATURE_KEYWORDS = {
        "dark_mode": (r"\bdark mode\b", r"\bdark theme\b"),
        "light_mode": (r"\blight mode\b", r"\blight theme\b"),
        "animations": (r"\banimations?\b", r"\banimated\b", r"\btransitions?\b"),
        "contact_form": (r"\bcontact form\b", r"\bcontact page\b"),
        "search": (r"\bsearch\b", r"\bsearch (?:bar|interface|box)\b"),
        "login": (r"\blogin\b", r"\bauth\b", r"\bauthentication\b"),
        "responsive": (r"\bresponsive\b", r"\bmobile(?: friendly)?\b"),
        "gallery": (r"\bgallery\b", r"\bimage gallery\b"),
        "dashboard": (r"\bdashboard\b", r"\badmin (?:panel|dashboard)\b"),
        "chat": (r"\bchat\b", r"\bmessaging\b"),
        "comments": (r"\bcomments?\b", r"\breviews?\b"),
        "cart": (r"\bcart\b", r"\bshopping\b"),
        "payment": (r"\bpayment\b", r"\bcheckout\b", r"\bbilling\b"),
        "api": (r"\bapi\b",),
        "database": (r"\bdatabase\b", r"\bdb\b"),
        "multiplayer": (r"\bmultiplayer\b", r"\bonline\b"),
        "levels": (r"\blevels?\b", r"\bstages?\b"),
        "enemies": (r"\benemies?\b", r"\bmonsters?\b", r"\bopponents?\b"),
        "score": (r"\bscore\b", r"\bscoring\b", r"\bpoints?\b"),
        "health": (r"\bhealth\b", r"\blives?\b"),
        "pause": (r"\bpause\b", r"\bpause (?:menu|screen)\b"),
        "sound": (r"\bsound\b", r"\baudio\b", r"\bmusic\b"),
        "settings": (r"\bsettings\b", r"\bconfig\b"),
        "menu": (r"\bmenu\b", r"\bstart (?:menu|screen)\b"),
        "win_lose": (r"\bwin\b", r"\blose\b", r"\bgame over\b", r"\bwin/lose\b"),
        "difficulty": (r"\bdifficulty\b", r"\bhard mode\b", r"\beasy mode\b"),
    }

    # Theme/style keywords
    THEME_KEYWORDS = {
        "dark": (r"\bdark\b", r"\bblack\b"),
        "light": (r"\blight\b", r"\bbright\b"),
        "gaming": (r"\bgaming\b", r"\bgamer\b"),
        "modern": (r"\bmodern\b", r"\bsleek\b", r"\bclean\b"),
        "minimal": (r"\bminimal(?:ist)?\b", r"\bsimple\b"),
        "corporate": (r"\bcorporate\b", r"\bprofessional\b", r"\bbusiness\b"),
        "creative": (r"\bcreative\b", r"\bartistic\b", r"\bcolorful\b"),
        "tech": (r"\btech\b", r"\btechnology\b", r"\bdigital\b"),
    }

    def __init__(self) -> None:
        pass

    def analyze(self, prompt: str, inspection: ProjectInspection | None = None) -> TaskSpec:
        """Analyze a natural-language prompt and return a structured TaskSpec."""
        text = prompt.strip().lower()
        spec = TaskSpec(raw_prompt=prompt)

        if not text:
            spec.kind = "unknown"
            return spec

        # Determine if this is a creation or modification request
        is_create = self._matches_any(text, CREATE_VERBS)
        is_modify = self._matches_any(text, MODIFY_VERBS)

        # Detect specific kind
        kind = self._detect_kind(text)
        spec.kind = kind

        # Detect theme
        spec.theme = self._detect_theme(text)
        spec.color_scheme = self._detect_color_scheme(text, spec.theme)

        # Detect pages
        spec.pages = self._detect_pages(text)

        # Detect features
        spec.features = self._detect_features(text)

        # Detect followup type
        spec.followup_type = self._detect_followup_type(text, is_create, is_modify, inspection)

        # Determine name
        spec.name = self._extract_name(text, kind, spec.theme)

        # Determine tech
        spec.tech = self._detect_tech(text)

        # Build requirements list
        spec.requirements = self._extract_requirements(text)

        # Target path
        spec.target_path = spec.name

        # If followup, set kind to modify
        if spec.followup_type and spec.followup_type != "new":
            spec.kind = "modify"

        # If creation and no pages detected but kind is website, add default pages
        if kind == "website" and not spec.pages and spec.followup_type == "new":
            spec.pages = ["home"]

        return spec

    def _matches_any(self, text: str, patterns) -> bool:
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _detect_kind(self, text: str) -> str:
        if any(w in text for w in ("website", "web page", "web site", "landing page", "homepage")):
            return "website"
        if any(w in text for w in ("game", "arcade", "playable")):
            return "game"
        if any(w in text for w in ("script", "automation", "tool", "cli tool", "command line")):
            return "script"
        if any(w in text for w in ("document", "doc", "readme", "guide", "manual", "spec", "changelog", "project plan")):
            return "document"
        if any(w in text for w in ("app", "application", "dashboard", "tool")):
            return "app"
        return "website"

    def _detect_theme(self, text: str) -> str:
        for theme, patterns in self.THEME_KEYWORDS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                return theme
        return "default"

    def _detect_color_scheme(self, text: str, theme: str) -> str:
        if theme in ("dark", "gaming"):
            return "dark"
        if theme in ("light",):
            return "light"
        colors = re.findall(r"\b(red|blue|green|purple|orange|yellow|pink|cyan|teal|navy|gray|grey)\b", text)
        if colors:
            return colors[0]
        return "dark"

    def _detect_pages(self, text: str) -> list[str]:
        pages = []
        for page, patterns in self.PAGE_KEYWORDS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                if page not in pages:
                    pages.append(page)
        return pages

    def _detect_features(self, text: str) -> list[str]:
        features = []
        for feature, patterns in self.FEATURE_KEYWORDS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                if feature not in features:
                    features.append(feature)
        return features

    def _detect_followup_type(self, text: str, is_create: bool, is_modify: bool,
                               inspection: ProjectInspection | None) -> str:
        # Check for specific modification patterns first
        if re.search(r"\badd\b.*\b(page|section|feature)\b", text):
            page_match = re.search(r"\badd\b.*\b(\w+)\s+page\b", text)
            if page_match:
                return "add_page"
            return "add_feature"

        if re.search(r"\bmobile\b|\bresponsive\b", text):
            return "make_responsive"

        if re.search(r"\bundo\b", text):
            return "undo"

        if re.search(r"\bfix\b.*\b(?:error|bug|issue)\b", text):
            return "fix_error"

        if re.search(r"\bbigger\b|\blarger\b", text):
            return "increase_size"

        if re.search(r"\bsmaller\b", text):
            return "decrease_size"

        if re.search(r"\bdarker\b", text):
            return "darker"

        if re.search(r"\blighter\b|\bbrighter\b", text):
            return "lighter"

        if re.search(r"\bchange\b.*\b(?:color|colour)\b", text):
            return "change_color"

        if re.search(r"\bmodern(?:ize)?\b|\bmake it modern\b", text):
            return "modernize"

        if re.search(r"\b(?:change|update|modify)\b.*\b(?:navigation|nav|menu)\b", text):
            return "modify_nav"

        # If this is a create request and a project exists, it's a followup
        if is_create and inspection and inspection.total_files > 0:
            return "new"  # Create new project alongside existing

        if is_create:
            return "new"

        return ""

    def _extract_name(self, text: str, kind: str, theme: str) -> str:
        # Try "called X" or "named X" or "for X"
        name_match = re.search(
            r"(?:called|named)\s+['\"]?([a-z0-9][a-z0-9\-_\s]*?)['\"]?(?:\.|$|\s+(?:website|site|game|app|page))",
            text, re.IGNORECASE)
        if name_match:
            raw = name_match.group(1).strip().rstrip(".!")
            name = re.sub(r"[^a-z0-9\-]", "-", raw.lower()).strip("-")
            if name:
                return name

        # Try "for my company" or "for X"
        for_match = re.search(r"\bfor\s+(?:my\s+)?(\w+(?:\s+\w+)?)", text)
        if for_match and for_match.group(1) not in ("a", "an", "the", "my", "our", "company", "business"):
            raw = for_match.group(1).strip()
            name = re.sub(r"[^a-z0-9\-]", "-", raw.lower()).strip("-")
            if name and len(name) > 2:
                return f"{name}-{kind}"

        # Try to extract descriptive words before the kind keyword
        kind_words = {
            "website": ["website", "site", "page"],
            "game": ["game", "games"],
            "script": ["script", "tool", "automation"],
            "document": ["document", "doc", "report", "guide", "manual"],
            "app": ["app", "application"],
        }
        keywords = kind_words.get(kind, ["project"])
        pattern = r"make me (?:a |an )?(.+?)\s+(?:" + "|".join(keywords) + r")"
        desc_match = re.search(pattern, text, re.IGNORECASE)
        if desc_match:
            desc = desc_match.group(1).strip()
            name = re.sub(r"[^a-z0-9\-]", "-", desc.lower()).strip("-")
            if name and len(name) > 2:
                return f"{name}-{kind}"

        # Derive from theme + kind
        if kind == "website":
            if theme and theme != "default":
                return f"{theme}-website"
            return "my-website"
        elif kind == "game":
            return "my-game"
        elif kind == "script":
            return "my-script"
        elif kind == "document":
            return "my-document"
        elif kind == "app":
            # Check if React/Vite was mentioned
            if "react" in text or "vite" in text:
                return "react-app"
            return "my-app"
        return "my-project"

    def _detect_tech(self, text: str) -> str:
        if "react" in text or "next.js" in text or "nextjs" in text:
            return "react"
        if "tailwind" in text:
            return "tailwind"
        if "bootstrap" in text:
            return "bootstrap"
        return "vanilla"

    def _extract_requirements(self, text: str) -> list[str]:
        """Extract explicit requirements from the prompt."""
        reqs = []
        # "with X" patterns
        with_matches = re.findall(r"\bwith\b\s+([a-z][a-z\s\-]+?)(?:\s+(?:and|\.|$|,))", text)
        for m in with_matches:
            m = m.strip()
            if m and len(m) > 2 and m not in ("a", "an", "the"):
                reqs.append(m)
        return reqs[:15]

    def is_creation_request(self, prompt: str) -> bool:
        """Quick check if this is a creation/modify request."""
        text = prompt.strip().lower()
        if not text:
            return False
        return self._matches_any(text, CREATE_VERBS) or self._matches_any(text, MODIFY_VERBS)
