from app.rate_limit import RateLimiter
from app.webhooks import sign_payload


def test_sign_payload_is_deterministic():
    payload = b'{"a": 1}'
    secret = "segredo"
    assert sign_payload(payload, secret) == sign_payload(payload, secret)
    assert len(sign_payload(payload, secret)) == 64
    assert sign_payload(payload, "outro") != sign_payload(payload, secret)


def test_rate_limiter_blocks_excess():
    limiter = RateLimiter()
    key = "127.0.0.1:/login"
    for _ in range(3):
        assert limiter.allow(key, 3, 60) is True
    assert limiter.allow(key, 3, 60) is False