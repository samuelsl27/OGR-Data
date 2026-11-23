"""Minimal test runner: discovers tests/test_*.py, runs them, reports.

No pytest dependency (the suite convention is its own runner; OGR Data is
standalone and keeps the same spirit).
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import traceback
from pathlib import Path


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = Path(__file__).parent
    sys.path.insert(0, str(root.parent))
    # spec 025b: the program's settings go to a throwaway INI file, never to
    # the user's (the registry on Windows)
    from ogr_data.gui.settings import isolate_for_tests

    settings_dir = tempfile.mkdtemp(prefix="ogr-data-settings-")
    isolate_for_tests(settings_dir)
    try:
        return _run(root)
    finally:
        shutil.rmtree(settings_dir, ignore_errors=True)


def _run(root: Path) -> int:
    passed = failed = 0
    failures: list[str] = []
    for file in sorted(root.glob("test_*.py")):
        module = _load_module(file)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            label = f"{file.name}::{name}"
            try:
                fn()
            except Exception:
                failed += 1
                failures.append(label + "\n" + traceback.format_exc())
                print(f"FAIL {label}")
            else:
                passed += 1
                print(f"ok   {label}")
    print(f"\nPassed: {passed}  Failed: {failed}")
    if failures:
        print("\n".join(failures))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
