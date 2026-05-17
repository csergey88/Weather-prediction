## ADDED Requirements

### Requirement: WeatherAPI get_current и get_forecast одним запросом
`WeatherAPISource` SHALL получать current + forecast одним вызовом `/v1/forecast.json`.

#### Scenario: Успешный ответ
- **WHEN** API возвращает валидный JSON с `current` и `forecast.forecastday`
- **THEN** `get_current()` возвращает `WeatherReading` с wind_speed_ms (kph / 3.6)

#### Scenario: HTTP 500 → SourceUnavailableError
- **WHEN** API возвращает 500
- **THEN** выбрасывается `SourceUnavailableError`

#### Scenario: Конвертация скорости ветра
- **WHEN** API возвращает `wind_kph = 36.0`
- **THEN** `WeatherReading.wind_speed_ms == 10.0`

#### Scenario: Прогноз на N дней
- **WHEN** вызывается `get_forecast(lat, lon, days=5)`
- **THEN** возвращается список из 5 `ForecastPoint`

### Requirement: WeatherAPI нормализация condition.code
Все known condition.code SHALL маппиться в не-UNKNOWN `WeatherCondition`.

#### Scenario: Известные коды
- **WHEN** condition.code входит в стандартный набор WeatherAPI (1000, 1003, 1006, 1009, ...)
- **THEN** возвращается конкретный `WeatherCondition`
