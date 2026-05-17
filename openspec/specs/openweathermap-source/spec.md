## ADDED Requirements

### Requirement: OWM get_current
`OpenWeatherMapSource.get_current()` SHALL возвращать `WeatherReading` из `/data/2.5/weather`.

#### Scenario: Успешный ответ
- **WHEN** API возвращает валидный JSON с полями `main`, `wind`, `weather`
- **THEN** возвращается `WeatherReading` с temperature_c, humidity_pct, wind_speed_ms, condition

#### Scenario: HTTP 500 → SourceUnavailableError
- **WHEN** API возвращает 500
- **THEN** выбрасывается `SourceUnavailableError`

#### Scenario: HTTP 429 → SourceRateLimitError
- **WHEN** API возвращает 429
- **THEN** выбрасывается `SourceRateLimitError`

#### Scenario: HTTP 401 → SourceAuthError
- **WHEN** API возвращает 401
- **THEN** выбрасывается `SourceAuthError`

#### Scenario: Битый JSON → SourceParseError
- **WHEN** ответ содержит неожиданную структуру
- **THEN** выбрасывается `SourceParseError`

### Requirement: OWM get_forecast
`OpenWeatherMapSource.get_forecast()` SHALL возвращать `list[ForecastPoint]` из `/data/2.5/forecast` (3h шаги → дневные точки).

#### Scenario: Прогноз на 3 дня
- **WHEN** вызывается `get_forecast(lat, lon, days=3)`
- **THEN** возвращается список из 3 `ForecastPoint` (по одному на день)

### Requirement: OWM нормализация кодов
Все weather-id (2xx-8xx) SHALL маппиться в `WeatherCondition`.

#### Scenario: Известные коды не UNKNOWN
- **WHEN** weather.id входит в диапазоны 2xx, 3xx, 5xx, 6xx, 7xx, 800, 80x
- **THEN** возвращается конкретный `WeatherCondition`, не `UNKNOWN`
