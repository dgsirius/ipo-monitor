import glob
import json
import os


def latest_data_file(data_dir="data"):
    """Return path to most recent YYYY-MM-DD.json, or None if empty."""
    pattern = os.path.join(data_dir, "????-??-??.json")
    files = sorted(glob.glob(pattern), reverse=True)
    return files[0] if files else None


def load_all_data(data_dir="data"):
    """Load all weekly JSON files, sorted newest-first."""
    pattern = os.path.join(data_dir, "????-??-??.json")
    files = sorted(glob.glob(pattern), reverse=True)
    result = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            result.append(json.load(fh))
    return result
