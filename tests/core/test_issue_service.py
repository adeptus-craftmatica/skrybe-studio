from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from skrybe_studio.core.issues.contracts import Issue, IssueSeverity
from skrybe_studio.core.issues.service import IssueService


def _issue(rule_id: str = "missing_required_field") -> Issue:
    return Issue(
        id=uuid4(),
        severity=IssueSeverity.WARNING,
        rule_id=rule_id,
        plugin_owner="story_bible",
        entity_ids=(uuid4(),),
        title="Missing required field",
        description="The 'Name' field is required but empty.",
        created_at=datetime.now(UTC),
    )


class _Provider:
    def __init__(self, issues: list[Issue]) -> None:
        self._issues = issues

    def check(self) -> list[Issue]:
        return self._issues


class _RaisingProvider:
    def check(self) -> list[Issue]:
        raise RuntimeError("simulated failure")


def test_run_checks_aggregates_every_provider() -> None:
    service = IssueService()
    service.register_provider(_Provider([_issue("rule_a")]))
    service.register_provider(_Provider([_issue("rule_b")]))

    issues = service.run_checks()

    assert {issue.rule_id for issue in issues} == {"rule_a", "rule_b"}


def test_no_providers_returns_an_empty_list() -> None:
    service = IssueService()

    assert service.run_checks() == []


def test_a_raising_provider_is_isolated() -> None:
    service = IssueService()
    service.register_provider(_RaisingProvider())
    service.register_provider(_Provider([_issue()]))

    issues = service.run_checks()

    assert len(issues) == 1


def test_unregister_provider_stops_it_from_contributing() -> None:
    service = IssueService()
    provider = _Provider([_issue()])
    service.register_provider(provider)

    service.unregister_provider(provider)

    assert service.run_checks() == []


def test_issue_defaults_are_not_dismissed_or_resolved() -> None:
    issue = _issue()

    assert issue.dismissed is False
    assert issue.resolved is False
    assert issue.suggested_resolution is None
