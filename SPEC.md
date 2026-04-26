# Spec-Driven Development: Weather Forecast Bot

## Обзор

Telegram-бот на Python, который агрегирует данные о погоде с четырёх источников
(OpenWeatherMap, WeatherAPI.com, AccuWeather, Open-Meteo) и формирует прогноз
с помощью гибридного подхода: взвешенная агрегация ответов API + коррекция
через лёгкую ML-модель.

---

## 1. Структура проекта

```
weather-prediction/
├── SPEC.md
├── pyproject.toml
├── .env.example
├── models/                        # Сохранённые joblib-модели
├── data/                          # SQLite БД (история, кэш)
├── scripts/
│   ├── collect_training_data.py   # Сбор данных для обучения ML
│   └── train_model.py             # Обучение Ridge / LightGBM
├── src/
│   └── weather_bot/
│       ├── __init__.py
│       ├── main.py                # Точка входа — запуск бота
│       ├── config.py              # Pydantic-settings конфигурация
│       │
│       ├── bot/
│       │   ├── handlers.py        # Telegram-обработчики команд
│       │   ├── keyboards.py       # Inline-клавиатуры
│       │   └── formatters.py      # Форматирование карточек погоды
│       │
│       ├── sources/
│       │   ├── base.py            # Абстрактный класс WeatherSource
│       │   ├── openweathermap.py
│       │   ├── weatherapi.py
│       │   ├── accuweather.py
│       │   └── open_meteo.py
│       │
│       ├── aggregator/
│       │   ├── aggregator.py      # Параллельный сбор + нормализация
│       │   └── weights.py         # Веса источников
│       │
│       ├── forecast/
│       │   ├── ensemble.py        # Weighted ensemble прогноз
│       │   └── model.py           # ML-коррекция (sklearn Ridge / LightGBM)
│       │
│       ├── models/
│       │   ├── weather.py         # Pydantic-модели WeatherReading, Location
│       │   └── forecast.py        # ForecastPoint, AggregatedWeather
│       │
│       ├── storage/
│       │   ├── db.py              # SQLite (aiosqlite) — история, локации
│       │   └── cache.py           # In-memory LRU TTL-кэш
│       │
│       └── utils/
│           ├── geo.py             # Геокодирование: город → (lat, lon)
│           └── retry.py           # Async retry с exponential backoff
│
└── tests/
    ├── conftest.py
    ├── test_sources/
    │   ├── test_openweathermap.py
    │   ├── test_weatherapi.py
    │   ├── test_accuweather.py
    │   └── test_open_meteo.py
    ├── test_aggregator.py
    ├── test_ensemble.py
    └── test_bot_handlers.py
```

---

## 2. Модели данных

### 2.1 `WeatherCondition` — перечисление состояний погоды

```python
class WeatherCondition(str, Enum):
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    SNOW = "snow"
    SLEET = "sleet"
    STORM = "storm"
    FOG = "fog"
    HAIL = "hail"
    UNKNOWN = "unknown"
```

### 2.2 `Location`

```python
class Location(BaseModel):
    lat: float                     # -90..90
    lon: float                     # -180..180
    city: str | None = None
    country: str | None = None
    timezone: str | None = None    # "Europe/Moscow"
```

### 2.3 `WeatherReading` — показания одного источника

```python
class WeatherReading(BaseModel):
    source: str                    # "openweathermap" | "weatherapi" | "accuweather" | "open_meteo"
    location: Location
    fetched_at: datetime
    temperature_c: float           # -90..60
    feels_like_c: float
    humidity_pct: int              # 0-100
    pressure_hpa: float            # 870..1085
    wind_speed_ms: float           # >= 0
    wind_direction_deg: int        # 0-360
    visibility_km: float | None
    uv_index: float | None         # 0-11+
    condition: WeatherCondition
    precipitation_mm: float        # осадки за текущий час
    cloud_cover_pct: int           # 0-100
```

### 2.4 `ForecastPoint` — одна точка прогноза

```python
class ForecastPoint(BaseModel):
    target_dt: datetime
    temperature_c: float
    temperature_min_c: float
    temperature_max_c: float
    precipitation_probability_pct: int  # 0-100
    precipitation_mm: float
    condition: WeatherCondition
    wind_speed_ms: float
    confidence: float              # 0.0-1.0 — межисточниковое согласие
```

### 2.5 `AggregatedWeather` — итоговый результат

```python
class AggregatedWeather(BaseModel):
    location: Location
    aggregated_at: datetime
    readings: list[WeatherReading]          # сырые данные всех источников
    current: WeatherReading                  # взвешенное среднее
    forecast: list[ForecastPoint]            # до 7 дней
    source_weights: dict[str, float]         # актуальные веса
    ensemble_version: str                    # "v1_ridge" | "v2_lgbm"
```

---

## 3. Спецификация источников данных

### 3.1 Абстрактный класс `WeatherSource`

```python
class WeatherSource(ABC):
    name: str
    base_url: str
    timeout_s: int = 10

    @abstractmethod
    async def get_current(self, lat: float, lon: float) -> WeatherReading: ...

    @abstractmethod
    async def get_forecast(self, lat: float, lon: float, days: int) -> list[ForecastPoint]: ...

    async def health_check(self) -> bool: ...
```

**Иерархия исключений:**
```
WeatherSourceError
├── SourceUnavailableError    # HTTP 5xx, сеть недоступна
├── SourceTimeoutError        # Превышен timeout_s
├── SourceRateLimitError      # HTTP 429
├── SourceAuthError           # HTTP 401/403
└── SourceParseError          # Неожиданная схема ответа
```

### 3.2 OpenWeatherMap

| | |
|---|---|
| **Base URL** | `https://api.openweathermap.org` |
| **Current** | `GET /data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&lang=ru` |
| **Forecast** | `GET /data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&cnt=56` |
| **Rate limit** | 60 req/мин (free) |
| **Нормализация** | `weather[0].id` (2xx-8xx) → `WeatherCondition`; `wind.speed` уже в м/с |

### 3.3 WeatherAPI.com

| | |
|---|---|
| **Base URL** | `https://api.weatherapi.com` |
| **Endpoint** | `GET /v1/forecast.json?key={key}&q={lat},{lon}&days={days}&aqi=no` |
| **Rate limit** | 1 000 000 вызовов/мес (free) |
| **Особенность** | Один запрос возвращает current + forecast |
| **Нормализация** | `condition.code` (таблица кодов) → `WeatherCondition`; `wind_kph / 3.6` → м/с |

### 3.4 AccuWeather

| | |
|---|---|
| **Base URL** | `https://dataservice.accuweather.com` |
| **Location** | `GET /locations/v1/cities/geoposition/search?q={lat},{lon}&apikey={key}` |
| **Current** | `GET /currentconditions/v1/{locationKey}?apikey={key}&details=true` |
| **Forecast** | `GET /forecasts/v1/daily/5day/{locationKey}?apikey={key}&metric=true` |
| **Rate limit** | 50 req/день (free) — **кэшировать LocationKey на 24ч, данные на 30 мин** |
| **Нормализация** | `WeatherIcon` (1-44) → `WeatherCondition`; `Speed.Value` (км/ч → м/с) |

### 3.5 Open-Meteo

| | |
|---|---|
| **Base URL** | `https://api.open-meteo.com` |
| **Endpoint** | `GET /v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weathercode&hourly=temperature_2m,...&forecast_days={days}` |
| **Rate limit** | Нет (fair-use, без ключа) |
| **Нормализация** | WMO weather code (0, 1-3, 45-48, 51-67, 71-77, 80-82, 85-86, 95-99) → `WeatherCondition` |

---

## 4. Агрегация и гибридный прогноз

### 4.1 Параллельный сбор данных

```python
# Псевдокод ядра агрегатора
results = await asyncio.gather(
    *[source.get_current(lat, lon) for source in active_sources],
    return_exceptions=True,
)
successful = [r for r in results if isinstance(r, WeatherReading)]
if len(successful) < MIN_SOURCES:       # MIN_SOURCES = 2
    raise InsufficientSourcesError(...)
```

- Таймаут на каждый источник: `SOURCE_TIMEOUT_S` (default 10 сек)
- Ошибка одного источника: логируется, вес перераспределяется на оставшиеся
- При `len(successful) < 2` → возвращается `InsufficientSourcesError`

### 4.2 Взвешенное усреднение

**Веса по умолчанию** (калибруются по MAE на исторических данных):

| Источник | Вес |
|---|---|
| open_meteo | 0.35 |
| openweathermap | 0.30 |
| weatherapi | 0.25 |
| accuweather | 0.10 |

**Числовые поля** (temperature, pressure, humidity, wind\_speed…):
```
value = sum(reading.field * weight[reading.source] for reading in successful)
      / sum(weight[s] for s in successful_sources)
```

**Категориальные поля** (`condition`):
```
condition = argmax(sum of weights for each WeatherCondition voted)
```

### 4.3 ML-коррекция температуры

**Модель v1 (baseline):** Ridge Regression  
**Модель v2 (upgrade):** LightGBM (при улучшении MAE > 5%)

**Входные признаки:**
```python
features = [
    owm_temp, wa_temp, acw_temp, om_temp,   # показания источников
    owm_pressure, om_pressure,               # атмосферное давление
    ensemble_humidity,
    hour_of_day,   # 0-23
    month,         # 1-12
    lat, lon,      # координаты
]
```

**Применение:**
```python
delta = model.predict([features])[0]
corrected_temp = ensemble_temp + delta
```

**Обучение:** офлайн на данных ERA5 / NOAA (скрипт `scripts/train_model.py`).  
Модель сохраняется как `models/correction_model_{version}.joblib`.

### 4.4 Confidence score

```python
std = statistics.stdev(r.temperature_c for r in successful)
confidence = max(0.0, min(1.0, 1.0 - std / TEMP_STD_THRESHOLD))
# TEMP_STD_THRESHOLD = 3.0 °C
```

---

## 5. Telegram Bot

### 5.1 Команды

| Команда | Описание |
|---|---|
| `/start` | Приветствие + кнопки быстрого доступа |
| `/weather [город]` | Текущая погода |
| `/forecast [город] [дни]` | Прогноз на N дней (1-7, default 3) |
| `/set_location` | Сохранить геолокацию по умолчанию |
| `/sources` | Статус источников: доступность и веса |
| `/help` | Список команд |

**Inline mode:** `@weatherbot <город>` → карточка в любом чате.

### 5.2 Диалоговые сценарии

**A. Быстрый запрос по названию города:**
```
User → /weather Москва
Bot  → [загрузка...] → карточка погоды
       [Прогноз 3д] [Прогноз 7д] [Обновить]
```

**B. Геолокация:**
```
User → /set_location
Bot  → "Отправьте геолокацию:" [Share Location]
User → [геолокация]
Bot  → "Сохранено: Москва (55.75, 37.62)"
```

**C. Неизвестный город:**
```
User → /weather xyzabc123
Bot  → "Город не найден. Уточните название или отправьте геолокацию."
```

### 5.3 Формат карточки погоды

```
🌤 Москва, Россия
📅 26 апреля 2026, 20:00 MSK

🌡 Температура:   +12°C (ощущается +9°C)
💧 Влажность:     68%
💨 Ветер:         СЗ 5.2 м/с
👁 Видимость:     10 км
🌧 Осадки:        0.0 мм/ч
☁️ Облачность:    45%

📊 Уверенность прогноза: ████░ 82%
🔄 Источники: OWM ✓  WA ✓  ACW ✓  OM ✓
⏱ Обновлено: 2 мин назад
```

### 5.4 Формат прогноза (3 дня)

```
📅 Прогноз для Москвы

Пт 27 апр: 🌦 +8..+14°C | 💧 60% | 💨 4 м/с
Сб 28 апр: ⛅ +10..+17°C | 💧 20% | 💨 3 м/с
Вс 29 апр: ☀️ +13..+20°C | 💧 5%  | 💨 2 м/с
```

---

## 6. Кэширование

| Уровень | Ключ кэша | TTL | Хранилище |
|---|---|---|---|
| L1 memory | `{source}:{lat:.2f}:{lon:.2f}` | 10 мин | `cachetools.TTLCache` |
| L2 db current | `agg:current:{lat:.2f}:{lon:.2f}` | 15 мин | SQLite |
| L2 db forecast | `agg:forecast:{lat:.2f}:{lon:.2f}:{days}` | 3 часа | SQLite |
| AccuWeather location | `acw:loc:{lat:.2f}:{lon:.2f}` | 24 часа | SQLite |
| User default location | `user:{telegram_id}:location` | постоянно | SQLite |

Координаты округляются до 2 знаков (~1 км) для группировки близких запросов.

---

## 7. Конфигурация

```python
# src/weather_bot/config.py
class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # API Keys
    OWM_API_KEY: str
    WEATHERAPI_KEY: str
    ACCUWEATHER_KEY: str
    # Open-Meteo не требует ключа

    # Источники
    ENABLED_SOURCES: list[str] = ["openweathermap", "weatherapi", "accuweather", "open_meteo"]
    SOURCE_TIMEOUT_S: int = 10
    MIN_SOURCES: int = 2

    # ML
    MODEL_VERSION: str = "v1"
    MODEL_PATH: str = "models/correction_model_v1.joblib"
    TEMP_STD_THRESHOLD: float = 3.0

    # Storage
    DB_PATH: str = "data/weather.db"
    CACHE_TTL_CURRENT_S: int = 600
    CACHE_TTL_FORECAST_S: int = 10800

    model_config = SettingsConfigDict(env_file=".env")
```

```dotenv
# .env.example
TELEGRAM_BOT_TOKEN=
OWM_API_KEY=
WEATHERAPI_KEY=
ACCUWEATHER_KEY=
MODEL_VERSION=v1
```

---

## 8. Зависимости

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.12"
aiogram = "^3.13"           # Telegram Bot
httpx = "^0.27"             # Async HTTP
pydantic = "^2.8"
pydantic-settings = "^2.4"
aiosqlite = "^0.20"
cachetools = "^5.4"
scikit-learn = "^1.5"       # Ridge baseline
lightgbm = "^4.5"           # LightGBM (v2 ML)
joblib = "^1.4"
tenacity = "^9.0"           # Retry

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
respx = "^0.21"             # HTTP mock для httpx
pytest-cov = "^5.0"
ruff = "^0.6"
mypy = "^1.11"
```

---

## 9. Спецификация тестов

### 9.1 Unit-тесты источников (`tests/test_sources/`)

Каждый из 4 источников проверяется:

| Тест | Что проверяет |
|---|---|
| `test_get_current_success` | Нормальный ответ API → корректный `WeatherReading` |
| `test_get_current_http_error` | HTTP 500 → `SourceUnavailableError` |
| `test_get_current_timeout` | Таймаут httpx → `SourceTimeoutError` |
| `test_get_current_rate_limit` | HTTP 429 → `SourceRateLimitError` |
| `test_get_current_malformed_json` | Кривой JSON → `SourceParseError` |
| `test_normalize_all_condition_codes` | Все known коды → не `UNKNOWN` |
| `test_get_forecast_returns_correct_days` | `days=5` → 5 точек прогноза |

Все HTTP-запросы мокируются через `respx`.

### 9.2 Unit-тесты агрегатора (`tests/test_aggregator.py`)

| Тест | Что проверяет |
|---|---|
| `test_all_sources_available` | 4 успешных → корректное взвешенное среднее |
| `test_one_source_fails` | 3 из 4 → агрегация продолжается, вес перераспределяется |
| `test_below_min_sources` | < 2 → `InsufficientSourcesError` |
| `test_weights_sum_to_one` | Нормализованные веса сумма = 1.0 |
| `test_condition_majority_vote` | 3 RAIN + 1 CLOUDY → RAIN |

### 9.3 Unit-тесты ensemble/ML (`tests/test_ensemble.py`)

| Тест | Что проверяет |
|---|---|
| `test_prediction_in_valid_range` | Результат в диапазоне −60..+60°C |
| `test_confidence_high_when_sources_agree` | Разброс < 0.5°C → confidence > 0.9 |
| `test_confidence_low_when_sources_disagree` | Разброс > 5°C → confidence < 0.5 |
| `test_ml_correction_applied` | С обученной моделью результат отличается от ensemble |

### 9.4 Integration-тесты bot handlers (`tests/test_bot_handlers.py`)

| Тест | Что проверяет |
|---|---|
| `test_weather_command_valid_city` | `/weather Москва` → карточка с погодой |
| `test_weather_command_no_city` | `/weather` без аргумента → запрос города |
| `test_weather_command_unknown_city` | Несуществующий город → понятное сообщение |
| `test_forecast_days_clamped` | `/forecast Moscow 10` → прогноз на 7 дней (не 10) |
| `test_set_location_saves_to_db` | Геолокация → сохранена в SQLite |
| `test_sources_command` | `/sources` → статус всех 4 источников |

**Маркер:** `@pytest.mark.integration` — тесты с реальными ключами, запускаются отдельно.

---

## 10. Метрики качества

| Метрика | Цель |
|---|---|
| Температура MAE (24 ч) | < 1.5 °C |
| Температура MAE (72 ч) | < 2.5 °C |
| Вероятность осадков Precision | > 75% |
| Доступность сервиса | > 99% (за счёт fallback на оставшиеся источники) |
| p95 latency ответа бота | < 3 сек |
| Покрытие тестами | > 85% |

---

## 11. Фазы реализации

### Фаза 1 — Фундамент

- [ ] `pyproject.toml`, `.env.example`, структура директорий
- [ ] `models/weather.py`, `models/forecast.py` — Pydantic-модели
- [ ] `config.py` — конфигурация
- [ ] `utils/retry.py` — async retry (tenacity)
- [ ] `storage/cache.py`, `storage/db.py` — кэш и SQLite-схема

### Фаза 2 — Источники данных

- [ ] `sources/base.py` — абстрактный класс + иерархия исключений
- [ ] `sources/open_meteo.py` (без ключа — первым для разработки)
- [ ] `sources/openweathermap.py`
- [ ] `sources/weatherapi.py`
- [ ] `sources/accuweather.py`
- [ ] Unit-тесты всех источников (respx mock)

### Фаза 3 — Агрегация и прогноз

- [ ] `aggregator/weights.py`
- [ ] `aggregator/aggregator.py` — параллельный сбор
- [ ] `forecast/ensemble.py` — weighted ensemble
- [ ] `forecast/model.py` — Ridge baseline (нулевая дельта до обучения)
- [ ] Тесты агрегатора и ensemble

### Фаза 4 — Telegram Bot

- [ ] `bot/formatters.py` — форматирование карточек
- [ ] `bot/keyboards.py` — inline клавиатуры
- [ ] `bot/handlers.py` — все команды + FSM
- [ ] `utils/geo.py` — геокодирование город → координаты
- [ ] `main.py` — запуск бота
- [ ] Тесты handlers

### Фаза 5 — ML-коррекция

- [ ] `scripts/collect_training_data.py` — сбор исторических данных
- [ ] `scripts/train_model.py` — обучение Ridge / LightGBM
- [ ] Интеграция `forecast/model.py` с реальной моделью
- [ ] A/B оценка: MAE ensemble vs ML-corrected
- [ ] Upgrade до LightGBM при улучшении MAE > 5%

---

## 12. Верификация

```bash
# Unit-тесты + покрытие
pytest tests/ -v --cov=src/weather_bot --cov-report=term-missing

# Integration-тесты (с реальными API-ключами в .env)
pytest tests/ -m integration -v

# Запуск бота
python -m weather_bot.main

# Smoke-тест: /weather London — должна прийти карточка погоды

# Тест отказоустойчивости
# Закомментировать OWM_API_KEY в .env → бот продолжает работать на 3 источниках

# Тест кэша
# Два одинаковых запроса подряд → второй отвечает < 50 мс (L1 cache hit)
```
