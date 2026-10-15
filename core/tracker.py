# core/announcement_tracker.py

import json
from typing import List, Set, Dict

def load_known_ids(filepath: str) -> Set[str]:
    """Load known announcement IDs from a file."""
    try:
        with open(filepath, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_known_ids(known_ids: Set[str], filepath: str):
    """Save known announcement IDs to a file."""
    with open(filepath, "w") as f:
        json.dump(list(known_ids), f)

def get_new_announcements(fetched_announcements: List[Dict], known_ids: Set[str]) -> List[Dict]:
    """Return only the announcements that are new (not in known_ids)."""
    return [ann for ann in fetched_announcements if ann["_id"] not in known_ids]

def update_known_ids(fetched_announcements: List[Dict], known_ids: Set[str]) -> Set[str]:
    """Update the set of known IDs with IDs from the latest fetch."""
    return known_ids.union({ann["_id"] for ann in fetched_announcements})
