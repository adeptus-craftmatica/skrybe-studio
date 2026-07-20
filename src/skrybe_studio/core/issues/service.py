"""Aggregates results from every registered `IssueProvider`.

Deliberately mirrors `core/search/service.py`'s `SearchService`: both ask a
list of plugin-registered providers for typed contributions and tolerate
any one of them raising, without knowing anything about what those
contributions mean.
"""

from __future__ import annotations

import logging

from skrybe_studio.core.issues.contracts import Issue, IssueProvider

logger = logging.getLogger(__name__)


class IssueService:
    def __init__(self) -> None:
        self._providers: list[IssueProvider] = []

    def register_provider(self, provider: IssueProvider) -> None:
        self._providers.append(provider)

    def unregister_provider(self, provider: IssueProvider) -> None:
        if provider in self._providers:
            self._providers.remove(provider)

    def run_checks(self) -> list[Issue]:
        issues: list[Issue] = []
        for provider in self._providers:
            try:
                issues.extend(provider.check())
            except Exception:
                logger.exception("Issue provider %r raised while checking", provider)
        return issues
