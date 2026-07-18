# Contributing

Open an issue before substantial changes and use an issue-linked branch. Keep changes narrowly reviewable and add tests near changed trust behavior.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m build
```

Never place credentials, private logs, personal data, or product-specific private configuration in issues, fixtures, or commits. Pull-request execution must remain unprivileged.
