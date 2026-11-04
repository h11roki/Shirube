from collections.abc import Mapping, Sequence

from app.application.ports import TokenUsage

YEN_PER_DOLLAR = 150
PRICES = {
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
}


def price_of(model: str) -> tuple[float, float, float] | None:
    return next((rates for name, rates in PRICES.items() if model.startswith(name)), None)


def yen(usage: Mapping[str, TokenUsage]) -> float:
    total = 0.0
    for model, tokens in usage.items():
        price = price_of(model)
        if price is None:
            continue
        fresh, cached, output = price
        total += (
            (tokens.input - tokens.cached) * fresh + tokens.cached * cached + tokens.output * output
        ) / 1_000_000
    return total * YEN_PER_DOLLAR


def unpriced(models: Sequence[str]) -> list[str]:
    return sorted(model for model in models if price_of(model) is None)
