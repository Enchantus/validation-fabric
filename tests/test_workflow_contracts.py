import re
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


def test_validation_and_admission_use_the_trusted_base_manifest() -> None:
    for name in ("validate.yml", "admit.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert 'git show "${{ inputs.base }}:.validation-fabric.yml"' in text
        assert '--config "$RUNNER_TEMP/validation-fabric-base.yml"' in text
        assert "head-repository:" in text
        assert "repository: ${{ inputs.head-repository || github.repository }}" in text
    admission = (WORKFLOWS / "admit.yml").read_text(encoding="utf-8")
    assert "source-run-title:" in admission
    assert 'default: pull_request_target' in admission
    assert '.display_title == $run_title' in admission
    assert 'actions/workflows/$workflow_id' in admission
    assert '.name == $workflow and .path == $workflow_path and .state == "active"' in admission
    assert '.name == $workflow and .event' not in admission
    assert '.head_sha == $head' in admission
    assert '$source_event == "pull_request_target" and .head_sha == $base' not in admission
    assert "merge-multiple: false" in admission
    assert "! -name '*plan*'" not in admission


def test_merge_requires_certificate_and_admission_run() -> None:
    text = (WORKFLOWS / "merge.yml").read_text(encoding="utf-8")
    assert "admission-run-id:" in text
    assert "certificate-key:" in text
    assert "actions/download-artifact@" in text
    assert '--certificate "$certificate"' in text
    assert "git show \"$base:.validation-fabric.yml\"" in text
    assert '--config "$RUNNER_TEMP/validation-fabric-base.yml" merge' in text


def test_action_supports_declared_consumer_toolchains() -> None:
    text = ACTION.read_text(encoding="utf-8")
    for toolchain in ("python", "uv", "node", "go"):
        assert f"fromJSON(inputs.toolchain).{toolchain}" in text


def test_release_always_attests_github_artifacts_and_gates_pypi() -> None:
    text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    assert "actions/attest-build-provenance@" in text
    assert 'gh release create "$GITHUB_REF_NAME"' in text
    assert "if: vars.PYPI_PUBLISH_ENABLED == 'true'" in text


def test_all_external_actions_are_immutably_pinned() -> None:
    sources = [ACTION, *WORKFLOWS.glob("*.yml")]
    for source in sources:
        for line in source.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("- uses: ") or "uses: ./" in stripped:
                continue
            reference = stripped.split("#", 1)[0].rsplit("@", 1)[-1].strip()
            assert re.fullmatch(r"[0-9a-f]{40}", reference), f"unpinned action in {source}: {line}"


def test_recommended_caller_is_default_branch_owned_and_read_only() -> None:
    text = ACTION.parent / "examples" / "github" / "validation-fabric.yml"
    source = text.read_text(encoding="utf-8")
    assert "pull_request_target:" in source
    assert "run-name: Validation Fabric PR #" in source
    assert "contents: read" in source
    assert "head-repository: ${{ github.event.pull_request.head.repo.full_name }}" in source


def test_admission_caller_skips_superseded_ranges() -> None:
    source = (ACTION.parent / "examples" / "github" / "validation-fabric-admission.yml").read_text(encoding="utf-8")
    assert "state: ${{ steps.pull.outputs.state }}" in source
    assert "if: needs.resolve.outputs.state == 'planned'" in source
