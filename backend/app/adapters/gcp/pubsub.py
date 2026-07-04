"""
GCP Pub/Sub Event Publisher & Subscriber — Stage 1 implementation.
"""

from __future__ import annotations

import asyncio
import json
from functools import partial
from typing import Any, AsyncIterator

import structlog
from google.cloud import pubsub_v1

from app.adapters.base import EventPublisher, EventSubscriber
from app.adapters.exceptions import EventPublisherError, EventSubscriberError

logger = structlog.get_logger(__name__)


class GCPEventPublisher(EventPublisher):
    """
    Google Cloud Pub/Sub implementation of EventPublisher.

    Args:
        project_id: GCP project ID.
    """

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._publisher: pubsub_v1.PublisherClient | None = None

    def _get_publisher(self) -> pubsub_v1.PublisherClient:
        if self._publisher is None:
            self._publisher = pubsub_v1.PublisherClient()
        return self._publisher

    def _topic_path(self, topic: str) -> str:
        """Resolve logical topic name to full Pub/Sub topic path."""
        return self._get_publisher().topic_path(self._project_id, topic)

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        attributes: dict[str, str] | None = None,
    ) -> str:
        topic_path = self._topic_path(topic)
        data = json.dumps(payload).encode("utf-8")
        attrs = attributes or {}

        def _publish() -> str:
            future = self._get_publisher().publish(topic_path, data=data, **attrs)
            message_id: str = future.result(timeout=30)
            logger.debug("pubsub_published", topic=topic, message_id=message_id)
            return message_id

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _publish)
        except Exception as exc:
            raise EventPublisherError(
                f"Failed to publish to topic {topic!r}: {exc}", cause=exc
            ) from exc


class GCPEventSubscriber(EventSubscriber):
    """
    Google Cloud Pub/Sub pull-based EventSubscriber.

    Args:
        project_id: GCP project ID.
    """

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._subscriber: pubsub_v1.SubscriberClient | None = None

    def _get_subscriber(self) -> pubsub_v1.SubscriberClient:
        if self._subscriber is None:
            self._subscriber = pubsub_v1.SubscriberClient()
        return self._subscriber

    def _subscription_path(self, subscription: str) -> str:
        return self._get_subscriber().subscription_path(self._project_id, subscription)

    async def subscribe(
        self,
        subscription: str,
        batch_size: int = 10,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        sub_path = self._subscription_path(subscription)

        def _pull() -> list[Any]:
            response = self._get_subscriber().pull(
                request={"subscription": sub_path, "max_messages": batch_size},
                timeout=30,
            )
            return list(response.received_messages)

        try:
            loop = asyncio.get_event_loop()
            messages = await loop.run_in_executor(None, _pull)
            for msg in messages:
                payload = json.loads(msg.message.data.decode("utf-8"))
                yield msg.ack_id, payload
        except Exception as exc:
            raise EventSubscriberError(
                f"Failed to pull from subscription {subscription!r}: {exc}", cause=exc
            ) from exc

    async def acknowledge(self, subscription: str, message_id: str) -> None:
        sub_path = self._subscription_path(subscription)

        def _ack() -> None:
            self._get_subscriber().acknowledge(
                request={"subscription": sub_path, "ack_ids": [message_id]}
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _ack)
        except Exception as exc:
            raise EventSubscriberError(
                f"Failed to acknowledge message {message_id!r}: {exc}", cause=exc
            ) from exc

    async def nack(self, subscription: str, message_id: str) -> None:
        sub_path = self._subscription_path(subscription)

        def _nack() -> None:
            self._get_subscriber().modify_ack_deadline(
                request={
                    "subscription": sub_path,
                    "ack_ids": [message_id],
                    "ack_deadline_seconds": 0,  # Immediately re-deliver
                }
            )

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _nack)
        except Exception as exc:
            raise EventSubscriberError(
                f"Failed to nack message {message_id!r}: {exc}", cause=exc
            ) from exc
