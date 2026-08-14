#!/usr/bin/env python3
"""Answer one question: is this exact version installable from PyPI right now.

It exists because nothing was asking. v0.2.0 was tagged on 2026-08-06, GitHub created no workflow
run for that push, and the release simply did not happen. Everything downstream stayed green
because nothing downstream looked at the registry, so `pip install bankfile` kept serving 0.1.1,
which returns an account number welded to the front of a counterparty name. Eight days.

A tag is a claim about what people can install. This turns that claim into a measurement.

    check_published.py bankfile 0.2.0            one shot, exit 1 when absent
    check_published.py bankfile 0.2.0 --wait 180 poll, for use straight after an upload
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# The JSON API is the same surface pip resolves against, so a version visible here is a version a
# reader can install. The per-version endpoint is used rather than info.version because
# info.version is the LATEST release: a yanked or out of order upload would make it answer the
# wrong question.
ENDPOINT = "https://pypi.org/pypi/{package}/{version}/json"

# PyPI serves this through a CDN, so a fresh upload can take a few seconds to become visible from
# a given edge. Polling exists for that window only, not to paper over a failed upload.
POLL_SECONDS = 5


def is_published(package: str, version: str) -> bool:
    url = ENDPOINT.format(package=package, version=version)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
    return bool(payload.get("info", {}).get("version") == version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("version", help="version to look for, without the leading v")
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="seconds to keep asking before giving up (default: ask once)",
    )
    args = parser.parse_args(argv)

    deadline = time.monotonic() + args.wait
    while True:
        if is_published(args.package, args.version):
            print(f"{args.package} {args.version} is on PyPI")
            return 0
        if time.monotonic() >= deadline:
            break
        time.sleep(POLL_SECONDS)

    print(
        f"{args.package} {args.version} is NOT on PyPI. "
        f"A tag that nobody can install is a tag that lies about what is released.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
