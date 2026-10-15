# Contributing

Issues, documentation improvements, tests, and focused pull requests are
welcome. Please avoid committing WRF output files or other large datasets.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
python -m pytest
```

New diagnostics should accept NumPy-compatible arrays where practical, state
their axis and unit conventions, and include a numerical test. Public examples
must use relative paths or command-line arguments rather than machine-specific
paths.

Before proposing a release, regenerate the public API guide and run the full
showcase in a new output directory:

```bash
wrf-tools capabilities --markdown docs/API_CATALOG.md
python examples/showcase_all_capabilities.py --output example_results/release-showcase
```

Review its failures and `UNACCOUNTED` entries; do not relabel missing execution
as a pass. Copy the successful JSON/Markdown coverage ledger to `docs/validation/`
when recording a new audited snapshot. Every new physical diagnostic needs
method references, applicability limits and independent numerical assertions,
not only a plot or runtime-entry count. Real observations must remain distinct
from synthetic fixtures. See [the audit](docs/AUDIT.md).
