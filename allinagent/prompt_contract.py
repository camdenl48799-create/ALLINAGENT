"""Detailed-prompt requirement tracking for ALLINAGENT v1.5.0."""
from __future__ import annotations
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Requirement:
    id: int
    text: str

@dataclass(frozen=True)
class Contract:
    prompt: str
    requirements: list[Requirement]

    def summary(self) -> str:
        lines=["ALLINAGENT PROMPT CONTRACT", "", f"Requirements: {len(self.requirements)}"]
        lines += [f"{r.id}. {r.text}" for r in self.requirements]
        return "\n".join(lines)

def build_contract(prompt: str) -> Contract:
    raw=[]
    for line in prompt.splitlines():
        s=re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if len(s)>=4: raw.append(s)
    if not raw:
        parts=re.split(r"\s+(?:and|plus)\s+|[,;]", prompt)
        raw=[p.strip() for p in parts if len(p.strip())>=8]
    # Keep explicit prompt wording; de-duplicate without silently dropping detail.
    seen=set(); req=[]
    for item in raw:
        key=item.casefold()
        if key not in seen:
            seen.add(key); req.append(Requirement(len(req)+1,item))
    return Contract(prompt, req[:50])

def verification_instructions(contract: Contract) -> str:
    items="\n".join(f"{r.id}. {r.text}" for r in contract.requirements)
    return ("Before finishing, verify every requirement below. Do not claim a requirement is complete "
            "unless the implementation actually satisfies it. Report any unmet item honestly.\n\n"
            "REQUIREMENTS:\n" + items + "\n\n"
            "FINAL CHECK: list each requirement as PASS or NOT VERIFIED and briefly state the evidence.")
