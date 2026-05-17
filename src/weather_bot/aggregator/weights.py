DEFAULT_WEIGHTS: dict[str, float] = {
    "open_meteo": 0.35,
    "openweathermap": 0.30,
    "weatherapi": 0.25,
    "accuweather": 0.10,
}


def normalize_weights(active_sources: list[str]) -> dict[str, float]:
    total = sum(DEFAULT_WEIGHTS[s] for s in active_sources if s in DEFAULT_WEIGHTS)
    if total == 0:
        equal = 1.0 / len(active_sources)
        return {s: equal for s in active_sources}
    return {s: DEFAULT_WEIGHTS.get(s, 0.0) / total for s in active_sources}
