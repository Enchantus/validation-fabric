from pathlib import Path

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"


def test_reusable_workflows_do_not_self_reference_unpublished_major() -> None:
    for name in ("validate.yml", "admit.yml", "merge.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "Enchantus/validation-fabric@v1" not in text
        assert "tooling-ref:" in text
        assert "repository: Enchantus/validation-fabric" in text
        assert "ref: ${{ inputs.tooling-ref }}" in text
        assert "uses: ./.validation-fabric-tooling" in text
