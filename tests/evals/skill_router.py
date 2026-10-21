"""Skill files for eval prompts, read from the Required Load Packets of AGENTS.md.

AGENTS.md is the single source of truth for which files a task loads, so packets are
parsed from it rather than listed here. Questions name a packet by any unique part of
its heading, case-insensitive: ``"data loading"``, ``"Brain Wide Map"``, ``"atlas"``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]


def load_packets(agents_md: Path = REPO_ROOT.joinpath("AGENTS.md")) -> dict[str, list[Path]]:
    """Return ``{heading: [files]}`` for every packet of the Required Load Packets section.

    A packet is a line ending in ``:`` followed by bullets; every backticked path in a
    bullet is a file, or a directory standing for all the markdown files under it.
    """
    section = agents_md.read_text().split("## Required Load Packets", 1)[1].split("\n## ", 1)[0]
    packets: dict[str, list[Path]] = {}
    current = None
    for line in section.splitlines():
        if line.endswith(":") and not line.startswith("-"):
            current = packets.setdefault(line.removesuffix(":").strip(), [])
        elif current is not None and line.startswith("- "):
            for rel in re.findall(r"`([^`]+)`", line):
                path = REPO_ROOT.joinpath(rel)
                current += sorted(path.rglob("*.md")) if path.is_dir() else [path]
    return packets


PACKETS = load_packets()


def get_skill_files(*packets: str) -> list[Path]:
    """Return deduplicated file paths for the named packets, in the order named.

    Parameters
    ----------
    *packets
        Each a part of exactly one packet heading, case-insensitive.

    Returns
    -------
    list[Path]

    Raises
    ------
    KeyError
        If a name matches no heading, or more than one.
    """
    files: list[Path] = []
    for name in packets:
        matches = [key for key in PACKETS if name.lower() in key.lower()]
        if len(matches) != 1:
            raise KeyError(f"{name!r} matches {len(matches)} packets: {matches}")
        files += [path for path in PACKETS[matches[0]] if path not in files]
    return files
