from pathlib import Path
import json
import pytest
from allinagent.memory import LocalMemory, MAX_ENTRIES


def test_malformed_memory_is_reported_and_preserved(tmp_path: Path):
    path = tmp_path / '.allinagent-memory.json'
    original = b'{broken'
    path.write_bytes(original)
    memory = LocalMemory(tmp_path)
    assert memory._load() == []
    assert memory.load_error
    assert 'warning' in memory.status().lower()
    assert path.read_bytes() == original


def test_memory_save_caps_entries(tmp_path: Path):
    memory = LocalMemory(tmp_path)
    memory._save([{'prompt': str(i), 'response': 'ok'} for i in range(MAX_ENTRIES + 3)])
    assert len(json.loads(memory.path.read_text(encoding='utf-8'))) == MAX_ENTRIES
