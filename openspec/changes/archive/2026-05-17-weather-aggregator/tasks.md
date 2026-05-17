## 1. Веса источников

- [x] 1.1 Реализовать `aggregator/weights.py`: словарь весов по умолчанию + `normalize_weights(active_sources)`

## 2. Ensemble и модель

- [x] 2.1 Реализовать `forecast/ensemble.py`: взвешенное среднее числовых полей + majority vote для `WeatherCondition`
- [x] 2.2 Реализовать `forecast/model.py`: `CorrectionModel` с `predict(features) -> float` (нулевая дельта до joblib-модели)

## 3. Агрегатор

- [x] 3.1 Реализовать `aggregator/aggregator.py`: `WeatherAggregator.__init__` — инициализация источников из конфига
- [x] 3.2 Реализовать `get_weather(lat, lon)`: `asyncio.gather` + нормализация весов + confidence score + ML-коррекция
- [x] 3.3 Реализовать `get_forecast(lat, lon, days)`: параллельный сбор прогнозов + агрегация по дням
- [x] 3.4 Реализовать `health_check()`: опрос `source.health_check()` параллельно
- [x] 3.5 Добавить `InsufficientSourcesError` и проверку `< MIN_SOURCES`

## 4. Интеграция с ботом

- [x] 4.1 Заменить `MockAggregator` на `WeatherAggregator` в `bot/handlers.py`

## 5. Тесты

- [x] 5.1 Написать `tests/test_aggregator.py`: все источники успешны, один падает, < MIN_SOURCES, нормализация весов, majority vote
- [x] 5.2 Написать `tests/test_ensemble.py`: взвешенное среднее, prediction in range, confidence high/low, ML-коррекция применяется
