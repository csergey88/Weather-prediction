from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def weather_actions_kb(city: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Прогноз 3д", callback_data=f"forecast:3:{city}"),
        InlineKeyboardButton(text="📅 Прогноз 7д", callback_data=f"forecast:7:{city}"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh:{city}"),
    )
    return builder.as_markup()


def share_location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
