from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from weather_bot.aggregator.aggregator import InsufficientSourcesError, WeatherAggregator
from weather_bot.bot.formatters import format_current_weather, format_forecast
from weather_bot.bot.keyboards import share_location_kb, weather_actions_kb
from weather_bot.storage.db import get_user_location, save_user_location
from weather_bot.utils.geo import CityNotFoundError, geocode

router = Router()
_aggregator = WeatherAggregator.from_settings()


class SetLocationStates(StatesGroup):
    waiting_for_location = State()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я бот прогноза погоды.\n\n"
        "Использую 4 источника и ML-коррекцию для точного прогноза.\n\n"
        "Команды:\n"
        "/weather <город> — текущая погода\n"
        "/forecast <город> [дни] — прогноз на 1–7 дней\n"
        "/set\\_location — сохранить геолокацию по умолчанию\n"
        "/sources — статус источников\n"
        "/help — справка",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 *Команды бота*\n\n"
        "/weather \\[город\\] — текущая погода\n"
        "/forecast \\[город\\] \\[дни\\] — прогноз на 1–7 дней \\(default 3\\)\n"
        "/set\\_location — сохранить геолокацию по умолчанию\n"
        "/sources — доступность и веса источников\n"
        "/help — эта справка",
        parse_mode="MarkdownV2",
    )


@router.message(Command("weather"))
async def cmd_weather(message: Message) -> None:
    assert message.text is not None
    args = message.text.split(maxsplit=1)
    city_arg = args[1].strip() if len(args) > 1 else None

    if not city_arg:
        assert message.from_user is not None
        loc = await get_user_location(message.from_user.id)
        if loc is None:
            await message.answer("Введите название города: /weather Москва")
            return
    else:
        try:
            loc = await geocode(city_arg)
        except CityNotFoundError:
            await message.answer(
                "Город не найден. Уточните название или отправьте геолокацию."
            )
            return

    city_display = loc.city or city_arg or f"{loc.lat:.2f},{loc.lon:.2f}"
    try:
        agg = await _aggregator.get_weather(loc.lat, loc.lon)
    except InsufficientSourcesError:
        await message.answer("⚠️ Недостаточно источников данных. Попробуйте позже.")
        return
    agg.location = loc
    agg.current.location = loc

    text = format_current_weather(agg)
    await message.answer(text, parse_mode="Markdown", reply_markup=weather_actions_kb(city_display))


@router.message(Command("forecast"))
async def cmd_forecast(message: Message) -> None:
    assert message.text is not None
    parts = message.text.split(maxsplit=2)

    city_arg: str | None = None
    days = 3

    if len(parts) >= 2:
        # Last token could be a number (days)
        if parts[-1].isdigit() and len(parts) >= 3:
            days = max(1, min(7, int(parts[-1])))
            city_arg = parts[1]
        else:
            city_arg = " ".join(parts[1:])

    if not city_arg:
        assert message.from_user is not None
        loc = await get_user_location(message.from_user.id)
        if loc is None:
            await message.answer("Введите город: /forecast Москва 3")
            return
    else:
        try:
            loc = await geocode(city_arg)
        except CityNotFoundError:
            await message.answer(
                "Город не найден. Уточните название или отправьте геолокацию."
            )
            return

    city_display = loc.city or city_arg or f"{loc.lat:.2f},{loc.lon:.2f}"
    try:
        agg = await _aggregator.get_forecast(loc.lat, loc.lon, days)
    except InsufficientSourcesError:
        await message.answer("⚠️ Недостаточно источников данных. Попробуйте позже.")
        return
    text = format_forecast(agg.forecast, city_display)
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("set_location"))
async def cmd_set_location(message: Message, state: FSMContext) -> None:
    await state.set_state(SetLocationStates.waiting_for_location)
    await message.answer(
        "📍 Отправьте вашу геолокацию:",
        reply_markup=share_location_kb(),
    )


@router.message(SetLocationStates.waiting_for_location, F.location)
async def handle_location(message: Message, state: FSMContext) -> None:
    assert message.location is not None
    assert message.from_user is not None

    lat = message.location.latitude
    lon = message.location.longitude

    try:
        loc = await geocode(f"{lat},{lon}")
    except CityNotFoundError:
        from weather_bot.models.weather import Location
        loc = Location(lat=lat, lon=lon)

    await save_user_location(message.from_user.id, loc)
    await state.clear()

    city_str = f"{loc.city}" if loc.city else f"{lat:.4f}, {lon:.4f}"
    await message.answer(
        f"✅ Сохранено: {city_str} ({lat:.2f}, {lon:.2f})",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("sources"))
async def cmd_sources(message: Message) -> None:
    health = await _aggregator.health_check()
    source_names = {"openweathermap": "OWM", "weatherapi": "WA", "accuweather": "ACW", "open_meteo": "OM"}
    weights = {"open_meteo": 0.35, "openweathermap": 0.30, "weatherapi": 0.25, "accuweather": 0.10}

    lines = ["📡 *Статус источников*\n"]
    for src, abbr in source_names.items():
        status = "✓" if health.get(src) else "✗"
        w = weights.get(src, 0.0)
        lines.append(f"{abbr} {status}  вес: {w:.2f}")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.callback_query(F.data.startswith("forecast:"))
async def cb_forecast(callback: CallbackQuery) -> None:
    assert callback.data is not None
    _, days_str, city = callback.data.split(":", 2)
    days = int(days_str)

    try:
        loc = await geocode(city)
    except CityNotFoundError:
        await callback.answer("Город не найден", show_alert=True)
        return

    agg = await _aggregator.get_forecast(loc.lat, loc.lon, days)
    text = format_forecast(agg.forecast, city)
    assert callback.message is not None
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("refresh:"))
async def cb_refresh(callback: CallbackQuery) -> None:
    assert callback.data is not None
    city = callback.data.split(":", 1)[1]

    try:
        loc = await geocode(city)
    except CityNotFoundError:
        await callback.answer("Город не найден", show_alert=True)
        return

    agg = await _aggregator.get_weather(loc.lat, loc.lon)
    agg.location = loc
    agg.current.location = loc
    text = format_current_weather(agg)
    assert callback.message is not None
    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=weather_actions_kb(city)
    )
    await callback.answer("Обновлено")
