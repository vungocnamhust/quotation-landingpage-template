from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    prompt={
        "id": "{replace here}",
        "version": "2",
    },
    input=[],
    text={
        "format": {
            "type": "json_schema",
            "name": "guide_search_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "block_id": {
                        "type": ["string", "null"],
                        "description": "Unique identifier for the search brief; set null if error and block_id is missing.",
                    },
                    "task": {
                        "type": "string",
                        "enum": ["guide_search"],
                        "description": "Task name, always 'guide_search'.",
                    },
                    "destination": {
                        "type": ["string", "null"],
                        "description": "Destination city/region; set null if error and destination is missing.",
                    },
                    "candidates": {
                        "type": "array",
                        "description": "Ranked candidate guides for the request.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {
                                    "type": "integer",
                                    "description": "Rank of the candidate, 1 is highest.",
                                },
                                "type": {
                                    "type": "string",
                                    "enum": ["freelance", "agency", "platform"],
                                    "description": "Guide type: freelance, agency, or platform.",
                                },
                                "language": {
                                    "type": "string",
                                    "description": "Guide's available language; always requested language if matched, else 'other'.",
                                },
                                "price_per_day_usd": {
                                    "type": ["number", "null"],
                                    "description": "Daily price in USD; null if unavailable.",
                                },
                                "total_days": {
                                    "type": "integer",
                                    "description": "Total duration in days from the brief.",
                                },
                                "total_estimate_usd": {
                                    "type": ["number", "null"],
                                    "description": "Total estimated price in USD; null if unavailable.",
                                },
                                "specialization": {
                                    "type": "string",
                                    "description": "Specialization: matches brief or best fit.",
                                },
                                "source_url": {
                                    "type": ["string", "null"],
                                    "description": "URL to source profile/page or null if not available.",
                                },
                                "retrieved_date": {
                                    "type": "string",
                                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                                    "description": "Date data was fetched (YYYY-MM-DD).",
                                },
                                "notes": {
                                    "type": ["string", "null"],
                                    "description": "License type, review score, surcharges, or key notes; null if not available.",
                                },
                            },
                            "required": [
                                "rank",
                                "type",
                                "language",
                                "price_per_day_usd",
                                "total_days",
                                "total_estimate_usd",
                                "specialization",
                                "source_url",
                                "retrieved_date",
                                "notes",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Machine-readable error code.",
                            },
                            "message": {
                                "type": "string",
                                "description": "Human-readable error message.",
                            },
                            "missing_fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Array of missing field names for invalid/incomplete brief format; omitted otherwise.",
                            },
                        },
                        "required": ["code", "message", "missing_fields"],
                        "additionalProperties": False,
                    },
                },
                "required": ["block_id", "task", "destination", "candidates", "error"],
                "additionalProperties": False,
                "$defs": {},
            },
        }
    },
    reasoning={},
    max_output_tokens=2048,
    store=True,
    include=["web_search_call.action.sources"],
)
