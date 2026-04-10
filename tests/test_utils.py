# tests/test_utils.py
import json
import os
import tempfile
import pytest
from scripts.utils import latest_data_file, load_all_data


def test_latest_data_file_returns_newest(tmp_path):
    (tmp_path / "2026-04-07.json").write_text("{}")
    (tmp_path / "2026-04-14.json").write_text("{}")
    (tmp_path / "2026-03-31.json").write_text("{}")
    result = latest_data_file(str(tmp_path))
    assert result == str(tmp_path / "2026-04-14.json")


def test_latest_data_file_empty_dir(tmp_path):
    result = latest_data_file(str(tmp_path))
    assert result is None


def test_load_all_data_returns_sorted_desc(tmp_path):
    week_a = {"week": "2026-04-07", "ipos": []}
    week_b = {"week": "2026-04-14", "ipos": []}
    (tmp_path / "2026-04-07.json").write_text(json.dumps(week_a))
    (tmp_path / "2026-04-14.json").write_text(json.dumps(week_b))
    result = load_all_data(str(tmp_path))
    assert result[0]["week"] == "2026-04-14"
    assert result[1]["week"] == "2026-04-07"
