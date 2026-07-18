from pathlib import Path

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
ACTION = Path(__file__).parents[1] / "action.yml"


def test_reusable_workflows_do_not_self_reference_unpublished_major() -> None:
    for name in ("validate.yml", "admit.yml", "merge.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "Enchantus/validation-fabric@v1" not in text
        assert "tooling-ref:" in text
        assert "repository: Enchantus/validation-fabric" in text
        assert "ref: ${{ inputs.tooling-ref }}" in text
        assert "uses: ./.validation-fabric-tooling" in text


def test_action_supports_declared_consumer_toolchains() -> None:
    text = ACTION.read_text(encoding="utf-8")
    for toolchain in ("python", "uv", "node", "go"):
        assert f"fromJSON(inputs.toolchain).{toolchain}" in text
