## Why

Пользователям нужен удобный интерфейс для получения агрегированного прогноза погоды из 4 источников. Telegram-бот — наиболее доступный канал: не требует установки, работает на любом устройстве.

## What Changes

- Добавляется Telegram-бот на aiogram 3 как точка входа для пользователей
- Реализуются команды `/weather`, `/forecast`, `/set_location`, `/sources`, `/help`, `/start`
- Добавляется геокодирование города в координаты (город → lat/lon)
- Добавляется сохранение дефолтной локации пользователя в SQLite
- Добавляются inline-клавиатуры для быстрых действий (Прогноз 3д / 7д / Обновить)
- Добавляется форматирование карточки погоды с emoji и confidence-баром

## Capabilities

### New Capabilities

- `telegram-bot-commands`: Обработка команд `/start`, `/weather`, `/forecast`, `/set_location`, `/sources`, `/help`
- `weather-card-formatter`: Форматирование карточки текущей погоды и прогноза в Markdown
- `city-geocoding`: Преобразование названия города в координаты (lat, lon) через geopy/nominatim
- `user-location-storage`: Сохранение и получение дефолтной геолокации пользователя по telegram_id

### Modified Capabilities

## Impact

- Новые модули: `src/weather_bot/bot/`, `src/weather_bot/utils/geo.py`, `src/weather_bot/main.py`
- Новая зависимость: `aiogram ^3.13`, `geopy ^2.4`
- Требует `TELEGRAM_BOT_TOKEN` в `.env`
- Опирается на агрегатор (Фазы 1–3) как на backend
