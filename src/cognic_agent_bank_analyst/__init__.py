"""cognic-agent-bank-analyst — declarative governed agent pack (M8, ADR-027).

This package intentionally contains NO agent code: the pack is a hosted
AGENT.md persona + a signed manifest; the AgentOS kernel owns the reasoning
loop and every dispatch decision. The package directory exists solely so
the wheel can carry AGENT.md + cognic-pack-manifest.toml as package data
for the AgentOS hosting layer (deferred-load discipline — the kernel reads
package data without importing pack code) and so the inert ``cognic.agents``
marker in ``marker.py`` has an importable home for registry discovery.
"""

__all__: list[str] = []
