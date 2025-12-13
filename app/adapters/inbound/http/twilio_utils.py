"""Twilio utility functions for webhook handling."""

import hashlib
import hmac
from urllib.parse import urlencode

from fastapi import HTTPException, Request, status

from app.infrastructure.config.settings import settings


def validate_twilio_signature(request: Request, url: str, form_data: dict[str, str]) -> bool:
    """
    Validate Twilio webhook signature.

    Args:
        request: FastAPI request object
        url: Full URL of the webhook endpoint
        form_data: Form data dictionary from the request

    Returns:
        True if signature is valid, False otherwise

    Raises:
        HTTPException: 403 if validation is enabled and signature is invalid
    """
    if not settings.twilio_validate_signature:
        return True

    if not settings.twilio_auth_token:
        # If validation is enabled but no token, fail
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twilio signature validation enabled but TWILIO_AUTH_TOKEN not configured",
        )

    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Twilio-Signature header",
        )

    # Build signature string
    # Twilio signs: URL + sorted form parameters
    sorted_params = sorted(form_data.items())
    param_string = urlencode(sorted_params)
    signature_string = url + param_string

    # Compute HMAC-SHA1
    computed_signature = hmac.new(
        settings.twilio_auth_token.encode("utf-8"),
        signature_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    # Base64 encode
    import base64

    computed_signature_b64 = base64.b64encode(computed_signature).decode("utf-8")

    # Compare (constant-time comparison)
    return hmac.compare_digest(computed_signature_b64, signature)


def generate_twiml_response(message: str) -> str:
    """
    Generate TwiML XML response for WhatsApp message.

    Args:
        message: Message text to send (in Spanish)

    Returns:
        TwiML XML string
    """
    # Escape XML special characters
    escaped_message = (
        message.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped_message}</Message></Response>'  # noqa: E501
