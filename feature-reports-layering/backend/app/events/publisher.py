"""Domain-event publisher.

Local/dev has no message bus, so events are emitted to the structured logger.
Swapping in a real transport (e.g. a queue client) is a matter of replacing the
body of `publish_event` — the call sites and payloads stay the same.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

from app.events.models import DomainEvent

logger = logging.getLogger("reports.events")


def publish_event(event_name: str, payload: dict[str, Any]) -> DomainEvent:
    event = DomainEvent(name=event_name, payload=payload)
    logger.info(
        "domain_event",
        extra={
            "event": "domain_event",
            "event_name": event_name,
            "correlation_id": uuid.uuid4().hex,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    )
    return event
