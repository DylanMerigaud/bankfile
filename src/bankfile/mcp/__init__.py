"""The MCP server, kept in its own package and behind an optional dependency.

Nothing in `bankfile` imports this. Someone using the library inside their own pipeline has no
reason to pull a server framework, and the core has to stay installable in the old stacks a
bank format parser lives in.
"""

from __future__ import annotations

import sys

# The console script points HERE and not at `.server:main`, on purpose. `pip install bankfile`
# without the extra still puts `bankfile-mcp` on the PATH, and pointing the script straight at
# the server module made it die on `import mcp` with a raw ModuleNotFoundError traceback before
# any code of ours ran. Someone following the README got a Python stack trace on their first
# command. The import happens inside the function so we can answer instead.
MISSING = (
    "bankfile-mcp needs the optional MCP dependency, which is not installed.\n"
    '  pip install "bankfile[mcp]"\n'
    "or run it without installing anything:\n"
    '  uvx --from "bankfile[mcp]" bankfile-mcp --root .'
)


def main(argv: list[str] | None = None) -> int:
    try:
        from bankfile.mcp.server import main as run
    except ModuleNotFoundError as exc:  # pragma: no cover - needs an install without the extra
        if exc.name and exc.name.split(".")[0] == "mcp":
            print(MISSING, file=sys.stderr)
            return 2
        raise
    return run(argv)
