"""`bankfile <file> --json`.

JSON goes to stdout and warnings go to stderr. That split is not cosmetic: the output of this
command is meant to be piped into `jq`, and a warning printed on stdout would corrupt the
document it is warning about. The warnings are in the JSON as well, so nothing is lost by
redirecting stderr away.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bankfile import parse
from bankfile.detect import UnknownFormatError
from bankfile.serialize import to_json_dict

# The file could not be identified or could not be read at all. Distinct from 1, which stays
# available for a future "read it, but something was wrong" outcome.
EXIT_UNREADABLE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bankfile",
        description="Read a bank file (MT940 or OFX/QFX) and print one normalised schema.",
    )
    parser.add_argument("path", type=Path, help="the bank file to read")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print JSON. This is the only output today, the flag exists so the command reads "
        "the same once there are others.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indent, 0 for one line")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        statement = parse(args.path)
    except (UnknownFormatError, OSError) as exc:
        print(f"bankfile: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    document = to_json_dict(statement)
    print(json.dumps(document, indent=args.indent or None, ensure_ascii=False))

    for warning in statement.warnings:
        where = f" [{warning.field}]" if warning.field else ""
        print(f"bankfile: {warning.rule}{where}: {warning.message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
