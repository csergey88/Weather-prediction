## ADDED Requirements

### Requirement: Open-Meteo get_current
`OpenMeteoSource.get_current()` SHALL возвращать `WeatherReading` из `/v1/forecast` с WMO-кодами.

#### Scenario: Успешный ответ
- **WHEN** API возвращает валидный JSON с `current` и `current_units`
- **THEN** возвращается `WeatherReading` с корректными полями (temperature_c, humidity_pct, wind_speed_ms, condition)

#### Scenario: HTTP 500
- **WHEN** API возвращает 500
- **THEN** выбрасывается `SourceUnavailableError`

#### Scenario: Timeout
- **WHEN** запрос превышает timeout
- **THEN** выбрасывается `SourceTimeoutError`

#### Scenario: Битый JSON
- **WHEN** ответ содержит невалидный JSON или отсутствует поле `current`
- **THEN** выбрасывается `SourceParseError`

### Requirement: Open-Meteo get_forecast
`OpenMeteoSource.get_forecast()` SHALL возвращать `list[ForecastPoint]` длиной `days`.

#### Scenario: Прогноз на 5 дней
- **WHEN** вызывается `get_forecast(lat, lon, days=5)`
- **THEN** возвращается список из 5 `ForecastPoint`

### Requirement: WMO нормализация
Все известные WMO-коды (0, 1-3, 45-48, 51-67, 71-77, 80-82, 85-86, 95-99) SHALL маппиться в не-UNKNOWN `WeatherCondition`.

#### Scenario: Известные коды
- **WHEN** WMO-код входит в диапазоны 0, 1-3, 45, 51, 61, 71, 80, 85, 95
- **THEN** возвращается конкретный `WeatherCondition`, не `UNKNOWN`
