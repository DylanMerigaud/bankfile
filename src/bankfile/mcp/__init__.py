"""The MCP server, kept in its own package and behind an optional dependency.

Nothing in `bankfile` imports this. Someone using the library inside their own pipeline has no
reason to pull a server framework, and the core has to stay installable in the old stacks a
bank format parser lives in.
"""
