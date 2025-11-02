"""Tests for retry policy module"""

import pytest
from app.transport.retry_policy import (
    RetryConfig,
    RetryStrategy,
    JitterType,
    RetryPolicy,
    create_retry_policy,
    DEFAULT_RETRY_CONFIG,
    AGGRESSIVE_RETRY_CONFIG,
    CONSERVATIVE_RETRY_CONFIG,
)


class DummyException(Exception):
    pass


@pytest.mark.parametrize(
    "strategy,expected",
    [
        (
            RetryStrategy.EXPONENTIAL,
            [0.0, 4.0, 8.0, 10.0],
        ),  # 2*2^1=4, 2*2^2=8, 2*2^3=16->10 (capped)
        (RetryStrategy.LINEAR, [0.0, 4.0, 6.0, 8.0]),  # 2+2*1=4, 2+2*2=6, 2+2*3=8
        (RetryStrategy.FIXED, [0.0, 2.0, 2.0, 2.0]),
    ],
)
def test_calculate_delay_strategies(strategy, expected):
    config = RetryConfig(
        max_attempts=4,
        base_delay=2.0,
        max_delay=10.0,
        backoff_multiplier=2.0,
        strategy=strategy,
        jitter_type=JitterType.NONE,
    )
    policy = RetryPolicy(config)
    delays = [policy.calculate_delay(i) for i in range(4)]
    assert delays == expected


@pytest.mark.parametrize(
    "jitter_type",
    [JitterType.NONE, JitterType.FULL, JitterType.EQUAL, JitterType.DECORRELATED],
)
def test_apply_jitter_types(jitter_type):
    config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        backoff_multiplier=2.0,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter_type=jitter_type,
        jitter_factor=0.5,
    )
    policy = RetryPolicy(config)
    # Just test that it runs and returns a float
    delay = policy._apply_jitter(5.0, 2)
    assert isinstance(delay, float)
    assert delay >= 0


@pytest.mark.asyncio
async def test_execute_with_retry_success():
    config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.1)
    policy = RetryPolicy(config)

    async def op():
        return "ok"

    result = await policy.execute_with_retry(op)
    assert result == "ok"
    stats = policy.get_retry_stats()
    assert stats["total_attempts"] == 0


@pytest.mark.asyncio
async def test_execute_with_retry_failure():
    config = RetryConfig(
        max_attempts=2,
        base_delay=0.01,
        max_delay=0.1,
        retryable_exceptions=[DummyException],
    )
    policy = RetryPolicy(config)

    async def op():
        raise DummyException("fail")

    with pytest.raises(DummyException):
        await policy.execute_with_retry(op)
    stats = policy.get_retry_stats()
    assert stats["total_attempts"] == 2
    assert "fail" in stats["last_exception"]


@pytest.mark.asyncio
async def test_execute_with_retry_custom_condition():
    def retry_condition(exc):
        return isinstance(exc, DummyException) and str(exc) == "retry"

    config = RetryConfig(
        max_attempts=3,
        base_delay=0.01,
        max_delay=0.1,
        retryable_exceptions=[DummyException],
        retry_condition=retry_condition,
    )
    policy = RetryPolicy(config)
    calls = []

    async def op():
        calls.append(1)
        if len(calls) < 2:
            raise DummyException("retry")
        return "done"

    result = await policy.execute_with_retry(op)
    assert result == "done"
    stats = policy.get_retry_stats()
    assert stats["total_attempts"] == 1


@pytest.mark.parametrize(
    "config_obj",
    [DEFAULT_RETRY_CONFIG, AGGRESSIVE_RETRY_CONFIG, CONSERVATIVE_RETRY_CONFIG],
)
def test_preconfigured_configs(config_obj):
    policy = create_retry_policy(config_obj)
    assert isinstance(policy, RetryPolicy)
    assert policy.config == config_obj


@pytest.mark.parametrize(
    "bad_field,bad_value,err_msg",
    [
        ("max_attempts", 0, "max_attempts must be at least 1"),
        ("base_delay", 0, "base_delay must be positive"),
        ("max_delay", 0.5, "max_delay must be >= base_delay"),
        (
            "backoff_multiplier",
            1,
            "backoff_multiplier must be > 1 for exponential strategy",
        ),
    ],
)
def test_retry_config_validation(bad_field, bad_value, err_msg):
    kwargs = dict(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        backoff_multiplier=2.0,
        strategy=RetryStrategy.EXPONENTIAL,
    )
    kwargs[bad_field] = bad_value
    with pytest.raises(ValueError, match=err_msg):
        RetryConfig(**kwargs)  # type: ignore
