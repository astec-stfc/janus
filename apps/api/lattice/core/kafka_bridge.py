"""Async Kafka-to-EventBus bridge for the lattice API."""

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from core.bus import EventBus

logger = logging.getLogger(__name__)


class KafkaBridge:
    """A Kafka consumer that consumes messages and then publishes them onto an EventBus.
    """

    def __init__(
        self,
        bus: EventBus,
        topics: tuple[str, ...],
        bootstrap_servers: str,
        group_id: str,
    ) -> None:
        self._bus = bus
        self._topics = topics
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="kafka-bridge")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # cancelled successfully, continue.
                pass
            self._task = None

    async def _run(self) -> None:
        while True:
            consumer = AIOKafkaConsumer(
                *self._topics,
                bootstrap_servers=self._bootstrap_servers,
                group_id=self._group_id,
                auto_offset_reset="latest",
                enable_auto_commit=True,
            )
            try:
                await consumer.start()
                logger.info(
                    "Kafka bridge started for topics: %s",
                    ", ".join(self._topics),
                )
                async for msg in consumer:
                    data = json.loads(msg.value.decode("utf-8"))
                    self._bus.publish(msg.topic, data)
            except asyncio.CancelledError:
                await consumer.stop()
                raise
            except Exception as exc:
                logger.error(f"Kafka bridge error: {exc}")
                await consumer.stop()
                # if disconnect, sleep and then re-create consumer above to attempt a retry
                await asyncio.sleep(5)
            else:
                await consumer.stop()
