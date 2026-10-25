"""
Lightweight Pub/Sub Event Bus for Viewer V2.
"""

from __future__ import annotations
from collections import defaultdict
import logging
from typing import Any, Callable

logger = logging.getLogger("viewer.bus")


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, topic: str, callback: Callable[..., Any]) -> Callable[[], None]:
        self._listeners[topic].append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners[topic]:
                self._listeners[topic].remove(callback)

        return unsubscribe

    def publish(self, topic: str, **kwargs: Any) -> None:
        for callback in list(self._listeners[topic]):
            try:
                callback(**kwargs)
            except Exception as e:
                logger.exception("Error executing subscriber for topic '%s': %s", topic, e)


bus = EventBus()
