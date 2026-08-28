#!/usr/bin/env python3
"""Answer one question: is this exact version installable from PyPI right now.

It exists because nothing was asking. v0.2.0 was tagged on 2026-08-06, GitHub created no workflow
run for that push, and the release simply did not happen. Everything downstream stayed green
because nothing downstream looked at the registry, so `pip install bankfile` kept serving 0.1.1,
which returns an account number welded to the front of a counterparty name. Eight days.

A tag is a claim about what people can install. This turns that claim into a measurement.

    check_published.py bankfile 0.2.0            one shot, exit 1 when absent
    check_published.py bankfile 0.2.0 --wait 180 poll, for use straight after an upload

Exit codes carry two different meanings on purpose: 1 means PyPI was reached and answered "no
such version", 2 means PyPI could not be reached at all. Collapsing those into one exit code is
exactly the bug that shipped on 2026-08-27: a mid-handshake connection reset while checking 0.1.1
(itself already on PyPI, confirmed separately) was read as "not published" and filed a
release-gap issue against a version nobody had a problem with. A network blip is not a verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# The JSON API is the same surface pip resolves against, so a version visible here is a version a
# reader can install. The per-version endpoint is used rather than info.version because
# info.version is the LATEST release: a yanked or out of order upload would make it answer the
# wrong question.
#
# Overridable through an environment variable so the test suite can point this at a local stand
# in server and exercise real retry and exit code behaviour over a real socket, rather than
# mocking urlopen and risking a test that passes against a fake shaped nothing like the real
# failure. Nothing sets this variable outside the test suite, so production always talks to PyPI.
ENDPOINT = os.environ.get(
    "BANKFILE_CHECK_PUBLISHED_ENDPOINT", "https://pypi.org/pypi/{package}/{version}/json"
)

# PyPI serves this through a CDN, so a fresh upload can take a few seconds to become visible from
# a given edge. Polling exists for that window only, not to paper over a failed upload.
POLL_SECONDS = 5

# A reset or a timed out handshake heals within a few seconds on a healthy registry: these
# retries are for that window, not for a registry that is actually down. The delay is
# overridable for the same reason ENDPOINT is: so the test suite can prove the retry actually
# happens without a real test run sitting through NETWORK_RETRIES * NETWORK_RETRY_SECONDS.
NETWORK_RETRIES = 3
NETWORK_RETRY_SECONDS = int(os.environ.get("BANKFILE_CHECK_PUBLISHED_RETRY_SECONDS", "5"))


class RegistryUnreachableError(RuntimeError):
    """PyPI could not be asked, as opposed to PyPI answering that the version is absent."""


def is_published(package: str, version: str) -> bool:
    """Return whether `version` is installable, or raise if the registry could not be reached.

    A 404 is PyPI answering the question: that version does not exist, return False. Anything
    else (a reset connection, a timed out handshake, a 5xx) is the network or the registry
    failing to answer at all, and is retried a few times before being raised distinctly, so the
    caller never confuses "I could not check" with "I checked and it is missing".
    """
    url = ENDPOINT.format(package=package, version=version)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310
    last_error: Exception | None = None
    for attempt in range(1, NETWORK_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                payload = json.load(response)
            return bool(payload.get("info", {}).get("version") == version)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return False
            last_error = error
        except urllib.error.URLError as error:
            last_error = error
        if attempt < NETWORK_RETRIES:
            time.sleep(NETWORK_RETRY_SECONDS)
    msg = f"could not reach PyPI to check {package} {version}: {last_error}"
    raise RegistryUnreachableError(msg) from last_error


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
    last_unreachable: RegistryUnreachableError | None = None
    while True:
        try:
            published = is_published(args.package, args.version)
        except RegistryUnreachableError as error:
            last_unreachable = error
            if time.monotonic() >= deadline:
                break
            time.sleep(POLL_SECONDS)
            continue

        if published:
            print(f"{args.package} {args.version} is on PyPI")
            return 0
        last_unreachable = None
        if time.monotonic() >= deadline:
            break
        time.sleep(POLL_SECONDS)

    if last_unreachable is not None:
        print(str(last_unreachable), file=sys.stderr)
        return 2

    print(
        f"{args.package} {args.version} is NOT on PyPI. "
        f"A tag that nobody can install is a tag that lies about what is released.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
