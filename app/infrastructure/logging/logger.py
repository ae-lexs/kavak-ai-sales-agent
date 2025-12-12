"""Structured logger for observability."""

import logging
from typing import Any, Optional

# Configure root logger with JSON-like structured format
_logger = logging.getLogger("kavak_ai_sales_agent")
_logger.setLevel(logging.INFO)

# Create console handler if not exists
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)


def log_turn(
    session_id: str,
    turn_id: str,
    component: str,
    level: int = logging.INFO,
    **kwargs: Any,
) -> None:
    """
    Log structured event for a chat turn.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier (UUID string)
        component: Component name (e.g., 'http', 'use_case', 'rag')
        level: Log level (default: INFO)
        **kwargs: Additional structured fields to log
    """
    # Build structured log message
    fields = {
        "session_id": session_id,
        "turn_id": turn_id,
        "component": component,
    }
    fields.update(kwargs)

    # Format as key=value pairs for readability
    log_parts = [f"{k}={v!r}" for k, v in fields.items()]
    log_message = " | ".join(log_parts)

    _logger.log(level, log_message)


def log_intent_detected(
    session_id: str,
    turn_id: str,
    intent: str,
    **kwargs: Any,
) -> None:
    """
    Log intent detection event.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier
        intent: Detected intent (e.g., 'faq', 'commercial_flow')
        **kwargs: Additional fields
    """
    log_turn(
        session_id=session_id,
        turn_id=turn_id,
        component="intent_detection",
        intent_detected=intent,
        **kwargs,
    )


def log_flow_step(
    session_id: str,
    turn_id: str,
    step_before: Optional[str] = None,
    step_after: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Log flow step transition.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier
        step_before: Previous step
        step_after: New step
        **kwargs: Additional fields
    """
    fields = {}
    if step_before is not None:
        fields["flow_step_before"] = step_before
    if step_after is not None:
        fields["flow_step_after"] = step_after
    fields.update(kwargs)

    log_turn(
        session_id=session_id,
        turn_id=turn_id,
        component="flow",
        **fields,
    )


def log_rag_retrieval(
    session_id: str,
    turn_id: str,
    top_score: float,
    chunks_count: int,
    **kwargs: Any,
) -> None:
    """
    Log RAG retrieval event.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier
        top_score: Top chunk relevance score
        chunks_count: Number of retrieved chunks
        **kwargs: Additional fields
    """
    log_turn(
        session_id=session_id,
        turn_id=turn_id,
        component="rag",
        rag_retrieval_top_score=top_score,
        rag_chunks_count=chunks_count,
        **kwargs,
    )


def log_catalog_search(
    session_id: str,
    turn_id: str,
    filters: dict[str, Any],
    results_count: int,
    **kwargs: Any,
) -> None:
    """
    Log catalog search event.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier
        filters: Search filters applied
        results_count: Number of results
        **kwargs: Additional fields
    """
    log_turn(
        session_id=session_id,
        turn_id=turn_id,
        component="catalog",
        catalog_filters=filters,
        catalog_results_count=results_count,
        **kwargs,
    )


def log_financing_calculation(
    session_id: str,
    turn_id: str,
    car_price: float,
    down_payment: str,
    loan_term: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """
    Log financing calculation event.

    Args:
        session_id: Session identifier
        turn_id: Turn identifier
        car_price: Car price
        down_payment: Down payment amount or percentage
        loan_term: Loan term in months
        **kwargs: Additional fields
    """
    fields = {
        "financing_inputs": {
            "car_price": car_price,
            "down_payment": down_payment,
        },
    }
    if loan_term is not None:
        fields["financing_inputs"]["loan_term"] = loan_term
    fields.update(kwargs)

    log_turn(
        session_id=session_id,
        turn_id=turn_id,
        component="financing",
        **fields,
    )


# Export logger instance for backward compatibility
logger = _logger
