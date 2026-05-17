## 1. Зависимости и конфигурация

- [ ] 1.1 Добавить `aiogram ^3.13` и `geopy ^2.4` в `pyproject.toml`
- [ ] 1.2 Добавить `TELEGRAM_BOT_TOKEN` в `config.py` (Settings) и `.env.example`

## 2. Геокодирование (utils/geo.py)

- [ ] 2.1 Реализовать `geocode(city: str) -> Location` через geopy Nominatim
- [ ] 2.2 Добавить `CityNotFoundError` в иерархию исключений
- [ ] 2.3 Реализовать SQLite-кэш геокодирования на 24ч (таблица `geocode_cache`)
- [ ] 2.4 Добавить rate-limit задержку 1 сек между запросами к Nominatim

## 3. Хранилище локаций (storage/db.py)

- [ ] 3.1 Добавить таблицу `user_locations` (telegram_id, lat, lon, city, country, timezone)
- [ ] 3.2 Реализовать `save_user_location(telegram_id, location)` с UPSERT
- [ ] 3.3 Реализовать `get_user_location(telegram_id) -> Location | None`

## 4. Форматтер карточек (bot/formatters.py)

- [ ] 4.1 Реализовать `format_current_weather(agg: AggregatedWeather) -> str`
- [ ] 4.2 Реализовать `format_forecast(points: list[ForecastPoint], city: str) -> str`
- [ ] 4.3 Реализовать `format_confidence_bar(confidence: float) -> str` (████░ 82%)
- [ ] 4.4 Реализовать маппинг `WeatherCondition → emoji`

## 5. Inline-клавиатуры (bot/keyboards.py)

- [ ] 5.1 Реализовать `weather_actions_kb(city: str) -> InlineKeyboardMarkup` (Прогноз 3д / 7д / Обновить)
- [ ] 5.2 Реализовать `share_location_kb() -> ReplyKeyboardMarkup`

## 6. Обработчики команд (bot/handlers.py)

- [ ] 6.1 Реализовать handler `/start`
- [ ] 6.2 Реализовать handler `/weather [город]`
- [ ] 6.3 Реализовать handler `/forecast [город] [дни]` с clamp 1–7
- [ ] 6.4 Реализовать FSM для `/set_location` (ожидание геолокации → сохранение)
- [ ] 6.5 Реализовать handler `/sources`
- [ ] 6.6 Реализовать handler `/help`
- [ ] 6.7 Реализовать callback-handler для inline-кнопок (Прогноз 3д / 7д / Обновить)

## 7. Точка входа (main.py)

- [ ] 7.1 Реализовать `main()`: инициализация бота, dp, регистрация роутеров, polling

## 8. Тесты

- [ ] 8.1 Написать тесты `test_bot_handlers.py` (все 6 сценариев из spec)
- [ ] 8.2 Написать тесты форматтера: карточка, прогноз, confidence-бар
- [ ] 8.3 Написать тесты `utils/geo.py`: успех, `CityNotFoundError`, кэш-попадание
