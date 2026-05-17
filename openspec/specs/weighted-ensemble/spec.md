## ADDED Requirements

### Requirement: Взвешенное среднее числовых полей
`ensemble.py` SHALL вычислять взвешенное среднее для temperature_c, feels_like_c, humidity_pct, pressure_hpa, wind_speed_ms.

#### Scenario: Взвешенное усреднение температуры
- **WHEN** 4 источника дают температуры [10, 12, 11, 13] с весами [0.35, 0.30, 0.25, 0.10]
- **THEN** результирующая температура равна взвешенному среднему этих значений

### Requirement: Majority vote для WeatherCondition
Категориальные поля SHALL определяться голосованием с весами.

#### Scenario: Большинство за RAIN
- **WHEN** 3 источника возвращают RAIN, 1 — CLOUDY
- **THEN** итоговый condition = RAIN

#### Scenario: Победа по сумме весов
- **WHEN** RAIN набирает больший суммарный вес, чем CLOUDY
- **THEN** итоговый condition = RAIN
