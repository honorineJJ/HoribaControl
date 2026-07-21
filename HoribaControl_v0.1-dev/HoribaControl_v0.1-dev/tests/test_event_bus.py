from horibacontrol.core.event_bus import EventBus
from horibacontrol.domain.events import Event


async def test_event_bus_calls_sync_and_async_handlers():
    bus = EventBus()
    received = []

    def sync_handler(event):
        received.append(("sync", event.payload))

    async def async_handler(event):
        received.append(("async", event.payload))

    bus.subscribe("test", sync_handler)
    bus.subscribe("test", async_handler)
    await bus.publish(Event("test", 42))

    assert ("sync", 42) in received
    assert ("async", 42) in received
