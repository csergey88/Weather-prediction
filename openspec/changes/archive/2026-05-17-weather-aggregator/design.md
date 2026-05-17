## Context

Источники (Фаза 2) готовы. Модели `WeatherReading`, `ForecastPoint`, `AggregatedWeather` определены. Нужно склеить всё в агрегатор согласно SPEC.md §4.

## Goals / Non-Goals

**Goals:**
- Параллельный сбор из 4 источников с graceful degradation
- Взвешенное усреднение числовых полей и majority vote для условий
- Confidence score через межисточниковое согласие
- Ridge baseline как plug-in для будущей ML-коррекции
- Замена MockAggregator в боте

**Non-Goals:**
- Обучение ML-модели (Фаза 5)
- L1/L2 кэширование ответов (можно добавить позже)
- A/B тестирование моделей

## Decisions

**D1: `asyncio.gather(return_exceptions=True)` для параллельного сбора**
Позволяет продолжить при падении 1–2 источников. Упавшие источники логируются, их вес перераспределяется на оставшиеся.

**D2: `InsufficientSourcesError` при < MIN_SOURCES успешных**
`MIN_SOURCES=2` по умолчанию (настраивается). Бот показывает сообщение об ошибке пользователю.

**D3: Веса — статический словарь, нормализованный при частичном провале**
```python
active_weight = sum(weights[s] for s in successful_sources)
norm_weight = {s: weights[s] / active_weight for s in successful_sources}
```

**D4: Confidence через stdev температур**
```python
std = statistics.stdev(r.temperature_c for r in successful)
confidence = max(0.0, min(1.0, 1.0 - std / TEMP_STD_THRESHOLD))
```

**D5: Ridge model с нулевой дельтой до обучения**
`model.predict()` возвращает 0.0, пока нет обученной модели. Интерфейс совместим с реальной joblib-моделью.

**D6: Агрегатор инициализирует источники из конфига**
`WeatherAggregator.__init__` читает `settings.ENABLED_SOURCES` и создаёт только нужные источники.

## Risks / Trade-offs

- [Все источники кроме Open-Meteo требуют ключей] → При отсутствии ключа источник не добавляется в список; если активных < MIN_SOURCES — поднять `InsufficientSourcesError`
- [Разные шкалы уверенности у источников] → confidence считается только по температуре (наиболее стабильная метрика)
- [Forecast confidence] → применяется единый confidence ко всем точкам прогноза

## Migration Plan

1. Реализовать `weights.py`, `ensemble.py`, `model.py`
2. Реализовать `aggregator.py` с `WeatherAggregator`
3. Заменить MockAggregator в `handlers.py`
4. Написать тесты
5. Проверить что `pytest tests/` зелёный

## Open Questions

- Нужен ли отдельный `get_forecast` на агрегаторе или делать через `get_weather`?
