## ADDED Requirements

### Requirement: AccuWeather LocationKey с кэшем
`AccuWeatherSource` SHALL получать LocationKey через `/locations/v1/cities/geoposition/search` и кэшировать его в SQLite на 24ч.

#### Scenario: Первый запрос — кэш пустой
- **WHEN** `get_current()` вызывается впервые для координат
- **THEN** делается HTTP-запрос к `/locations/...`, ключ сохраняется в кэш

#### Scenario: Повторный запрос — кэш-попадание
- **WHEN** `get_current()` вызывается второй раз в течение 24ч для тех же координат
- **THEN** LocationKey берётся из SQLite, HTTP-запрос к `/locations/...` не делается

### Requirement: AccuWeather get_current
`AccuWeatherSource.get_current()` SHALL возвращать `WeatherReading` из `/currentconditions/v1/{locationKey}?details=true`.

#### Scenario: Успешный ответ
- **WHEN** API возвращает валидный JSON
- **THEN** возвращается `WeatherReading` с temperature_c (Metric), wind_speed_ms (Speed.Value km/h → m/s)

#### Scenario: HTTP 500 → SourceUnavailableError
- **WHEN** API возвращает 500
- **THEN** выбрасывается `SourceUnavailableError`

#### Scenario: HTTP 401 → SourceAuthError
- **WHEN** API возвращает 401
- **THEN** выбрасывается `SourceAuthError`

### Requirement: AccuWeather get_forecast
`AccuWeatherSource.get_forecast()` SHALL возвращать до 5 дней из `/forecasts/v1/daily/5day/{locationKey}`.

#### Scenario: Прогноз на 5 дней
- **WHEN** вызывается `get_forecast(lat, lon, days=5)`
- **THEN** возвращается список из 5 `ForecastPoint`

### Requirement: AccuWeather нормализация WeatherIcon
WeatherIcon (1–44) SHALL маппиться в `WeatherCondition`.

#### Scenario: Известные иконки
- **WHEN** WeatherIcon входит в диапазон 1–44
- **THEN** возвращается конкретный `WeatherCondition`, не `UNKNOWN`
