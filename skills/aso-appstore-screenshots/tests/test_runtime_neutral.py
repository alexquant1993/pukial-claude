"""Guard the active ASO instructions against host-specific assumptions."""

from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
ACTIVE_INSTRUCTION_FILES = [
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "README.md",
    *sorted((SKILL_ROOT / "references").glob("*.md")),
]
FORBIDDEN_RUNTIME_MARKERS = (
    "AskUserQuestion",
    "~/.claude",
    "$HOME/.claude",
    "Claude Code's auto-memory",
    "Read tool",
)


def test_active_instructions_are_host_neutral() -> None:
    violations = {
        path.relative_to(SKILL_ROOT): marker
        for path in ACTIVE_INSTRUCTION_FILES
        for marker in FORBIDDEN_RUNTIME_MARKERS
        if marker in path.read_text()
    }

    assert not violations, f"Host-specific markers remain: {violations}"


def test_memory_contract_is_project_local_and_gate_is_host_neutral() -> None:
    skill_text = (SKILL_ROOT / "SKILL.md").read_text()
    schema_text = (SKILL_ROOT / "references" / "memory-schema.md").read_text()

    assert ".aso/MEMORY.md" in skill_text
    assert ".aso/" in schema_text
    assert "USER_INPUT_GATE" in skill_text
