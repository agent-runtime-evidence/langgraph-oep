# Contributing

This package is an alpha reference implementation. Keep changes small,
inspectable, and aligned with the public claim boundary in
[`docs/public_claims.md`](docs/public_claims.md).

Before proposing a change, run:

```bash
ruff check src/ tests/
mypy src/
pytest -v --tb=short
python -m build
twine check dist/*
```

Do not add endorsement, partnership, official-integration, replacement, or
production-certified framing. Placeholder policy evidence is for examples only
and must not be presented as real policy proof.
