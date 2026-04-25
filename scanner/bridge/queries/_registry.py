"""
Query plugin registry — auto-discovery for queries/ folder.

Each q_*.py file in this folder is auto-discovered at first access. Plugin
contract: must export QUERY_NAME (str) and run() (callable).

The composer calls get_query(name) to look up plugins by name. evidence_collector
uses this to dispatch to plugins in deterministic order.

Adding a new query = adding a new q_*.py file. No registry edits needed.

See doc/bridge_design_v1.md §1.2 (plugin architecture), §8.4 (queries folder).
"""

import importlib
from pathlib import Path
from typing import Callable, Optional


_registry: dict = {}
_failed_imports: list = []
_initialized: bool = False


def get_query(name: str) -> Optional[Callable]:
    """Returns the run() callable for the named plugin, or None."""
    _ensure_initialized()
    return _registry.get(name)


def list_queries() -> list:
    """Returns sorted list of discovered query names."""
    _ensure_initialized()
    return sorted(_registry.keys())


def get_failed_imports() -> list:
    """Returns list of (filename, error_msg) tuples for failed plugins."""
    _ensure_initialized()
    return list(_failed_imports)


def reset_registry() -> None:
    """Clears state. Next access re-runs discovery."""
    global _initialized
    _registry.clear()
    _failed_imports.clear()
    _initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        _discover()
        _initialized = True


def _discover() -> None:
    """
    Scan this folder for q_*.py files. Import each. Validate QUERY_NAME
    and run() are present. Plugin failures land in _failed_imports;
    the registry as a whole still works.
    """
    queries_dir = Path(__file__).parent

    for path in sorted(queries_dir.glob("q_*.py")):
        # Defensive: glob already excludes _* but the spec calls
        # for an explicit guard.
        if path.name.startswith("_"):
            continue

        module_name = f"scanner.bridge.queries.{path.stem}"

        try:
            mod = importlib.import_module(module_name)
        except Exception as e:
            _failed_imports.append(
                (path.name, f"{type(e).__name__}: {e}"))
            continue

        query_name = getattr(mod, "QUERY_NAME", None)
        run_fn = getattr(mod, "run", None)

        if not isinstance(query_name, str) or not query_name:
            _failed_imports.append(
                (path.name, "missing or empty QUERY_NAME"))
            continue

        if not callable(run_fn):
            _failed_imports.append(
                (path.name, "missing or non-callable run()"))
            continue

        _registry[query_name] = run_fn
