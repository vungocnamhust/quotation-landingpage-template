from __future__ import annotations

from typing import Any
from notification.domain.events import EventType, IntegrationEvent, Severity
from notification.domain.models import Channel


class NotificationPolicy:
    """Core communication policy determining recipients, channels, severity, and action URLs."""

    @staticmethod
    def resolve_recipients(event: IntegrationEvent) -> list[dict[str, str | None]]:
        """Resolves target recipients from the event payload and metadata.

        Returns a list of dicts: [{"email": "...", "profile_id": "..."}].
        """
        payload = event.payload or {}
        recipients: list[dict[str, str | None]] = []

        # 1. Direct explicit recipient in payload
        if "recipient_email" in payload and payload["recipient_email"]:
            email = str(payload["recipient_email"]).strip().lower()
            profile_id = payload.get("recipient_profile_id")
            recipients.append({"email": email, "profile_id": profile_id})

        # 2. Targeted designer / creator in payload
        designer_email = payload.get("designer_email") or payload.get("travel_designer_email")
        if designer_email:
            email = str(designer_email).strip().lower()
            if not any(r["email"] == email for r in recipients):
                recipients.append({
                    "email": email,
                    "profile_id": payload.get("designer_profile_id") or payload.get("travel_designer_id"),
                })

        created_by_email = payload.get("created_by_email")
        if created_by_email:
            email = str(created_by_email).strip().lower()
            if not any(r["email"] == email for r in recipients):
                recipients.append({
                    "email": email,
                    "profile_id": payload.get("created_by_profile_id"),
                })

        # 3. Fallback to actor if no other recipient found
        if not recipients and event.actor_email:
            recipients.append({
                "email": event.actor_email.strip().lower(),
                "profile_id": payload.get("actor_profile_id"),
            })

        # 4. Broadcast / Default fallback
        if not recipients:
            recipients.append({"email": "all@workspace.internal", "profile_id": None})

        return recipients

    @staticmethod
    def resolve_severity(event: IntegrationEvent) -> Severity:
        payload = event.payload or {}
        if "severity" in payload:
            try:
                return Severity(payload["severity"])
            except ValueError:
                pass

        if event.event_type in (
            EventType.QUOTATION_PUBLICATION_FAILED,
            EventType.AI_DRAFT_FAILED,
        ):
            return Severity.ERROR

        if event.event_type in (
            EventType.QUOTATION_PUBLICATION_COMPLETED,
            EventType.QUOTATION_PDF_READY,
            EventType.AI_DRAFT_COMPLETED,
            EventType.QUOTE_REQUEST_CONVERTED,
            EventType.AGENTIC_SUPPLIER_QUOTE_RECEIVED,
        ):
            return Severity.SUCCESS

        if event.event_type in (
            EventType.AGENTIC_COST_OPTIMIZATION_ALERT,
        ):
            return Severity.WARNING

        return Severity.INFO

    @staticmethod
    def resolve_action_url(event: IntegrationEvent) -> str | None:
        payload = event.payload or {}
        if "action_url" in payload and payload["action_url"]:
            return str(payload["action_url"])

        # Construct projection reference URL
        if event.aggregate_type == "quotation":
            if event.event_type == EventType.QUOTATION_PDF_READY:
                return f"/workspace/quotations/{event.aggregate_id}?tab=pdf"
            return f"/workspace/quotations/{event.aggregate_id}"

        if event.aggregate_type == "quote_request":
            return f"/workspace/requests/{event.aggregate_id}"

        if event.aggregate_type == "agentic_run":
            return f"/workspace/agents/{event.aggregate_id}"

        return None

    @staticmethod
    def resolve_channels(event: IntegrationEvent) -> list[Channel]:
        """Resolves required delivery channels for an event."""
        # By default, all system events deliver to INAPP_SSE inbox
        channels = [Channel.INAPP_SSE]

        payload = event.payload or {}
        if payload.get("send_email", False):
            channels.append(Channel.EMAIL)

        return channels
