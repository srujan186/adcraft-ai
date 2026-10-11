"""M4: estimator deliverability bands + share helpers (pure, no DB)."""
from app.models.campaign import CampaignGoal
from app.services.estimator import compute_estimate, daypart_share, device_share


def _deliv(eligible: int) -> str:
    # total_sample = NATIONAL so scale = 1 and eligible_sample == eligible_national
    return compute_estimate(
        eligible_sample=eligible, total_sample=120_000_000, placement_share=1.0,
        device_share_val=0.78, daypart_share_val=1.0, avg_cpm_micros=24_000_000,
        budget_daily_micros=50_000_000, goal=CampaignGoal.awareness,
    )["deliverability"]


def test_deliverability_bands():
    assert _deliv(1_000) == "insufficient"
    assert _deliv(4_000) == "limited"
    assert _deliv(10_000) == "good"
    assert _deliv(50_000) == "excellent"


def test_narrow_vs_broad_monotonic():
    narrow = compute_estimate(
        eligible_sample=2, total_sample=200_000, placement_share=1.0, device_share_val=0.78,
        daypart_share_val=1.0, avg_cpm_micros=24_000_000, budget_daily_micros=50_000_000,
        goal=CampaignGoal.traffic,
    )
    broad = compute_estimate(
        eligible_sample=180_000, total_sample=200_000, placement_share=1.0, device_share_val=0.78,
        daypart_share_val=1.0, avg_cpm_micros=24_000_000, budget_daily_micros=50_000_000,
        goal=CampaignGoal.traffic,
    )
    assert narrow["deliverability"] == "insufficient"
    assert broad["deliverability"] == "excellent"
    assert broad["audience_households"][1] > narrow["audience_households"][1]


def test_share_helpers():
    assert abs(device_share(["tv"]) - 0.78) < 1e-9
    assert device_share(["tv", "mobile"]) > device_share(["tv"])
    assert daypart_share({"preset": "any"}) == 1.0
    assert daypart_share(None) == 1.0
    assert daypart_share({"preset": "primetime"}) < 1.0
