"""
Custom exceptions for the Finance Agent.
Kept centralized so services/routers raise/catch consistent error types.
"""


class FinanceAgentError(Exception):
    """Base exception for all Finance Agent errors."""


class ValidationError(FinanceAgentError):
    """Raised when input data fails validation."""


class RepositoryError(FinanceAgentError):
    """Raised when a data access operation fails."""


class ServiceExecutionError(FinanceAgentError):
    """Raised when a service fails to complete its use-case."""