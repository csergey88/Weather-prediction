## 1. Базовый слой

- [x] 1.1 Реализовать `sources/base.py`: абстрактный `WeatherSource` + иерархия исключений (`WeatherSourceError`, `SourceUnavailableError`, `SourceTimeoutError`, `SourceRateLimitError`, `SourceAuthError`, `SourceParseError`)
- [x] 1.2 Реализовать `utils/retry.py`: `retry_async` декоратор через tenacity (3 попытки, exponential backoff 1→2→4с, retry только на `SourceUnavailableError`/`SourceTimeoutError`)

## 2. Open-Meteo (без ключа)

- [x] 2.1 Реализовать `sources/open_meteo.py`: `get_current()` через `/v1/forecast` с WMO-кодами
- [x] 2.2 Реализовать `get_forecast()` для Open-Meteo: группировка hourly → дневные `ForecastPoint`
- [x] 2.3 Написать таблицу нормализации WMO-кодов → `WeatherCondition`
- [x] 2.4 Написать тесты `tests/test_sources/test_open_meteo.py` (7 сценариев: success, 500, timeout, 429, malformed, all codes, forecast days)

## 3. OpenWeatherMap

- [x] 3.1 Реализовать `sources/openweathermap.py`: `get_current()` через `/data/2.5/weather`
- [x] 3.2 Реализовать `get_forecast()` для OWM: `/data/2.5/forecast` (3h шаги → дневные точки)
- [x] 3.3 Написать таблицу нормализации OWM weather-id → `WeatherCondition`
- [x] 3.4 Написать тесты `tests/test_sources/test_openweathermap.py` (7 сценариев)

## 4. WeatherAPI

- [x] 4.1 Реализовать `sources/weatherapi.py`: один запрос `/v1/forecast.json` для current + forecast
- [x] 4.2 Написать таблицу нормализации condition.code → `WeatherCondition`
- [x] 4.3 Написать тесты `tests/test_sources/test_weatherapi.py` (7 сценариев)

## 5. AccuWeather

- [x] 5.1 Добавить таблицу `accuweather_location_cache` в `storage/db.py`
- [x] 5.2 Реализовать `sources/accuweather.py`: `_get_location_key()` с SQLite-кэшем на 24ч
- [x] 5.3 Реализовать `get_current()` через `/currentconditions/v1/{key}?details=true`
- [x] 5.4 Реализовать `get_forecast()` через `/forecasts/v1/daily/5day/{key}`
- [x] 5.5 Написать таблицу нормализации WeatherIcon (1–44) → `WeatherCondition`
- [x] 5.6 Написать тесты `tests/test_sources/test_accuweather.py` (7 сценариев + кэш LocationKey)

## 6. Финализация

- [x] 6.1 Добавить `__init__.py` для `sources/` с экспортом всех классов
- [x] 6.2 Убедиться что `pytest tests/test_sources/` проходит целиком
