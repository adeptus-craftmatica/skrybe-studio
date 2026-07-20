from __future__ import annotations

from dataclasses import dataclass

from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.events.bus import EventBus


@dataclass(frozen=True, slots=True)
class _SampleEvent(Event):
    value: int


def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus()
    received: list[int] = []
    bus.subscribe(_SampleEvent, lambda event: received.append(event.value))

    bus.publish(_SampleEvent(value=42))

    assert received == [42]


def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    received: list[int] = []

    def handler(event: _SampleEvent) -> None:
        received.append(event.value)

    bus.subscribe(_SampleEvent, handler)
    bus.unsubscribe(_SampleEvent, handler)
    bus.publish(_SampleEvent(value=1))

    assert received == []


def test_subscriber_error_is_isolated_from_other_subscribers() -> None:
    bus = EventBus()
    received: list[int] = []

    def failing_handler(_event: _SampleEvent) -> None:
        raise RuntimeError("boom")

    def good_handler(event: _SampleEvent) -> None:
        received.append(event.value)

    bus.subscribe(_SampleEvent, failing_handler)
    bus.subscribe(_SampleEvent, good_handler)

    bus.publish(_SampleEvent(value=7))

    assert received == [7]


def test_publish_with_no_subscribers_does_not_raise() -> None:
    bus = EventBus()
    bus.publish(_SampleEvent(value=1))
