"""File for singletons for lattice API to stop circular import issues"""

from core.bus import EventBus

event_bus: EventBus = EventBus()
kafka_producer = None
