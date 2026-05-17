## 1. Веса источников

- [ ] 1.1 Реализовать `aggregator/weights.py`: словарь весов по умолчанию + `normalize_weights(active_sources)`

## 2. Ensemble и модель

- [ ] 2.1 Реализовать `forecast/ensemble.py`: взвешенное среднее числовых полей + majority vote для `WeatherCondition`
- [ ] 2.2 Реализовать `forecast/model.py`: `CorrectionModel` с `predict(features) -> float` (нулевая дельта до joblib-модели)

## 3. Агрегатор

- [ ] 3.1 Реализовать `aggregator/aggregator.py`: `WeatherAggregator.__init__` — инициализация источников из конфига
- [ ] 3.2 Реализовать `get_weather(lat, lon)`: `asyncio.gather` + нормализация весов + confidence score + ML-коррекция
- [ ] 3.3 Реализовать `get_forecast(lat, lon, days)`: параллельный сбор прогнозов + агрегация по дням
- [ ] 3.4 Реализовать `health_check()`: опрос `source.health_check()` параллельно
- [ ] 3.5 Добавить `InsufficientSourcesError` и проверку `< MIN_SOURCES`

## 4. Интеграция с ботом

- [ ] 4.1 Заменить `MockAggregator` на `WeatherAggregator` в `bot/handlers.py`

## 5. Тесты

- [ ] 5.1 Написать `tests/test_aggregator.py`: все источники успешны, один падает, < MIN_SOURCES, нормализация весов, majority vote
- [ ] 5.2 Написать `tests/test_ensemble.py`: взвешенное среднее, prediction in range, confidence high/low, ML-коррекция применяется
