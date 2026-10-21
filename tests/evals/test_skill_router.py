"""Unit tests for the AGENTS.md packet parser. No API calls."""

import pytest

from tests.evals.skill_router import PACKETS, get_skill_files, load_packets


@pytest.mark.parametrize("packet", sorted(PACKETS))
def test_every_path_in_agents_md_exists(packet):
    # A renamed or removed skill file in AGENTS.md would silently thin a prompt.
    assert PACKETS[packet], "packet has no files"
    assert not [str(path) for path in PACKETS[packet] if not path.exists()]


def test_packets_are_parsed_from_the_given_file(tmp_path):
    agents = tmp_path.joinpath("AGENTS.md")
    agents.write_text(
        "# Top\n\n## Required Load Packets\n\nFirst packet:\n- `a.md` when needed\n"
        "- `b.md` and `c.md`\n\nSecond:\n- `a.md`\n\n## Next section\n\nIgnored:\n- `d.md`\n"
    )
    names = {key: [p.name for p in files] for key, files in load_packets(agents).items()}
    assert names == {"First packet": ["a.md", "b.md", "c.md"], "Second": ["a.md"]}


def test_a_packet_is_found_by_part_of_its_heading_and_files_are_deduplicated():
    files = get_skill_files("data loading", "DATA LOADING", "atlas")
    assert files == get_skill_files("data loading") + get_skill_files("atlas")


@pytest.mark.parametrize("name", ["not-a-packet", "IBL"])  # no match; several matches
def test_a_name_matching_zero_or_several_packets_raises(name):
    with pytest.raises(KeyError):
        get_skill_files(name)
