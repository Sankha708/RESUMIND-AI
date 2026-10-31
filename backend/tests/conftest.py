import pytest

from app.middleware.security import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits_between_tests():
    limiter.clear()
    yield
    limiter.clear()
