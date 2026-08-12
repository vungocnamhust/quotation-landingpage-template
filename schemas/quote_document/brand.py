"""Base and brand-facing schema primitives for quotation documents.

This module intentionally has no FastAPI, repository, or rendering imports so
it can be used by generation, persistence, and API layers without a cycle.
"""
from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


class QuoteBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class BrandContentPolicy(QuoteBaseModel):
    tone: str = ""
    vocabulary: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    legal_default: str = ""
    image_style: str = ""


class BrandProfile(QuoteBaseModel):
    brand_id: str
    display_name: str
    domain: str = ""
    logo: str = ""
    colors: Dict[str, str] = Field(default_factory=dict)
    fonts: Dict[str, str] = Field(default_factory=dict)
    content_policy: BrandContentPolicy = Field(default_factory=BrandContentPolicy)


class GenerationStatus(QuoteBaseModel):
    narrative: Literal["generated", "fallback", "manual"] = "fallback"
    assets: Literal["generated", "fallback", "manual"] = "fallback"
    warnings: List[str] = Field(default_factory=list)


class AssetSelectionResult(QuoteBaseModel):
    hero: str = ""
    destinations: Dict[str, List[str]] = Field(default_factory=dict)
    hotels: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    dividers: Dict[str, str] = Field(default_factory=dict)
