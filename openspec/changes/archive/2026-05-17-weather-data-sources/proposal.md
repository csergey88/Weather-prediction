## Why

Telegram-бот сейчас работает на MockAggregator и возвращает фиктивные данные. Для реальной работы нужны 4 источника погоды: OpenWeatherMap, WeatherAPI, AccuWeather, Open-Meteo — с нормализацией, обработкой ошибок и unit-тестами.

## What Changes

- Добавляется абстрактный класс `WeatherSource` с иерархией исключений
- Реализуются 4 конкретных источника: OWM, WeatherAPI, AccuWeather, Open-Meteo
- Каждый источник нормализует ответ API в `WeatherReading` и `list[ForecastPoint]`
- AccuWeather кэширует LocationKey на 24ч (50 req/день лимит)
- Все HTTP-запросы через httpx (async) с retry через tenacity
- Unit-тесты всех источников через respx (mock HTTP)

## Capabilities

### New Capabilities

- `weather-source-base`: Абстрактный класс `WeatherSource` + иерархия исключений (`SourceUnavailableError`, `SourceTimeoutError`, `SourceRateLimitError`, `SourceAuthError`, `SourceParseError`)
- `open-meteo-source`: Источник Open-Meteo (без API-ключа, WMO-коды → WeatherCondition)
- `openweathermap-source`: Источник OpenWeatherMap (OWM weather-id → WeatherCondition)
- `weatherapi-source`: Источник WeatherAPI.com (condition.code → WeatherCondition, wind kph→m/s)
- `accuweather-source`: Источник AccuWeather (WeatherIcon 1-44 → WeatherCondition, LocationKey-кэш)
- `retry-util`: Async retry с exponential backoff через tenacity

### Modified Capabilities

## Impact

- Новые модули: `src/weather_bot/sources/`, `src/weather_bot/utils/retry.py`
- Новые зависимости: уже есть в `pyproject.toml` (`httpx`, `tenacity`)
- Требует `OWM_API_KEY`, `WEATHERAPI_KEY`, `ACCUWEATHER_KEY` в `.env`
- MockAggregator в `aggregator/aggregator.py` остаётся как fallback до Фазы 3
