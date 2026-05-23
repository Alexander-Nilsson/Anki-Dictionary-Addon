# Development

## Setup

```bash
git clone <repository-url>
cd anki-dictionary-addon
uv sync
```

## Workflow

```bash
python dev.py ci     # Run linting + tests
python dev.py build  # Build for testing
```

## Commands

| Command | Action |
|---|---|
| `uv sync` | Install dependencies |
| `python dev.py test` | Run test suite (unit + integration) |
| `python dev.py lint` | flake8 + black --check |
| `python dev.py format` | black auto-format |
| `python dev.py ci` | lint + test (full CI check) |
| `python dev.py build` | Build .ankiaddon package |
| `python dev.py clean` | Clean build artifacts |
| `pytest tests/ -m "not integration and not network" --ignore=tests/test_all_dictionaries.py --ignore=tests/test_dictionary_index.py` | Fast unit tests only |
| `pytest tests/integration/` | Integration tests (needs anki installed) |
| `act -P ubuntu-latest=catthehacker/ubuntu:act-24.04 -j pipeline --input=false` | Run CI locally via act (use 24.04 image for correct manylinux) |

## CI

The CI workflow (`.github/workflows/ci.yml`) runs lint, test, and build on every push to master.

To run it locally with act:

```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-24.04 -j pipeline --input=false
```

The `act-24.04` image is required because `anki` ships `manylinux_2_36` wheels and older containers only expose `manylinux_2_35` to uv's platform detection.

## Code Conventions

- **Naming:** `snake_case` for vars/funcs, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Formatting:** black (line length 88), flake8 (complexity ≤ 10)
- **Types:** Pyright strict mode — all new code must have type hints
- **Imports:** Absolute within package (`from anki_dictionary.core.database import DictDB`)
- **Logging:** Use `get_logger("module_name")` from `utils/logger.py`
- **Config:** Access via `miInfo()` / `miAsk()` from `utils/common.py`
- **Anki globals:** `mw` is injected at runtime; do not import at module level in testable code
