from __future__ import annotations

from typing import Any
from notification.domain.events import EventType, IntegrationEvent


class NotificationTemplateEngine:
    """Renders human-readable titles and message bodies from IntegrationEvent facts."""

    @staticmethod
    def render(event: IntegrationEvent) -> tuple[str, str]:
        p = event.payload or {}
        event_type = event.event_type

        # 1. Quote Request Events
        if event_type == EventType.QUOTE_REQUEST_CREATED:
            customer = p.get("customer_name") or p.get("title") or "A new customer"
            destination = p.get("destination") or "Vietnam"
            return (
                "New Travel Request Received",
                f"{customer} submitted a new inquiry for {destination}.",
            )

        if event_type == EventType.QUOTE_REQUEST_ASSIGNED:
            designer = p.get("designer_name") or "You have"
            title = p.get("request_title") or f"Request #{event.aggregate_id}"
            return (
                "Request Assigned",
                f"{title} has been assigned to {designer}.",
            )

        if event_type == EventType.QUOTE_REQUEST_EDITED:
            title = p.get("request_title") or f"Request #{event.aggregate_id}"
            return (
                "Request Updated",
                f"Changes were made to inquiry '{title}'.",
            )

        if event_type == EventType.QUOTE_REQUEST_CONVERTED:
            title = p.get("request_title") or f"Request #{event.aggregate_id}"
            quotation_id = p.get("quotation_id") or "new quotation"
            return (
                "Request Converted to Quotation",
                f"Inquiry '{title}' was successfully converted into quotation {quotation_id}.",
            )

        # 2. Quotation Lifecycle Events
        if event_type == EventType.QUOTATION_CREATED:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            return (
                "Quotation Created",
                f"New quotation '{title}' has been drafted.",
            )

        if event_type == EventType.QUOTATION_UPDATED:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            return (
                "Quotation Updated",
                f"Quotation '{title}' details have been saved.",
            )

        if event_type == EventType.QUOTATION_PUBLICATION_QUEUED:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            return (
                "Publication Started",
                f"Publishing process for '{title}' is currently running.",
            )

        if event_type == EventType.QUOTATION_PUBLICATION_COMPLETED:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            return (
                "Quotation Published Successfully",
                f"Landing page for '{title}' is now live.",
            )

        if event_type == EventType.QUOTATION_PUBLICATION_FAILED:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            err = p.get("error") or "Unknown publication error."
            return (
                "Publication Failed",
                f"Failed to publish '{title}': {err}",
            )

        if event_type == EventType.QUOTATION_PDF_READY:
            title = p.get("title") or f"Quotation #{event.aggregate_id}"
            return (
                "PDF Export Ready",
                f"High-resolution PDF brochure for '{title}' has been generated.",
            )

        # 3. AI & Content Draft Events
        if event_type == EventType.AI_DRAFT_COMPLETED:
            scope = p.get("scope") or "itinerary"
            return (
                "AI Content Generated",
                f"AI storytelling draft for {scope} is ready for review.",
            )

        if event_type == EventType.AI_DRAFT_FAILED:
            scope = p.get("scope") or "itinerary"
            return (
                "AI Generation Issue",
                f"Could not complete AI storytelling generation for {scope}.",
            )

        # 4. DMC Agentic AI Events
        if event_type == EventType.AGENTIC_PLANNING_COMPLETED:
            run_title = p.get("run_title") or f"Agentic Plan #{event.aggregate_id}"
            return (
                "Agentic Optimization Complete",
                f"Autonomous agent finished itinerary & cost calculations for {run_title}.",
            )

        if event_type == EventType.AGENTIC_COST_OPTIMIZATION_ALERT:
            margin = p.get("margin_delta") or "pricing variance"
            return (
                "Cost Optimization Notice",
                f"Agent detected pricing improvement: {margin}.",
            )

        if event_type == EventType.AGENTIC_SUPPLIER_QUOTE_RECEIVED:
            supplier = p.get("supplier_name") or "A partner hotel/transport"
            return (
                "Supplier Rate Updated",
                f"Received updated contract rate from {supplier}.",
            )

        # 5. Default Fallback
        title = p.get("title") or f"Notification for {event.aggregate_type or 'workspace'}"
        body = p.get("message") or p.get("body") or f"Event {event_type} occurred."
        return (title, body)
