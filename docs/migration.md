# Migration and rollback

Adopt in shadow mode first:

Pin both the reusable workflow reference and its required `tooling-ref` input to
the same immutable tag or commit. During prerelease evaluation, use an exact
commit SHA so the workflow and installed CLI cannot drift.

1. **Inventory:** record the legacy implementation commit, required checks, path ownership, transitive inputs, commands, runner/toolchains, merge method, and post-merge dispatches. Keep product-specific policy in the consumer manifest.
2. **Install:** commit `.validation-fabric.yml` plus the thin unprivileged and `workflow_run` callers. Pin both `uses:` and `tooling-ref` to one immutable release commit during evaluation.
3. **Shadow:** run legacy CI and Validation Fabric for identical base/head pairs. Compare changed paths, selected domains, unknown paths, fingerprints, cache decisions, command outcomes, certificates, and admission outcomes.
4. **Reconcile:** classify every difference as an intentional policy correction or a defect. Expand ownership or fallback domains for every unexplained legacy-only failure and repeat the exact fixture.
5. **Trust-boundary proof:** submit a disposable candidate that attempts to change the manifest and caller. Prove candidate jobs have no signing or merge authority and that the default-branch verifier uses the trusted base manifest.
6. **Cut over:** update required checks to the public admission result only after the selected release has passed package, fixture, security, and live-shadow gates. Keep exact-candidate merge disabled unless separately approved.
7. **Observe:** retain the legacy workflow as manually dispatchable for one full observation window. Exercise at least one normal candidate and one stale/superseded dispatch on the public path.
8. **Retire:** remove the embedded planner, certificate, event, admission, merge, caller, and duplicate tests only after the observation record is green. Preserve the consumer manifest, callers, migration provenance, and rollback tag.

## Rollback trigger and procedure

Rollback when the public path has an unexplained selection, fingerprint, evidence, certificate, or admission divergence; when its required check cannot reach a trustworthy terminal state; or when release provenance cannot be verified.

1. Remove the public admission check from branch protection before changing callers.
2. Restore the legacy caller at its recorded rollback commit and make its check required.
3. Disable optional exact-candidate merge and post-merge dispatch while evidence is reconciled.
4. Preserve the failed source run, admission run, exact base/head pair, package/workflow ref, and sanitized comparison result.
5. Correct the public implementation through a new release; never retag an immutable version.

Certificates and evidence are diagnostic and do not mutate source state. A rollback therefore does not require source-history repair.

## Embedded implementation removal checklist

- No consumer script imports or executes embedded planner, fingerprint, certificate, event, admission, or merge code.
- Branch protection names only the intended public-path checks.
- Local developer commands install a pinned package and use `vv` directly.
- Product-specific commands, ownership, runners, toolchains, merge method, and post-merge dispatches exist only in `.validation-fabric.yml` or consumer callers.
- Duplicate embedded fixtures are deleted only after equivalent public-package fixtures pass.
- Documentation names the public release, immutable rollback ref, observation dates, and retained evidence.
- A repository search finds no distributable implementation copied into the consumer.

SessionBuddie is the first compatibility consumer and will use this dual-proof process before removing its embedded implementation.
