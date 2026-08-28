"""check_published.py must tell "PyPI said no" apart from "PyPI could not be reached".

On 2026-08-27 it did not: a connection reset mid TLS handshake while checking bankfile 0.1.1 (a
version confirmed on PyPI separately, by a plain curl, at the time this test was written) was
read as "not published" and filed issue #4, a release-gap against a version nobody had a problem
with. The script had only one way to fail, `is_published` raising past an unhandled exception,
and the workflow had only one way to read that: add the tag to the missing list.

This exercises the fix against a real local HTTP server standing in for pypi.org, wired in
through BANKFILE_CHECK_PUBLISHED_ENDPOINT, rather than mocking urlopen: the failure that shipped
was in what happens across repeated real socket calls, and a mock shaped to the fix would not
have caught the bug the fix repairs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_published.py"


class _FakeRegistry:
    """Serves one status per call, repeating the last one once the list runs out."""

    def __init__(self, statuses: list[int]) -> None:
        self.statuses = statuses
        self.calls = 0
        self.server = HTTPServer(("127.0.0.1", 0), self._make_handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        registry = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                registry.calls += 1
                index = min(registry.calls, len(registry.statuses)) - 1
                status = registry.statuses[index]
                body = json.dumps({"info": {"version": "0.1.1"}}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if status < 300:
                    self.wfile.write(body)

            def log_message(self, format_: str, *args: object) -> None:  # noqa: ARG002
                return

        return Handler

    @property
    def endpoint(self) -> str:
        port = self.server.server_address[1]
        return f"http://127.0.0.1:{port}/{{package}}/{{version}}/json"

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join()


RegistryFactory = Callable[[list[int]], _FakeRegistry]


@pytest.fixture
def fake_registry() -> Iterator[RegistryFactory]:
    started: list[_FakeRegistry] = []

    def factory(statuses: list[int]) -> _FakeRegistry:
        registry = _FakeRegistry(statuses)
        started.append(registry)
        return registry

    yield factory
    for registry in started:
        registry.close()


def run(
    registry: _FakeRegistry, *extra_args: str, wait: int | None = None
) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(SCRIPT), "bankfile", "0.1.1", *extra_args]
    if wait is not None:
        args += ["--wait", str(wait)]
    env = dict(os.environ)
    env["BANKFILE_CHECK_PUBLISHED_ENDPOINT"] = registry.endpoint
    env["BANKFILE_CHECK_PUBLISHED_RETRY_SECONDS"] = "0"
    return subprocess.run(  # noqa: S603
        args, cwd=ROOT, capture_output=True, text=True, check=False, env=env
    )


def test_published_exits_zero(fake_registry: RegistryFactory) -> None:
    registry = fake_registry([200])
    result = run(registry)
    assert result.returncode == 0, result.stderr
    assert "is on PyPI" in result.stdout


def test_a_definitive_404_exits_one_without_retrying(
    fake_registry: RegistryFactory,
) -> None:
    """A 404 is PyPI answering the question, not the network failing. One call is enough."""
    registry = fake_registry([404])
    result = run(registry)
    assert result.returncode == 1
    assert "is NOT on PyPI" in result.stderr
    assert registry.calls == 1


def test_a_transient_failure_is_retried_into_a_pass(
    fake_registry: RegistryFactory,
) -> None:
    """The exact shape of the 2026-08-27 incident: the registry misbehaves once, then answers
    correctly. The old script crashed on the first call; the fix must reach the real answer."""
    registry = fake_registry([503, 503, 200])
    result = run(registry)
    assert result.returncode == 0, result.stderr
    assert "is on PyPI" in result.stdout
    assert registry.calls == 3


def test_a_registry_that_stays_down_exits_two_not_one(
    fake_registry: RegistryFactory,
) -> None:
    """Exit code 1 means "confirmed absent" and feeds a GitHub issue. A registry that never
    recovers must not be reported the same way as a 404, or every outage files a false
    release-gap the way issue #4 did."""
    registry = fake_registry([503])
    result = run(registry)
    assert result.returncode == 2
    assert "could not reach" in result.stderr
    assert registry.calls > 1, "a single 503 must be retried, not treated as final"
