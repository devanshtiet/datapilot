"""
app/tools/tool_registry.py
===========================
Central registry for all DataPilot tool functions.

Every callable that crosses a tool boundary (i.e. can be invoked by the
LangGraph planner in Mission 2) must be:
  1. Registered here with @register_tool(name).
  2. Wrapped automatically in try/except with structured logging.
  3. Validated: inputs come in as dicts and are parsed into the declared
     Pydantic input model; output must be a Pydantic model or list thereof.

In Mission 1 the registry is populated but not used by a planner — the
Streamlit app calls the functions directly. Mission 2 will wire the planner
to this registry.

Usage
-----
  from app.tools.tool_registry import TOOL_REGISTRY

  result = TOOL_REGISTRY["detect_iqr"](df=df, dataset_version=dv)
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry store
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def register_tool(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that:
    - Registers the function in TOOL_REGISTRY under `name`.
    - Wraps it in try/except so failures are logged and re-raised
      as RuntimeError (never silently swallowed).
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("Tool '%s' called with args=%s kwargs=%s", name, args, kwargs)
            try:
                result = fn(*args, **kwargs)
                logger.debug("Tool '%s' succeeded", name)
                return result
            except Exception as exc:
                logger.exception("Tool '%s' failed: %s", name, exc)
                raise RuntimeError(f"Tool '{name}' failed: {exc}") from exc

        if name in TOOL_REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered. Use a unique name.")

        TOOL_REGISTRY[name] = wrapper
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Register all tools by importing their modules
# (import side-effects populate TOOL_REGISTRY via @register_tool)
# ---------------------------------------------------------------------------

def _register_all() -> None:
    """
    Called once at startup to ensure all tools are registered.
    Import order does not matter — each module registers on import.
    """
    # Data tools
    from app.data import ingestion as _ing  # noqa: F401
    from app.data import quality as _qual   # noqa: F401

    # Analytics tools
    from app.analytics import statistics as _stats  # noqa: F401
    from app.analytics import correlations as _corr  # noqa: F401

    # Anomaly tools
    from app.anomaly import iqr as _iqr                            # noqa: F401
    from app.anomaly import zscore as _zs                          # noqa: F401
    from app.anomaly import isolation_forest as _iforest           # noqa: F401

    logger.info("Tool registry: %d tool(s) registered: %s", len(TOOL_REGISTRY), list(TOOL_REGISTRY))


# ---------------------------------------------------------------------------
# Apply @register_tool to each public function
# ---------------------------------------------------------------------------
# We do this here rather than in each module so the modules themselves
# stay importable without registering (e.g. in unit tests).

def _apply_registrations() -> None:
    from app.data.ingestion import load_file
    from app.data.quality import score_quality
    from app.analytics.statistics import compute_descriptive_stats
    from app.analytics.correlations import compute_correlation_matrix
    from app.anomaly.iqr import detect_iqr
    from app.anomaly.zscore import detect_zscore
    from app.anomaly.isolation_forest import detect_isolation_forest

    _tools = {
        "load_file": load_file,
        "score_quality": score_quality,
        "compute_descriptive_stats": compute_descriptive_stats,
        "compute_correlation_matrix": compute_correlation_matrix,
        "detect_iqr": detect_iqr,
        "detect_zscore": detect_zscore,
        "detect_isolation_forest": detect_isolation_forest,
    }

    for tool_name, fn in _tools.items():
        if tool_name not in TOOL_REGISTRY:
            @functools.wraps(fn)
            def _make_wrapper(f: Callable[..., Any], n: str) -> Callable[..., Any]:
                @functools.wraps(f)
                def _wrapper(*args: Any, **kwargs: Any) -> Any:
                    logger.debug("Tool '%s' called", n)
                    try:
                        return f(*args, **kwargs)
                    except Exception as exc:
                        logger.exception("Tool '%s' failed: %s", n, exc)
                        raise RuntimeError(f"Tool '{n}' failed: {exc}") from exc
                return _wrapper

            TOOL_REGISTRY[tool_name] = _make_wrapper(fn, tool_name)

    logger.info(
        "Tool registry ready: %d tool(s): %s",
        len(TOOL_REGISTRY),
        list(TOOL_REGISTRY),
    )


_apply_registrations()
