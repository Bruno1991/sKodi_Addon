import pytest

from corporate_security import CircuitBreaker, CorporateError


def test_breaker_opens_and_recovers_half_open() -> None:
    now = [0.0]
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0, clock=lambda: now[0])
    breaker.before_call(); breaker.on_failure()
    breaker.before_call(); breaker.on_failure()
    with pytest.raises(CorporateError) as captured:
        breaker.before_call()
    assert captured.value.code == "circuit_open"
    now[0] = 11.0
    breaker.before_call()
    breaker.on_success()
    breaker.before_call()
