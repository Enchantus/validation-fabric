"""Exercise one example as a clean consumer repository."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
CHANGED_FILES = {
    "python": ("src/fixture.py",),
    "node": ("src/add.js",),
    "go": ("add.go",),
    "polyglot": ("backend/app.py", "web/src/add.js", "edge/add.go"),
}


def run(*args: str, cwd: Path, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("preset", choices=tuple(CHANGED_FILES))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"validation-fabric-{args.preset}-") as temporary:
        consumer = Path(temporary) / "consumer"
        shutil.copytree(ROOT / "examples" / args.preset, consumer)
        run("git", "init", "-b", "main", cwd=consumer)
        run("git", "config", "user.email", "fixture@example.invalid", cwd=consumer)
        run("git", "config", "user.name", "Validation Fabric Fixture", cwd=consumer)
        run("git", "add", ".", cwd=consumer)
        run("git", "commit", "-m", "fixture base", cwd=consumer)
        base = run("git", "rev-parse", "HEAD", cwd=consumer, capture=True)
        for relative in CHANGED_FILES[args.preset]:
            path = consumer / relative
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        run("git", "add", ".", cwd=consumer)
        run("git", "commit", "-m", "fixture candidate", cwd=consumer)
        head = run("git", "rev-parse", "HEAD", cwd=consumer, capture=True)
        run("vv", "doctor", cwd=consumer)
        run("vv", "plan", "--base", base, "--head", head, cwd=consumer)
        run("vv", "run", "--base", base, "--head", head, cwd=consumer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
