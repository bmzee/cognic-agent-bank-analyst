"""The inert ``cognic.agents`` marker — AST-scan + import-probe pins.

A declarative agent pack ships NOTHING executable: the marker module's
whole job is to give the registry-discovery entry point a resolvable,
side-effect-free target. Three layers pin inertness: an exact-shape AST
scan of the module body (docstring + one ``typing`` import + one bare
``object()`` sentinel — nothing else, so no statement capable of I/O,
network, filesystem or global mutation can exist), a bare-import probe
asserting no environment/cwd mutation, and the installed entry-point
mapping resolving to the very same sentinel object.
"""

from __future__ import annotations

import ast
import importlib
import importlib.metadata
import os
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MARKER_PATH = _ROOT / "src" / "cognic_agent_bank_analyst" / "marker.py"
_INIT_PATH = _ROOT / "src" / "cognic_agent_bank_analyst" / "__init__.py"
_ENTRY_POINT_VALUE = "cognic_agent_bank_analyst.marker:AGENT_MARKER"


def test_marker_module_body_is_exactly_the_inert_shape() -> None:
    """Exact-shape pin: docstring, `from typing import Final`, and the
    bare `AGENT_MARKER: Final = object()` sentinel — and NOTHING else. Any
    added statement (a call, an import, an assignment) fails here before
    it could ever run at import time."""
    tree = ast.parse(_MARKER_PATH.read_text(encoding="utf-8"))
    body = tree.body
    assert len(body) == 3, "marker.py must contain ONLY docstring + import + sentinel"
    docstring, import_node, assign = body
    assert isinstance(docstring, ast.Expr)
    assert isinstance(docstring.value, ast.Constant)
    assert isinstance(docstring.value.value, str)
    assert isinstance(import_node, ast.ImportFrom)
    assert import_node.module == "typing"
    assert [alias.name for alias in import_node.names] == ["Final"]
    assert isinstance(assign, ast.AnnAssign)
    assert isinstance(assign.target, ast.Name)
    assert assign.target.id == "AGENT_MARKER"
    call = assign.value
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Name)
    assert call.func.id == "object"
    assert call.args == [] and call.keywords == []


def test_marker_module_has_no_io_capable_imports() -> None:
    """`typing` is the whole import allow-list — nothing reachable from
    the module body can open files, sockets, or subprocesses."""
    tree = ast.parse(_MARKER_PATH.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert imported == ["typing"]


def test_marker_bare_import_is_inert() -> None:
    """The import probe: a bare import succeeds and mutates neither the
    process environment nor the working directory."""
    env_before = dict(os.environ)
    cwd_before = os.getcwd()
    module = importlib.import_module("cognic_agent_bank_analyst.marker")
    assert dict(os.environ) == env_before
    assert os.getcwd() == cwd_before
    assert hasattr(module, "AGENT_MARKER")


def test_marker_is_a_bare_object_sentinel() -> None:
    from cognic_agent_bank_analyst.marker import AGENT_MARKER

    assert type(AGENT_MARKER) is object


def test_entry_point_mapping_resolves_to_the_same_sentinel() -> None:
    """The installed distribution's cognic.agents entry point (the plugin
    registry's discovery surface) names THIS marker object — pyproject ↔
    installed-metadata ↔ module identity all agree."""
    matches = [
        ep
        for ep in importlib.metadata.entry_points(group="cognic.agents")
        if ep.name == "bank-analyst" and ep.value == _ENTRY_POINT_VALUE
    ]
    assert len(matches) == 1
    from cognic_agent_bank_analyst.marker import AGENT_MARKER

    assert matches[0].load() is AGENT_MARKER


def test_package_init_is_inert_too() -> None:
    """The package __init__ carries only its docstring + an empty __all__
    — the marker's importable home performs no work either."""
    tree = ast.parse(_INIT_PATH.read_text(encoding="utf-8"))
    body = tree.body
    assert len(body) == 2, "__init__.py must contain ONLY docstring + __all__"
    docstring, assign = body
    assert isinstance(docstring, ast.Expr)
    assert isinstance(docstring.value, ast.Constant)
    assert isinstance(assign, ast.AnnAssign)
    assert isinstance(assign.target, ast.Name)
    assert assign.target.id == "__all__"
