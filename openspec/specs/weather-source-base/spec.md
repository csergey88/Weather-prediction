## ADDED Requirements

### Requirement: WeatherSource абстрактный класс
Каждый источник SHALL реализовывать методы `get_current(lat, lon)` и `get_forecast(lat, lon, days)`.

#### Scenario: Интерфейс источника
- **WHEN** создаётся новый класс источника без реализации абстрактных методов
- **THEN** Python выбрасывает `TypeError` при попытке инстанцировать класс

### Requirement: Иерархия исключений источника
Все ошибки источника SHALL наследоваться от `WeatherSourceError`.

#### Scenario: HTTP 5xx → SourceUnavailableError
- **WHEN** API возвращает статус 500
- **THEN** источник выбрасывает `SourceUnavailableError`

#### Scenario: Timeout → SourceTimeoutError
- **WHEN** HTTP-запрос превышает `timeout_s`
- **THEN** источник выбрасывает `SourceTimeoutError`

#### Scenario: HTTP 429 → SourceRateLimitError
- **WHEN** API возвращает статус 429
- **THEN** источник выбрасывает `SourceRateLimitError`

#### Scenario: HTTP 401/403 → SourceAuthError
- **WHEN** API возвращает статус 401 или 403
- **THEN** источник выбрасывает `SourceAuthError`

#### Scenario: Неожиданная схема JSON → SourceParseError
- **WHEN** ответ API содержит неожиданную структуру или отсутствующие поля
- **THEN** источник выбрасывает `SourceParseError`

### Requirement: health_check
Метод `health_check()` SHALL возвращать `bool` без выброса исключений.

#### Scenario: Источник доступен
- **WHEN** вызывается `health_check()` и API отвечает 2xx
- **THEN** возвращается `True`

#### Scenario: Источник недоступен
- **WHEN** вызывается `health_check()` и API недоступен
- **THEN** возвращается `False` (не выбрасывает исключение)
