import pytest
from app.core.compliance import RobotsChecker, DomainRateLimiter


def setup_function():
    RobotsChecker.reset()
    DomainRateLimiter.reset()


def test_robots_checker_disallow_rules():
    domain = "example.com"
    robots_content = """
User-agent: *
Disallow: /admin
Disallow: /private/
Allow: /public
"""
    RobotsChecker.parse_robots_content(domain, robots_content)

    assert not RobotsChecker.is_allowed("https://example.com/admin")
    assert not RobotsChecker.is_allowed("https://example.com/private/data")
    assert RobotsChecker.is_allowed("https://example.com/public/page")


@pytest.mark.asyncio
async def test_domain_rate_limiter():
    url = "https://example.com/api/test"
    import time
    start = time.time()
    await DomainRateLimiter.enforce_rate_limit(url, min_delay_ms=100)
    await DomainRateLimiter.enforce_rate_limit(url, min_delay_ms=100)
    elapsed = (time.time() - start) * 1000.0

    assert elapsed >= 90.0


def test_robots_checker_check_disallowed_warning():
    domain = "disallowed-site.com"
    robots_content = """
User-agent: *
Disallow: /
"""
    RobotsChecker.parse_robots_content(domain, robots_content)

    warning = RobotsChecker.check_disallowed_warning("https://disallowed-site.com/api/v1")
    assert warning is not None
    assert warning["disallowed"] is True
    assert warning["domain"] == "disallowed-site.com"

    warning_allowed = RobotsChecker.check_disallowed_warning("https://allowed-site.com/api/v1")
    assert warning_allowed is None


def test_cli_force_and_rate_limit_options():
    from typer.testing import CliRunner
    from app.cli.main import app

    runner = CliRunner()
    domain = "blocked-target.org"
    robots_content = """
User-agent: *
Disallow: /
"""
    RobotsChecker.parse_robots_content(domain, robots_content)

    # Without --force (interactive confirm defaults to False in test runner)
    res_noforce = runner.invoke(app, ["crawl", "https://blocked-target.org", "--max-pages", "1"])
    assert res_noforce.exit_code != 0
    assert "COMPLIANCE WARNING" in res_noforce.output

    # With --force
    res_force = runner.invoke(app, ["crawl", "https://blocked-target.org", "--max-pages", "1", "--force", "--format", "none"])
    assert "COMPLIANCE WARNING" in res_force.output or "InsightAPI AI Agent" in res_force.output

