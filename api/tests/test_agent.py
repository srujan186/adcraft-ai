"""M11: Ask Agent suggested questions, config, and the help articles shown when it's unavailable.

Answer content and proposals are covered in test_agent_context.py (P0-2).
"""
import re
from pathlib import Path

from app.services.agent import HELP_ARTICLES, help_for
from tests.conftest import signup

HELP_TS = Path(__file__).resolve().parents[2] / "web" / "src" / "content" / "help.ts"


def test_suggested_questions_and_config(client):
    h = signup(client, "agent2@acme.io", "Acme")["headers"]
    qs = client.get("/api/v1/agent/suggested-questions?section=audience", headers=h).json()["questions"]
    assert len(qs) == 2 and "What audience should I target?" in qs
    assert client.get("/api/v1/agent/config", headers=h).json()["configured"] is False


def test_help_links_point_at_real_articles():
    src = HELP_TS.read_text(encoding="utf-8")
    web = dict(re.findall(r'slug: "([^"]+)", title: "([^"]+)"', src))
    assert web, "could not read help articles from web/src/content/help.ts"
    for slug, title in HELP_ARTICLES.items():
        assert web.get(slug) == title, f"{slug} missing or retitled in help.ts"


def test_help_picks_by_question():
    titles = [h["title"] for h in help_for("why is my pixel not tracking?", None)]
    assert titles[0] == "Set up your pixel"
    assert len(help_for("hello", None)) >= 1
