from datetime import datetime, timezone

import pytest

from weather_bot.forecast.ensemble import compute_confidence, majority_condition, weighted_average
from weather_bot.forecast.model import CorrectionModel
from weather_bot.models.weather import Location, WeatherCondition, WeatherReading


def _reading(source: str, temp: float, condition: WeatherCondition = WeatherCondition.CLEAR) -> WeatherReading:
    return WeatherReading(
        source=source,
        location=Location(lat=0, lon=0),
        fetched_at=datetime.now(timezone.utc),
        temperature_c=temp,
        feels_like_c=temp - 1,
        humidity_pct=60,
        pressure_hpa=1013.0,
        wind_speed_ms=4.0,
        wind_direction_deg=180,
        condition=condition,
        precipitation_mm=0.0,
        cloud_cover_pct=10,
    )


WEIGHTS = {"open_meteo": 0.35, "openweathermap": 0.30, "weatherapi": 0.25, "accuweather": 0.10}


def test_weighted_average_temperature():
    readings = [
        _reading("open_meteo", 10.0),
        _reading("openweathermap", 12.0),
        _reading("weatherapi", 11.0),
        _reading("accuweather", 13.0),
    ]
    result = weighted_average(readings, WEIGHTS)
    expected = 10.0 * 0.35 + 12.0 * 0.30 + 11.0 * 0.25 + 13.0 * 0.10
    assert abs(result["temperature_c"] - expected) < 0.01


def test_majority_condition_rain():
    readings = [
        _reading("open_meteo", 15.0, WeatherCondition.RAIN),
        _reading("openweathermap", 14.0, WeatherCondition.RAIN),
        _reading("weatherapi", 16.0, WeatherCondition.RAIN),
        _reading("accuweather", 15.5, WeatherCondition.CLOUDY),
    ]
    assert majority_condition(readings, WEIGHTS) == WeatherCondition.RAIN


def test_confidence_high_when_sources_agree():
    readings = [_reading(s, 15.0 + i * 0.1) for i, s in enumerate(["open_meteo", "openweathermap", "weatherapi"])]
    conf = compute_confidence(readings)
    assert conf > 0.9


def test_confidence_low_when_sources_disagree():
    readings = [
        _reading("open_meteo", 10.0),
        _reading("openweathermap", 16.0),
        _reading("weatherapi", 20.0),
    ]
    conf = compute_confidence(readings)
    assert conf < 0.5


def test_confidence_single_source():
    readings = [_reading("open_meteo", 15.0)]
    assert compute_confidence(readings) == 1.0


def test_prediction_in_valid_range():
    model = CorrectionModel()
    result = model.correct_temperature(15.0, [15.0] * 11)
    assert -60.0 <= result <= 60.0


def test_ml_correction_applied():
    model = CorrectionModel()
    model._model = type("M", (), {"predict": lambda self, x: [2.5]})()
    result = model.correct_temperature(15.0, [])
    assert abs(result - 17.5) < 0.01


def test_correction_clamped():
    model = CorrectionModel()
    model._model = type("M", (), {"predict": lambda self, x: [100.0]})()
    assert model.correct_temperature(55.0, []) == 60.0
    model._model = type("M", (), {"predict": lambda self, x: [-100.0]})()
    assert model.correct_temperature(-55.0, []) == -60.0
