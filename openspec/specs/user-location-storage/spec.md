## ADDED Requirements

### Requirement: Сохранение локации пользователя
Storage SHALL сохранять дефолтную геолокацию пользователя по `telegram_id`.

#### Scenario: Первое сохранение
- **WHEN** вызывается `save_user_location(telegram_id=123, location=loc)`
- **THEN** запись создаётся в таблице `user_locations`

#### Scenario: Обновление локации
- **WHEN** вызывается `save_user_location` для уже существующего `telegram_id`
- **THEN** старая запись обновляется (UPSERT)

### Requirement: Получение локации пользователя
Storage SHALL возвращать сохранённую локацию пользователя или `None`.

#### Scenario: Локация существует
- **WHEN** вызывается `get_user_location(telegram_id=123)`
- **THEN** возвращается `Location` с сохранёнными координатами

#### Scenario: Локация не сохранена
- **WHEN** вызывается `get_user_location(telegram_id=999)`
- **THEN** возвращается `None`
