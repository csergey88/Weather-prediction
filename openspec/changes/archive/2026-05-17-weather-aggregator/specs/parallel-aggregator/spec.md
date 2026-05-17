## ADDED Requirements

### Requirement: Параллельный сбор данных
`WeatherAggregator.get_weather()` SHALL запрашивать все активные источники параллельно через `asyncio.gather`.

#### Scenario: Все источники успешны
- **WHEN** все 4 источника возвращают данные
- **THEN** возвращается `AggregatedWeather` с `readings` длиной 4

#### Scenario: Один источник падает
- **WHEN** 3 из 4 источников успешны, один бросает исключение
- **THEN** агрегация продолжается на 3 источниках, упавший логируется

### Requirement: InsufficientSourcesError
Если успешных источников меньше MIN_SOURCES, агрегатор SHALL бросить `InsufficientSourcesError`.

#### Scenario: Меньше MIN_SOURCES источников
- **WHEN** успешных ответов < 2 (MIN_SOURCES)
- **THEN** выбрасывается `InsufficientSourcesError`

### Requirement: get_forecast
`WeatherAggregator.get_forecast()` SHALL возвращать прогноз, агрегируя `ForecastPoint` по дням.

#### Scenario: Прогноз на N дней
- **WHEN** вызывается `get_forecast(lat, lon, days=5)`
- **THEN** возвращается `AggregatedWeather` с `forecast` длиной 5
