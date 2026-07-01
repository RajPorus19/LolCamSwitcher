"""Tests for remote event hub."""

import time

import pytest

from lol_auto_director.lol.events import EventType
from lol_auto_director.server.hub import RemoteEventHub


def test_ingest_and_poll():
    hub = RemoteEventHub()
    hub.ingest_heartbeat("A", 100.0, "PlayerA")
    event = hub.ingest_event("A", "kill", 120.0, "PlayerA")
    assert event.type == EventType.KILL
    assert hub.is_available()
    polled = hub.poll_events()
    assert len(polled) == 1
    assert hub.poll_events() == []


def test_heartbeat_timeout():
    hub = RemoteEventHub()
    hub.ingest_heartbeat("B", 50.0)
    assert hub.is_available()
    hub._last_heartbeat["B"] = time.monotonic() - 60  # noqa: SLF001
    assert not hub.is_available()
