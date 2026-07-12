#!/usr/bin/env python3
"""Map a campaign name to its topic group (default group = campaign name)."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MAP = os.environ.get(
    "CAMPAIGN_GROUPS_JSON", os.path.join(_HERE, "campaign_groups.json")
)


def load_group_index(path=DEFAULT_MAP):
    """Return {campaign_name: group_name} inverted from the config file."""
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    index = {}
    for group, campaigns in cfg.get("groups", {}).items():
        for c in campaigns:
            index[c] = group
    return index


def group_for(campaign, index=None, path=DEFAULT_MAP):
    """Group for a campaign; unknown campaigns dedup only against themselves."""
    if index is None:
        index = load_group_index(path)
    return index.get(campaign, campaign)
