from agentverse.core.security import constant_time_key_match, redact, stable_tenant_key


def test_security_helpers() -> None:
    assert constant_time_key_match("same", "same")
    assert not constant_time_key_match("", "same")
    assert "super-secret" not in redact("api_key=super-secret")
    assert stable_tenant_key("a", "x") != stable_tenant_key("b", "x")
