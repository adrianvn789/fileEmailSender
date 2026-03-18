"""Shared fixtures for Canva API tests."""
import pytest


SAMPLE_PAGES_RESPONSE = {
    "items": [
        {"index": 1, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb1.png", "width": 160, "height": 90}},
        {"index": 2, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb2.png", "width": 160, "height": 90}},
        {"index": 3, "dimensions": {"width": 1920, "height": 1080}, "thumbnail": {"url": "https://example.com/thumb3.png", "width": 160, "height": 90}},
    ]
}

SAMPLE_TOKEN_RESPONSE = {
    "access_token": "fake_access_token_12345",
    "refresh_token": "fake_refresh_token_67890",
    "token_type": "Bearer",
    "expires_in": 14400,
    "scope": "design:meta:read design:content:read",
}


@pytest.fixture
def sample_pages_response():
    return SAMPLE_PAGES_RESPONSE


@pytest.fixture
def sample_token_response():
    return SAMPLE_TOKEN_RESPONSE
