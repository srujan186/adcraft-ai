"""Import every model module so Base.metadata is fully populated (alembic + tests)."""
from app.models.advertiser import Advertiser, Industry
from app.models.agent import AgentMessage, AgentProposal, AgentThread, ProposalStatus
from app.models.audience import Audience, AudienceMember, AudienceSource, AudienceStatus
from app.models.billing import (
    Coupon,
    CouponRedemption,
    HoldoutHousehold,
    Invoice,
    PaymentMethod,
    Transaction,
    TxnType,
)
from app.models.campaign import (
    BiddingMode,
    BudgetType,
    Campaign,
    CampaignGoal,
    CampaignStatus,
    Kpi,
    PlacementMode,
    Strategy,
    StrategyCreative,
    StrategyStatus,
)
from app.models.creative import Creative, CreativeSource, ReviewStatus
from app.models.delivery import SimClock
from app.models.identity import Account, ApiKey, Invitation, Membership, OAuthApp, Role, User
from app.models.intelligence import (
    Elasticity,
    Recommendation,
    RecommendationStatus,
    RecommendationSuppression,
    RecommendationType,
)
from app.models.measurement import Conversion, Impression, StatsDaily
from app.models.reporting import ReportDefinition
from app.models.studio import StudioJob, StudioJobStatus
from app.models.tracking import (
    App,
    AppStatus,
    Event,
    EventSource,
    EventType,
    InstallMethod,
    Mmp,
    Pixel,
    PixelEventType,
    PixelStatus,
    Platform,
)
from app.models.inventory import (
    Channel,
    ChannelCategory,
    Company,
    CompanyHousehold,
    Geo,
    GeoType,
    Household,
    InterestSegment,
)

__all__ = [
    "Account",
    "Advertiser",
    "ApiKey",
    "Channel",
    "ChannelCategory",
    "Company",
    "CompanyHousehold",
    "BiddingMode",
    "BudgetType",
    "Campaign",
    "CampaignGoal",
    "CampaignStatus",
    "Creative",
    "CreativeSource",
    "Kpi",
    "PlacementMode",
    "ReviewStatus",
    "SimClock",
    "Strategy",
    "StrategyCreative",
    "StrategyStatus",
    "Geo",
    "GeoType",
    "Household",
    "Industry",
    "InterestSegment",
    "Invitation",
    "Membership",
    "OAuthApp",
    "Role",
    "User",
]
