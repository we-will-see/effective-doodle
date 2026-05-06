"""Domain exceptions for AgentOS."""

from __future__ import annotations


class AgentOSError(Exception):
    """Base class for domain errors."""


class ExtractionError(AgentOSError):
    """Raised when extraction fails."""


class QueueConflictError(AgentOSError):
    """Raised when queue state conflicts with an expected transition."""


class PeriodValidationError(AgentOSError):
    """Raised when an Indian fiscal period label/date pair is invalid."""


class FingerprintError(AgentOSError):
    """Raised when fingerprint inputs are invalid."""

