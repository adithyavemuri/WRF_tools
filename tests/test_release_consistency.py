"""Keep examples/scripts/docs tied to the actual package, not an old release."""
import ast
import importlib
from pathlib import Path
import re

from wrf_tools.capabilities import capability_catalog, write_capability_guide

ROOT=Path(__file__).resolve().parents[1]


def test_local_package_imports_in_source_scripts_examples_and_tests_exist():
    for directory in ("src","scripts","examples","tests"):
        for path in (ROOT/directory).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        if alias.name=="wrf_tools" or alias.name.startswith("wrf_tools."):
                            importlib.import_module(alias.name)
                elif isinstance(node,ast.ImportFrom) and node.module and (node.module=="wrf_tools" or node.module.startswith("wrf_tools.")):
                    module=importlib.import_module(node.module)
                    for alias in node.names:
                        if alias.name=="*" or hasattr(module,alias.name): continue
                        try: importlib.import_module(f"{node.module}.{alias.name}")
                        except ImportError as exc:
                            raise AssertionError(f"{path.relative_to(ROOT)}:{node.lineno}: stale import {node.module}.{alias.name}") from exc


def test_published_api_catalog_matches_source(tmp_path):
    generated=write_capability_guide(tmp_path/"API.md")
    assert generated.read_text(encoding="utf-8") == (ROOT/"docs/API_CATALOG.md").read_text(encoding="utf-8"), "Regenerate with wrf-tools capabilities --markdown docs/API_CATALOG.md"


def test_repository_markdown_local_file_links_exist():
    files=[ROOT/"README.md",ROOT/"CONTRIBUTING.md",*(ROOT/"docs").rglob("*.md"),*(ROOT/"examples").rglob("*.md")]
    for path in files:
        for target in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8")):
            if target.startswith(("https://","http://","mailto:","#")): continue
            target=target.split("#",1)[0].strip("<>")
            assert (path.parent/target).exists(),f"{path.relative_to(ROOT)}: broken file link {target}"


def test_checked_capability_ledger_accounts_for_current_public_surface():
    import hashlib
    import json
    ledger=json.loads((ROOT/"docs/validation/capability-coverage.json").read_text(encoding="utf-8"))
    catalog=capability_catalog()
    assert {row["id"] for row in ledger["capabilities"]}==set(catalog)
    assert not ledger["failures"] and "UNACCOUNTED" not in ledger["counts"]
    assert all(row["basis"]==catalog[row["id"]]["basis"] for row in ledger["capabilities"])
    package=ROOT/"src/wrf_tools"
    digest=hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode()); digest.update(path.read_bytes())
    assert ledger["package_source_sha256"]==digest.hexdigest(), "Rerun the showcase and refresh docs/validation after changing package source"


def test_publishable_text_has_no_machine_specific_home_paths():
    # Match private workstation roots, not generic /path/to inputs or a public
    # author/repository URL. Generated runtime data is not a publication source.
    paths=[ROOT/"README.md",ROOT/"CONTRIBUTING.md",ROOT/"pyproject.toml",ROOT/".gitignore"]
    paths += [p for folder in ("src","docs","examples","scripts") for p in (ROOT/folder).rglob("*")
              if p.is_file() and p.suffix in {".py",".md",".toml",".json"}]
    forbidden=re.compile(r"/home/[^/\s]+/|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+[\\/]")
    for path in paths:
        assert not forbidden.search(path.read_text(encoding="utf-8")),f"Machine-specific path in {path.relative_to(ROOT)}"
