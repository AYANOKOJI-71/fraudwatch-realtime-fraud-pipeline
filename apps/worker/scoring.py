"""Explainable rule-based risk scoring; no claim of trained-model performance."""

from __future__ import annotations

from .models import DecisionAction, TransactionEvent


def evaluate(event: TransactionEvent, velocity_count: int) -> tuple[DecisionAction, int, list[str]]:
    score = 0
    rules: list[str] = []
    if event.amount_usd >= 1_000:
        score += 35
        rules.append("high_value_1000")
    elif event.amount_usd >= 500:
        score += 15
        rules.append("high_value_500")
    if event.new_device:
        score += 25
        rules.append("new_device")
    if event.country != event.home_country:
        score += 18
        rules.append("cross_border")
    if velocity_count >= 3:
        score += 40
        rules.append("velocity_5m")
    score = min(score, 100)
    if score >= 70:
        return DecisionAction.BLOCK, score, rules
    if score >= 40:
        return DecisionAction.REVIEW, score, rules
    return DecisionAction.ALLOW, score, rules
