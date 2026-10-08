"""Safe local security heuristics for ALLINAGENT v1.5.0.

This is a defensive scanner, not a replacement for Windows Security. It only
quarantines files inside the configured workspace and never modifies protected
Windows directories.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, re, shutil

PROTECTED_NAMES = {"system32", "syswow64", "winsxs", "boot", "servicing", "systemapps"}
SUSPICIOUS_PATTERNS = [
    (re.compile(r"powershell(?:\.exe)?[^\n]{0,160}-enc(?:odedcommand)?", re.I), 35, "encoded PowerShell command"),
    (re.compile(r"(?:invoke-expression|iex)\s*\(", re.I), 20, "dynamic command execution"),
    (re.compile(r"(?:downloadstring|webclient|bitsadmin|certutil)\b", re.I), 20, "network payload/downloader pattern"),
    (re.compile(r"(?:ransom|encrypt(?:ed|ion)?\s+files?)", re.I), 25, "ransomware-like wording"),
]

@dataclass
class Finding:
    path: str
    score: int
    reasons: list[str]
    sha256: str
    status: str = "review"

    @property
    def confidence(self) -> float:
        return min(100.0, max(0.0, float(self.score)))

class SecurityScanner:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.quarantine = self.workspace / ".allinagent" / "quarantine"

    def _safe(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.workspace)
            return True
        except ValueError:
            return False

    def scan_file(self, path: str | Path) -> Finding | None:
        p = Path(path)
        if not p.is_absolute(): p = self.workspace / p
        p = p.resolve()
        if not self._safe(p) or not p.is_file(): return None
        if any(part.casefold() in PROTECTED_NAMES for part in p.parts): return None
        try:
            data = p.read_bytes()
        except OSError:
            return None
        text = data[:2_000_000].decode("utf-8", errors="ignore")
        score = 0; reasons=[]
        for pattern, weight, reason in SUSPICIOUS_PATTERNS:
            if pattern.search(text): score += weight; reasons.append(reason)
        if p.suffix.casefold() in {".exe", ".dll", ".scr", ".msi", ".vbs", ".js"}:
            score += 5; reasons.append("executable/script file type")
        digest = hashlib.sha256(data).hexdigest()
        if score == 0: return Finding(str(p.relative_to(self.workspace)), 0, [], digest, "clean")
        status = "high-risk" if score >= 55 else "suspicious"
        return Finding(str(p.relative_to(self.workspace)), min(score, 100), reasons, digest, status)

    def scan_workspace(self, limit: int = 500) -> list[Finding]:
        findings=[]
        for p in self.workspace.rglob("*"):
            if len(findings) >= limit: break
            if p.is_file() and ".allinagent" not in p.parts:
                f=self.scan_file(p)
                if f and f.score >= 20: findings.append(f)
        return findings

    def quarantine_file(self, path: str) -> str:
        p=(self.workspace / path).resolve()
        if not self._safe(p) or not p.is_file(): return "QUARANTINE DENIED: file must be inside the workspace."
        if any(part.casefold() in PROTECTED_NAMES for part in p.parts): return "QUARANTINE DENIED: protected system path."
        self.quarantine.mkdir(parents=True, exist_ok=True)
        target=self.quarantine / (p.name + ".quarantined")
        if target.exists(): return "QUARANTINE DENIED: destination already exists."
        shutil.move(str(p), str(target))
        return f"QUARANTINED: {p.relative_to(self.workspace)} -> {target.relative_to(self.workspace)}"

def format_findings(findings: list[Finding]) -> str:
    if not findings: return "ALLINAGENT SECURITY SCAN\n\nNo suspicious files detected by local heuristics."
    lines=["ALLINAGENT SECURITY SCAN", "", f"Findings: {len(findings)}"]
    for f in findings:
        lines.append(f"- {f.path}: {f.confidence:.0f}% confidence ({f.status})")
        for r in f.reasons: lines.append(f"    reason: {r}")
    lines += ["", "Important: confidence is a risk estimate, not proof of malware.",
              "Use Windows Security/Defender for authoritative malware remediation."]
    return "\n".join(lines)
