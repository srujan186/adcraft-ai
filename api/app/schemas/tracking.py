from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.tracking import AppStatus, InstallMethod, Mmp, PixelStatus, Platform


class PixelCreate(BaseModel):
    install_method: InstallMethod = InstallMethod.manual


class PixelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    advertiser_id: uuid.UUID
    public_key: str
    install_method: InstallMethod
    status: PixelStatus
    last_event_at: dt.datetime | None


class PixelCreated(PixelOut):
    snippet: str


class AppCreate(BaseModel):
    advertiser_id: uuid.UUID
    platform: Platform = Platform.ios
    store_url: str | None = None
    bundle_id: str | None = None
    mmp: Mmp = Mmp.appsflyer
    mmp_app_id: str | None = None


class AppOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    advertiser_id: uuid.UUID
    platform: Platform
    store_url: str | None
    bundle_id: str | None
    mmp: Mmp
    mmp_app_id: str | None
    status: AppStatus
    last_postback_at: dt.datetime | None
    postback_url: str | None = None
