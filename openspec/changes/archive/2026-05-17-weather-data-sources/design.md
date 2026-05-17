## Context

Бот работает с MockAggregator. Нужно реализовать 4 реальных источника погоды согласно SPEC.md §3. Модели `WeatherReading`, `ForecastPoint`, `Location`, `WeatherCondition` уже есть в `src/weather_bot/models/`.

## Goals / Non-Goals

**Goals:**
- Абстрактный `WeatherSource` с единым интерфейсом `get_current()` / `get_forecast()`
- 4 реализации с нормализацией в общие модели
- Иерархия исключений для типизированной обработки ошибок
- Async retry с exponential backoff
- Полное покрытие тестами через respx (без реальных сетевых запросов)

**Non-Goals:**
- Агрегация источников (это Фаза 3)
- ML-коррекция (Фаза 5)
- Кэширование ответов источников на уровне L1/L2 (Фаза 3)

## Decisions

**D1: httpx AsyncClient + tenacity retry**
httpx уже в зависимостях, нативно async. Tenacity даёт декларативный retry: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))`.

**D2: Каждый источник — отдельный модуль, один класс**
Изоляция: изменение одного API не затрагивает другие. Легко мокировать в тестах.

**D3: AccuWeather LocationKey кэшируется в SQLite на 24ч**
50 req/день на free-tier. Таблица `accuweather_location_cache` уже предусмотрена в `init_db()`.

**D4: WMO / OWM / WeatherAPI коды → WeatherCondition через dict-таблицы**
Статические словари внутри каждого модуля источника. Неизвестный код → `WeatherCondition.UNKNOWN`.

**D5: `health_check()` — GET к базовому эндпоинту, timeout 5 сек**
Используется в `/sources` команде бота. Не бросает исключений — возвращает `bool`.

## Risks / Trade-offs

- [AccuWeather бесплатный лимит 50 req/день] → LocationKey кэш на 24ч, данные не кэшируются здесь (кэш L2 — в Фазе 3)
- [Изменение схемы ответа API] → `SourceParseError` + тест `test_get_current_malformed_json`
- [Номализация кодов погоды неполная] → тест `test_normalize_all_condition_codes`, unknown → `UNKNOWN` (не падает)
- [Open-Meteo без ключа — fair-use] → при злоупотреблении может ограничить по IP; бот запрашивает не чаще чем раз в 10 мин (кэш Фазы 3)

## Migration Plan

1. Реализовать `sources/base.py` + `utils/retry.py`
2. Реализовать Open-Meteo первым (без ключа — удобно для разработки)
3. Реализовать OWM, WeatherAPI, AccuWeather
4. Написать тесты всех источников
5. MockAggregator остаётся до Фазы 3

## Open Questions

- Нужен ли `health_check` для Open-Meteo (нет ключа, всегда доступен)?
