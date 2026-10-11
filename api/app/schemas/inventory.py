from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.inventory import ChannelCategory, GeoType


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    category: ChannelCategory
    publisher: str | None
    reach_households: int
    base_cpm_micros: int
    is_premium: bool
    logo_url: str | None


class ChannelsResponse(BaseModel):
    items: list[ChannelOut]
    count: int
    total_count: int
    all_apps_reach_households: int  # "All Apps & Channels" aggregate reach


class InterestSegmentNode(BaseModel):
    id: uuid.UUID
    name: str
    reach_households: int
    children: list["InterestSegmentNode"] = []


InterestSegmentNode.model_rebuild()


class GeoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: GeoType
    code: str
    name: str
    households: int


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    domain: str
    name: str
    industry: str
    size_bucket: str
