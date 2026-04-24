"""Execution declarations for inline and background-capable workflows."""

from __future__ import annotations

import asyncio
import inspect
import re

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Iterator, Optional, Protocol, Union
from uuid import uuid4


class ExecutionMode(str, Enum):
    """Supported execution modes."""

    INLINE = "inline"
    BACKGROUND = "background"


class ExecutionCapability(str, Enum):
    """Declares whether a workflow is inline-only or can be deferred."""

    INLINE_ONLY = "inline-only"
    ASYNC_CAPABLE = "async-capable"


ExecutionModeLike = Union[ExecutionMode, str, None]


def normalize_execution_mode(mode: ExecutionModeLike) -> Optional[ExecutionMode]:
    """Normalize a caller-provided execution mode."""
    if mode is None:
        return None
    if isinstance(mode, ExecutionMode):
        return mode
    return ExecutionMode(mode)


@dataclass(frozen=True)
class ExecutionProfile:
    """Declares the supported execution modes for a workflow."""

    capability: ExecutionCapability = ExecutionCapability.INLINE_ONLY
    default_mode: ExecutionMode = ExecutionMode.INLINE
    background_hint: Optional[str] = None

    def __post_init__(self) -> None:
        if (
            self.default_mode == ExecutionMode.BACKGROUND
            and self.capability != ExecutionCapability.ASYNC_CAPABLE
        ):
            raise ValueError(
                "Background default_mode requires an async-capable execution profile."
            )

    @property
    def supported_modes(self) -> tuple[ExecutionMode, ...]:
        if self.capability == ExecutionCapability.ASYNC_CAPABLE:
            return (ExecutionMode.INLINE, ExecutionMode.BACKGROUND)
        return (ExecutionMode.INLINE,)

    @property
    def supports_background(self) -> bool:
        return self.capability == ExecutionCapability.ASYNC_CAPABLE

    def resolve_mode(self, mode: ExecutionModeLike = None) -> ExecutionMode:
        """Validate and resolve a requested execution mode."""
        resolved = normalize_execution_mode(mode) or self.default_mode
        if resolved not in self.supported_modes:
            raise ValueError(
                f"Execution mode '{resolved.value}' is not supported by the "
                f"'{self.capability.value}' execution profile."
            )
        return resolved

    def as_metadata(self) -> dict[str, object]:
        """Return JSON-safe metadata for reporting and inspection."""
        metadata: dict[str, object] = {
            "capability": self.capability.value,
            "default_mode": self.default_mode.value,
            "supported_modes": [mode.value for mode in self.supported_modes],
        }
        if self.background_hint:
            metadata["background_hint"] = self.background_hint
        return metadata

    @classmethod
    def inline_only(cls) -> "ExecutionProfile":
        return cls()

    @classmethod
    def async_capable(
        cls,
        *,
        default_mode: ExecutionMode = ExecutionMode.INLINE,
        background_hint: Optional[str] = None,
    ) -> "ExecutionProfile":
        return cls(
            capability=ExecutionCapability.ASYNC_CAPABLE,
            default_mode=default_mode,
            background_hint=background_hint,
        )


@dataclass(frozen=True)
class ExecutionPlan:
    """Resolved execution intent for a pipeline or gateway operation."""

    scope: str
    mode: ExecutionMode
    profile: ExecutionProfile

    def as_metadata(self) -> dict[str, object]:
        metadata = {"scope": self.scope, "mode": self.mode.value}
        metadata.update(self.profile.as_metadata())
        return metadata


class RuntimeScope(str, Enum):
    """Runtime activity and error scope."""

    REQUEST = "request"
    PIPELINE = "pipeline"
    INTEROP = "interop"
    STARTUP = "startup"
    INTERNAL = "internal"


class RuntimeStatus(str, Enum):
    """Lifecycle status for runtime events."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeErrorSurface:
    """Typed runtime error metadata for hooks and response mapping."""

    phase: RuntimeScope
    code: str
    message: str
    status_code: int = 500
    retryable: bool = False
    detail: Optional[Any] = None
    correlation_id: Optional[str] = None

    def as_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "phase": self.phase.value,
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "retryable": self.retryable,
        }
        if self.detail is not None:
            metadata["detail"] = self.detail
        if self.correlation_id:
            metadata["correlation_id"] = self.correlation_id
        return metadata


@dataclass(frozen=True)
class RuntimeEvent:
    """Structured runtime event delivered to pluggable hooks."""

    name: str
    activity: RuntimeScope
    status: RuntimeStatus
    scope: str
    correlation_id: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, object] = field(default_factory=dict)
    error: Optional[RuntimeErrorSurface] = None

    def as_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "name": self.name,
            "activity": self.activity.value,
            "status": self.status.value,
            "scope": self.scope,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
        if self.correlation_id:
            metadata["correlation_id"] = self.correlation_id
        if self.error is not None:
            metadata["error"] = self.error.as_metadata()
        return metadata


class RuntimeHook(Protocol):
    """Protocol for pluggable runtime sinks."""

    def emit(self, event: RuntimeEvent) -> Optional[Awaitable[None]]: ...


RuntimeHookLike = Union[
    RuntimeHook, Callable[[RuntimeEvent], Optional[Awaitable[None]]]
]


class RuntimeHooks:
    """Sync-friendly manager for pluggable runtime hooks."""

    def __init__(self, hooks: Optional[list[RuntimeHookLike]] = None):
        self._hooks: list[RuntimeHookLike] = list(hooks or [])

    def register(self, hook: RuntimeHookLike) -> RuntimeHookLike:
        self._hooks.append(hook)
        return hook

    def emit(self, event: RuntimeEvent) -> None:
        for hook in list(self._hooks):
            emit = getattr(hook, "emit", hook)
            result = emit(event)
            if inspect.isawaitable(result):
                _consume_awaitable(result)


_RUNTIME_CORRELATION_ID: ContextVar[Optional[str]] = ContextVar(
    "healthchain_runtime_correlation_id",
    default=None,
)
_RUNTIME_HOOKS: ContextVar[Optional[RuntimeHooks]] = ContextVar(
    "healthchain_runtime_hooks",
    default=None,
)


def generate_correlation_id() -> str:
    return str(uuid4())


def get_correlation_id() -> Optional[str]:
    return _RUNTIME_CORRELATION_ID.get()


def get_runtime_hooks() -> Optional[RuntimeHooks]:
    return _RUNTIME_HOOKS.get()


@contextmanager
def runtime_context(
    *,
    correlation_id: Optional[str] = None,
    hooks: Optional[RuntimeHooks] = None,
) -> Iterator[None]:
    correlation_token: Optional[Token[Optional[str]]] = None
    hooks_token: Optional[Token[Optional[RuntimeHooks]]] = None
    try:
        if correlation_id is not None:
            correlation_token = _RUNTIME_CORRELATION_ID.set(correlation_id)
        if hooks is not None:
            hooks_token = _RUNTIME_HOOKS.set(hooks)
        yield
    finally:
        if hooks_token is not None:
            _RUNTIME_HOOKS.reset(hooks_token)
        if correlation_token is not None:
            _RUNTIME_CORRELATION_ID.reset(correlation_token)


def record_runtime_event(
    *,
    name: str,
    activity: RuntimeScope,
    status: RuntimeStatus,
    scope: str,
    details: Optional[dict[str, object]] = None,
    error: Optional[RuntimeErrorSurface] = None,
    correlation_id: Optional[str] = None,
    hooks: Optional[RuntimeHooks] = None,
) -> Optional[RuntimeEvent]:
    resolved_hooks = hooks or get_runtime_hooks()
    if resolved_hooks is None:
        return None
    event = RuntimeEvent(
        name=name,
        activity=activity,
        status=status,
        scope=scope,
        correlation_id=correlation_id or get_correlation_id(),
        details=details or {},
        error=error,
    )
    resolved_hooks.emit(event)
    return event


def map_runtime_error(
    exc: Exception,
    *,
    phase: RuntimeScope = RuntimeScope.INTERNAL,
    correlation_id: Optional[str] = None,
) -> RuntimeErrorSurface:
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    resolved_correlation_id = correlation_id or get_correlation_id()
    if isinstance(exc, RequestValidationError):
        return RuntimeErrorSurface(
            phase=RuntimeScope.REQUEST,
            code="request.validation_error",
            message="Request validation failed",
            status_code=422,
            detail={"errors": exc.errors(), "body": exc.body},
            correlation_id=resolved_correlation_id,
        )
    if isinstance(exc, HTTPException):
        return RuntimeErrorSurface(
            phase=RuntimeScope.REQUEST,
            code=f"request.http_{exc.status_code}",
            message=str(exc.detail),
            status_code=exc.status_code,
            detail=exc.detail,
            correlation_id=resolved_correlation_id,
        )

    status_code = _coerce_status_code(getattr(exc, "state", None)) or 500
    upstream_code = getattr(exc, "code", exc.__class__.__name__)
    detail = {"exception_type": exc.__class__.__name__}
    if getattr(exc, "state", None) is not None:
        detail["upstream_state"] = str(exc.state)
    if getattr(exc, "code", None) is not None:
        detail["upstream_code"] = str(exc.code)

    return RuntimeErrorSurface(
        phase=phase,
        code=f"{phase.value}.{_slugify(upstream_code)}",
        message=getattr(exc, "message", str(exc)),
        status_code=status_code,
        retryable=status_code >= 500,
        detail=detail,
        correlation_id=resolved_correlation_id,
    )


def _consume_awaitable(result: Awaitable[None]) -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(result)
        finally:
            loop.close()
    else:
        asyncio.create_task(result)


def _coerce_status_code(value: object) -> Optional[int]:
    try:
        status_code = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return status_code if 100 <= status_code <= 599 else None


def _slugify(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return text or "error"
