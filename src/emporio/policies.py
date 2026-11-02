"""Store policies, loaded from the curated markdown and keyed by section."""

import re
from functools import lru_cache
from pathlib import Path

POLICIES_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "policies.md"

_HEADING = re.compile(r"^## (\w+) \| (.+)$", re.MULTILINE)


@lru_cache
def load_policies(path: Path = POLICIES_PATH) -> dict[str, dict[str, str]]:
    """Return {key: {"title": ..., "content": ...}} for every '## key | title' section."""
    text = path.read_text(encoding="utf-8")
    matches = list(_HEADING.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = {"title": m.group(2).strip(), "content": text[m.end():end].strip()}
    return sections
