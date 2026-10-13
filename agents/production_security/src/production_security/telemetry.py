from __future__ import annotations

from opentelemetry import metrics

_meter = metrics.get_meter("agentverse.security")
actions = _meter.create_counter("agentverse.security.actions")
denials = _meter.create_counter("agentverse.security.denials")
approval_attempts = _meter.create_counter("agentverse.security.approval_attempts")
retrieval_abstentions = _meter.create_counter("agentverse.security.retrieval_abstentions")
memory_rejections = _meter.create_counter("agentverse.security.memory_rejections")
tool_latency_ms = _meter.create_histogram("agentverse.security.tool_latency_ms", unit="ms")
