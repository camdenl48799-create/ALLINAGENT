"""Optional commerce configuration for ALLINAGENT.

Sensitive payment details belong to the selected payment provider, not to
ALLINAGENT project files.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class CommerceConfig:
    enabled: bool = False
    provider: str | None = None
    currency: str = "USD"
    checkout_mode: str = "hosted"
    onboarding_url: str | None = None
    catalog: list[dict] | None = None

SUPPORTED_PROVIDERS = {
    "stripe": "https://stripe.com",
    "paypal": "https://www.paypal.com",
    "shopify": "https://www.shopify.com",
}

class CommerceManager:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path.resolve()
        self.path = self.project_path / ".allinagent-commerce.json"

    def load(self) -> CommerceConfig:
        try:
            return CommerceConfig(**json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return CommerceConfig()

    def save(self, config: CommerceConfig) -> None:
        self.path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")

    def enable(self, provider: str, currency: str = "USD") -> CommerceConfig:
        key = provider.casefold().strip()
        if key not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported provider: " + provider)
        c = self.load()
        c.enabled, c.provider = True, key
        c.currency, c.checkout_mode = currency.upper(), "hosted"
        c.onboarding_url, c.catalog = SUPPORTED_PROVIDERS[key], c.catalog or []
        self.save(c)
        return c

    def disable(self) -> CommerceConfig:
        c = self.load()
        c.enabled = False
        self.save(c)
        return c

    def add_product(self, name: str, price_minor: int, description: str = "", sku: str | None = None) -> dict:
        if price_minor < 0:
            raise ValueError("price_minor cannot be negative")
        item_id = re.sub(r"[^A-Za-z0-9_-]", "-", sku or name).strip("-")[:64] or "product"
        c = self.load()
        catalog = list(c.catalog or [])
        existing = {str(x.get("id")) for x in catalog}
        base = item_id
        n = 2
        while item_id in existing:
            item_id = f"{base}-{n}"
            n += 1
        item = {"id": item_id, "name": name.strip(), "price_minor": int(price_minor),
                "currency": c.currency, "description": description.strip()}
        catalog.append(item)
        c.catalog = catalog
        self.save(c)
        return item

    def status(self) -> str:
        c = self.load()
        lines = ["ALLINAGENT SELLING", f"- enabled: {c.enabled}",
                 f"- provider: {c.provider or 'none'}", f"- currency: {c.currency}",
                 f"- checkout: {c.checkout_mode}", f"- products: {len(c.catalog or [])}"]
        if c.onboarding_url:
            lines.append("- provider setup: " + c.onboarding_url)
        lines += ["", "Security:",
                  "- Raw card, bank, and CVV data are never stored by this manager.",
                  "- Checkout is provider-hosted by design.",
                  "- Selling is optional; projects work normally with selling disabled."]
        return "\n".join(lines)
