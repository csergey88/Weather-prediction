## ADDED Requirements

### Requirement: Confidence через stdev температур
Confidence SHALL вычисляться как `max(0, 1 - stdev / TEMP_STD_THRESHOLD)` где порог = 3.0°C.

#### Scenario: Источники согласны (разброс < 0.5°C)
- **WHEN** все источники дают температуры в диапазоне 0.5°C
- **THEN** confidence > 0.9

#### Scenario: Источники расходятся (разброс > 5°C)
- **WHEN** источники дают температуры с разбросом > 5°C
- **THEN** confidence < 0.5

#### Scenario: Один источник — confidence = 1.0
- **WHEN** успешен только один источник (stdev невозможна)
- **THEN** confidence = 1.0
