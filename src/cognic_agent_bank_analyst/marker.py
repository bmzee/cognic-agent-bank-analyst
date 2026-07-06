"""The inert ``cognic.agents`` marker (M8, ADR-027).

A declarative agent pack ships NO executable agent surface: the AgentOS
kernel owns the reasoning loop and every dispatch decision; this pack only
declares WHO the agent is (the AGENT.md persona) and WHAT it requests (the
manifest ``[agent]`` block). This entry-point target exists solely so the
plugin registry can DISCOVER the installed distribution under the
``cognic.agents`` group — admission and hosting read the manifest +
AGENT.md as package data via ``Distribution.locate_file()`` and never load
this module (the ADR-002 gate-1 deferred-load discipline).

The module body is deliberately inert: one ``typing`` import, one bare
sentinel object. No I/O, no network, no filesystem access, no global
mutation — pinned by the pack's AST-scan + import-probe tests.
"""

from typing import Final

#: The inert marker the ``cognic.agents`` entry point names. A bare
#: ``object()`` sentinel: nothing to call, nothing to configure — its only
#: job is to give the entry point a resolvable, side-effect-free target.
AGENT_MARKER: Final = object()
