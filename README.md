# Validation Fabric

Validation Fabric selects validation by changed-path risk, fingerprints the exact inputs and commands, and admits only evidence bound to an exact repository, workflow run, base, and candidate SHA.

It ships as the `validation-fabric` Python package, the `vv` CLI, a GitHub Action, and reusable GitHub workflows. Exact-candidate merging is available but disabled by default.

> Status: `0.1.0a1` bootstrap. The API is intentionally prerelease until fixture adoption and SessionBuddie shadow parity are complete.

## Quick start

```bash
python -m pip install validation-fabric
vv init --preset python
vv doctor
vv plan --base origin/main --head HEAD
vv run --base origin/main --head HEAD
```

Commit `.validation-fabric.yml` and the thin callers from [`examples/github`](examples/github). The PR caller receives read-only permissions and no admission or merge credential. The privileged caller must live on the default branch and run only from `workflow_run`.

## Why it is different

- Unknown files widen to conservative fallback domains.
- Domain dependencies close transitively.
- Fingerprints cover changed content, declared inputs, commands, runner, toolchain, and configuration schema.
- PR jobs publish unsigned evidence; they do not possess trust keys.
- Default-branch code recomputes the plan and binds evidence to the originating run before signing admission.
- Stale exact SHA pairs are neutral supersessions, while malformed configuration and invalid evidence fail closed.

Read the [configuration reference](docs/configuration.md), [security model](docs/security-model.md), and [migration guide](docs/migration.md).

## Provenance

Validation Fabric was extracted from the implementation first proven in [Enchantus/SessionBuddie](https://github.com/Enchantus/SessionBuddie). The public package excludes SessionBuddie product configuration and private operational data. The extraction source and compatibility evidence are tracked in [issue #1](https://github.com/Enchantus/validation-fabric/issues/1).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
