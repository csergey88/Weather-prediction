## Context

Проект реализует прогноз погоды через агрегацию 4 API-источников (OWM, WeatherAPI, AccuWeather, Open-Meteo) с ML-коррекцией. Бот является единственным UI-слоем поверх уже спроектированного backend-агрегатора. Код пишется с нуля — brownfield только по SPEC.md.

## Goals / Non-Goals

**Goals:**
- Telegram-бот принимает команды и возвращает форматированные карточки погоды
- Геокодирование: название города → (lat, lon) через Nominatim (без API-ключа)
- Сохранение дефолтной локации пользователя в SQLite
- Inline-клавиатуры для быстрых действий

**Non-Goals:**
- Inline-режим (`@weatherbot` в чужих чатах) — выходит за рамки текущей фазы
- Push-уведомления по расписанию
- Веб-интерфейс или REST API

## Decisions

**D1: aiogram 3 (async) вместо python-telegram-bot**
Выбран aiogram 3 — нативный async, FSM из коробки, активная поддержка. python-telegram-bot требует больше boilerplate для async.

**D2: geopy + Nominatim для геокодирования**
Nominatim бесплатен, без ключа, покрывает весь мир. Альтернатива — Google Maps API (платно) или OpenCage (ключ). Добавляем `user-agent` заголовок по требованиям OSM.

**D3: FSM только для /set_location**
Только сценарий сохранения геолокации требует многошагового диалога (команда → запрос геолокации → сохранение). Остальные команды — stateless.

**D4: Агрегатор вызывается напрямую, не через HTTP**
Бот и агрегатор живут в одном процессе — нет смысла в REST-прослойке. Прямой вызов `await aggregator.get_weather(lat, lon)`.

## Risks / Trade-offs

- [Nominatim rate limit: 1 req/sec] → Кэшировать геокодирование в SQLite на 24ч
- [AccuWeather 50 req/день] → Уже учтён в SPEC.md: кэш LocationKey на 24ч
- [Telegram API flood limits] → aiogram throttling middleware при необходимости
- [Агрегатор не реализован] → Заглушка `MockAggregator` для разработки бота изолированно

## Migration Plan

1. Реализовать Фазу 1 (модели, config, storage) как зависимость
2. Реализовать бот с `MockAggregator`
3. Подключить реальный агрегатор после Фазы 3
4. Деплой: `python -m weather_bot.main` (systemd unit или Docker)

## Open Questions

- Нужен ли `/admin`-режим для мониторинга состояния источников?
- Локализация карточки: только русский или i18n?
