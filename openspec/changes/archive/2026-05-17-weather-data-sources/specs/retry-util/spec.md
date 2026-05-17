## ADDED Requirements

### Requirement: Async retry с exponential backoff
`retry_async` SHALL повторять вызов при `SourceUnavailableError` и `SourceTimeoutError` до 3 раз с задержкой 1→2→4 сек.

#### Scenario: Успех со второй попытки
- **WHEN** первый вызов выбрасывает `SourceUnavailableError`, второй — успешен
- **THEN** возвращается результат второго вызова

#### Scenario: Исчерпаны все попытки
- **WHEN** все 3 попытки выбрасывают `SourceUnavailableError`
- **THEN** пробрасывается последнее исключение

#### Scenario: Не-retriable ошибка
- **WHEN** вызов выбрасывает `SourceAuthError`
- **THEN** исключение пробрасывается немедленно без повторов
