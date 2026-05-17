## Why

Источники данных готовы, но бот всё ещё использует MockAggregator. Нужен реальный агрегатор: параллельный сбор из 4 источников, взвешенное усреднение и Ridge-модель для коррекции температуры.

## What Changes

- Реализуется `aggregator/weights.py` — веса источников и их нормализация
- Реализуется `aggregator/aggregator.py` — параллельный сбор через `asyncio.gather`, нормализация, confidence score
- Реализуется `forecast/ensemble.py` — взвешенное усреднение числовых и категориальных полей
- Реализуется `forecast/model.py` — Ridge baseline (нулевая дельта до обучения)
- MockAggregator в `bot/handlers.py` заменяется на реальный `WeatherAggregator`
- Добавляются тесты агрегатора и ensemble

## Capabilities

### New Capabilities

- `source-weights`: Веса источников по умолчанию, нормализация при выпадении источника
- `parallel-aggregator`: Параллельный сбор через `asyncio.gather`, обработка partial failures, `InsufficientSourcesError`
- `weighted-ensemble`: Взвешенное среднее числовых полей + majority vote для `WeatherCondition`
- `confidence-score`: Confidence через стандартное отклонение температур источников
- `ridge-model`: Ridge baseline (нулевая дельта) + интерфейс для будущей ML-модели

### Modified Capabilities

- `telegram-bot-commands`: Заменить `MockAggregator` на `WeatherAggregator` в handlers.py

## Impact

- Новые модули: `aggregator/weights.py`, `aggregator/aggregator.py`, `forecast/ensemble.py`, `forecast/model.py`
- Изменение: `bot/handlers.py` — инициализация реального агрегатора
- Новые тесты: `tests/test_aggregator.py`, `tests/test_ensemble.py`
- Требует `OWM_API_KEY`, `WEATHERAPI_KEY`, `ACCUWEATHER_KEY` в `.env` для полной работы; без ключей работает на Open-Meteo (MIN_SOURCES=1 fallback)
