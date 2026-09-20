from solutions.production_ai_security.app.models import Evidence, Identity, ToolRequest
from solutions.production_ai_security.app.orchestrator import SecureAgent


def main() -> None:
    agent = SecureAgent(
        (
            Evidence(
                "security-1",
                "Agent actions stay in a reversible sandbox until policy permits commit.",
                "docs://security/consent",
                "demo",
                1.0,
                True,
            ),
        )
    )
    identity = Identity("alice", "demo", frozenset({"orders:read", "refunds:write"}))
    print(agent.answer(identity, "How do agent actions stay reversible?"))
    print(
        agent.propose_action(
            identity,
            ToolRequest(
                "com.agentverse.payments",
                "issue_refund_lt_100",
                {"order_id": "ord-100", "amount": 79},
                "demo-request-1",
            ),
        )
    )


if __name__ == "__main__":
    main()
