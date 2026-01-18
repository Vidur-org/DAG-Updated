def confidence_score(text: str) -> float:
    return min(len(text) / 1000, 1.0)
