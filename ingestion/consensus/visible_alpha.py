from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VisibleAlphaConfig:
    """Configuration for Visible Alpha API access."""

    base_url: str = "https://api.visiblealpha.com"
    api_key: Optional[str] = None
    timeout_seconds: float = 30.0
    coverage_endpoint: str = "/consensus"
    identifier_preference: tuple[str, ...] = ("isin", "nse_symbol", "bse_code", "company_id")
    extra_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "VisibleAlphaConfig":
        return cls(
            base_url=os.getenv("VISIBLE_ALPHA_BASE_URL", cls.base_url),
            api_key=os.getenv("VISIBLE_ALPHA_API_KEY") or os.getenv("VISIBLE_ALPHA_KEY"),
            timeout_seconds=float(os.getenv("VISIBLE_ALPHA_TIMEOUT_SECONDS", "30")),
            coverage_endpoint=os.getenv("VISIBLE_ALPHA_CONSENSUS_PATH", cls.coverage_endpoint),
        )


class VisibleAlphaClient:
    """Thin REST client for Visible Alpha consensus pulls.

    The API shape is intentionally configurable because tenant-specific Visible Alpha
    deployments may expose slightly different consensus endpoints and filters.
    """

    def __init__(self, config: Optional[VisibleAlphaConfig] = None, session: Optional[requests.Session] = None):
        self.config = config or VisibleAlphaConfig.from_env()
        if not self.config.api_key:
            raise ValueError("VISIBLE_ALPHA_API_KEY is required")
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json",
                "User-Agent": "AgentOS-VisibleAlpha-Client/1.0",
                **self.config.extra_headers,
            }
        )

    def _request(self, method: str, path: str, *, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        response = self.session.request(method, url, params=params, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def company_identifier(self, company: Any) -> str:
        for field in self.config.identifier_preference:
            value = getattr(company, field, None)
            if value:
                return str(value)
        return str(company.id)

    def fetch_consensus(self, company: Any, *, as_of: Optional[date] = None) -> dict[str, Any]:
        """Fetch the current consensus snapshot for a single company.

        The caller is responsible for normalizing the returned payload into coverage.financials.
        """
        params: dict[str, Any] = {
            "company_id": str(getattr(company, "id")),
            "identifier": self.company_identifier(company),
        }
        if as_of is not None:
            params["as_of"] = as_of.isoformat()
        return self._request("GET", self.config.coverage_endpoint, params=params)

    @staticmethod
    def extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Best-effort normalization across plausible Visible Alpha response envelopes."""
        candidates: Iterable[Any] = (
            payload.get("consensus_rows"),
            payload.get("consensus"),
            payload.get("data"),
            payload.get("items"),
            payload.get("rows"),
            payload.get("results"),
        )
        for candidate in candidates:
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, dict)]
        if all(key in payload for key in ("metric", "value", "period_label")):
            return [payload]
        return []

    @staticmethod
    def parse_numeric(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            raise ValueError("numeric value is required")
        return Decimal(str(value))

    @staticmethod
    def parse_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if not value:
            return datetime.utcnow()
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

