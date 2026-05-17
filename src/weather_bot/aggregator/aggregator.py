import asyncio
import logging
from datetime import datetime, timezone

from weather_bot.aggregator.weights import normalize_weights
from weather_bot.forecast.ensemble import compute_confidence, majority_condition, weighted_average
from weather_bot.forecast.model import CorrectionModel
from weather_bot.models.forecast import AggregatedWeather, ForecastPoint
from weather_bot.models.weather import Location, WeatherReading
from weather_bot.sources.base import WeatherSource

logger = logging.getLogger(__name__)


class InsufficientSourcesError(Exception):
    pass


class WeatherAggregator:
    def __init__(self, sources: list[WeatherSource], min_sources: int = 2, model_path: str | None = None) -> None:
        self._sources = sources
        self._min_sources = min_sources
        self._model = CorrectionModel(model_path)

    @classmethod
    def from_settings(cls) -> "WeatherAggregator":
        from weather_bot.config import settings
        sources: list[WeatherSource] = []

        if "open_meteo" in settings.ENABLED_SOURCES:
            from weather_bot.sources.open_meteo import OpenMeteoSource
            sources.append(OpenMeteoSource())

        if "openweathermap" in settings.ENABLED_SOURCES and settings.OWM_API_KEY:
            from weather_bot.sources.openweathermap import OpenWeatherMapSource
            sources.append(OpenWeatherMapSource(settings.OWM_API_KEY))

        if "weatherapi" in settings.ENABLED_SOURCES and settings.WEATHERAPI_KEY:
            from weather_bot.sources.weatherapi import WeatherAPISource
            sources.append(WeatherAPISource(settings.WEATHERAPI_KEY))

        if "accuweather" in settings.ENABLED_SOURCES and settings.ACCUWEATHER_KEY:
            from weather_bot.sources.accuweather import AccuWeatherSource
            sources.append(AccuWeatherSource(settings.ACCUWEATHER_KEY))

        model_path = settings.MODEL_PATH if settings.MODEL_PATH else None
        return cls(sources, min_sources=settings.MIN_SOURCES, model_path=model_path)

    async def get_weather(self, lat: float, lon: float) -> AggregatedWeather:
        results = await asyncio.gather(
            *[s.get_current(lat, lon) for s in self._sources],
            return_exceptions=True,
        )

        successful: list[WeatherReading] = []
        for source, result in zip(self._sources, results):
            if isinstance(result, WeatherReading):
                successful.append(result)
            else:
                logger.warning("Source %s failed: %s", source.name, result)

        if len(successful) < self._min_sources:
            raise InsufficientSourcesError(
                f"Only {len(successful)} sources available, need {self._min_sources}"
            )

        active_names = [r.source for r in successful]
        weights = normalize_weights(active_names)
        confidence = compute_confidence(successful, threshold=3.0)
        averaged = weighted_average(successful, weights)
        condition = majority_condition(successful, weights)

        # ML temperature correction
        features = self._build_features(successful, lat, lon)
        corrected_temp = self._model.correct_temperature(averaged["temperature_c"], features)

        loc = Location(lat=lat, lon=lon)
        now = datetime.now(timezone.utc)

        current = WeatherReading(
            source="ensemble",
            location=loc,
            fetched_at=now,
            temperature_c=corrected_temp,
            feels_like_c=averaged["feels_like_c"],
            humidity_pct=int(averaged["humidity_pct"]),
            pressure_hpa=averaged["pressure_hpa"],
            wind_speed_ms=averaged["wind_speed_ms"],
            wind_direction_deg=int(averaged["wind_direction_deg"]),
            visibility_km=averaged.get("visibility_km"),
            condition=condition,
            precipitation_mm=averaged["precipitation_mm"],
            cloud_cover_pct=int(averaged["cloud_cover_pct"]),
        )

        return AggregatedWeather(
            location=loc,
            aggregated_at=now,
            readings=successful,
            current=current,
            forecast=[],
            source_weights=weights,
            ensemble_version=f"v{self._model._model is not None and '2_lgbm' or '1_ridge'}",
        )

    async def get_forecast(self, lat: float, lon: float, days: int) -> AggregatedWeather:
        agg = await self.get_weather(lat, lon)

        results = await asyncio.gather(
            *[s.get_forecast(lat, lon, days) for s in self._sources],
            return_exceptions=True,
        )

        # Collect successful forecasts per source
        source_forecasts: list[tuple[str, list[ForecastPoint]]] = []
        weights = agg.source_weights
        for source, result in zip(self._sources, results):
            if isinstance(result, list) and result:
                source_forecasts.append((source.name, result))
            else:
                logger.warning("Forecast source %s failed: %s", source.name, result)

        if not source_forecasts:
            return agg

        # Aggregate per day index
        max_days = min(days, max(len(pts) for _, pts in source_forecasts))
        forecast: list[ForecastPoint] = []

        for i in range(max_days):
            day_points = [
                (name, pts[i])
                for name, pts in source_forecasts
                if i < len(pts) and name in weights
            ]
            if not day_points:
                continue

            active_w = normalize_weights([name for name, _ in day_points])
            temps = [fp.temperature_c for _, fp in day_points]
            conf = compute_confidence(
                [WeatherReading(
                    source=name, location=agg.location, fetched_at=agg.aggregated_at,
                    temperature_c=fp.temperature_c, feels_like_c=fp.temperature_c,
                    humidity_pct=50, pressure_hpa=1013.0, wind_speed_ms=fp.wind_speed_ms,
                    wind_direction_deg=0, condition=fp.condition,
                ) for name, fp in day_points]
            )

            # weighted averages
            total_w = sum(active_w[name] for name, _ in day_points)
            avg_temp = sum(fp.temperature_c * active_w[name] for name, fp in day_points) / total_w
            avg_t_min = sum(fp.temperature_min_c * active_w[name] for name, fp in day_points) / total_w
            avg_t_max = sum(fp.temperature_max_c * active_w[name] for name, fp in day_points) / total_w
            avg_precip_pct = int(sum(fp.precipitation_probability_pct * active_w[name] for name, fp in day_points) / total_w)
            avg_precip_mm = sum(fp.precipitation_mm * active_w[name] for name, fp in day_points) / total_w
            avg_wind = sum(fp.wind_speed_ms * active_w[name] for name, fp in day_points) / total_w

            # majority condition
            from collections import defaultdict
            cond_scores: dict = defaultdict(float)
            for name, fp in day_points:
                cond_scores[fp.condition] += active_w[name]
            best_condition = max(cond_scores, key=lambda c: cond_scores[c])

            forecast.append(ForecastPoint(
                target_dt=day_points[0][1].target_dt,
                temperature_c=avg_temp,
                temperature_min_c=avg_t_min,
                temperature_max_c=avg_t_max,
                precipitation_probability_pct=avg_precip_pct,
                precipitation_mm=avg_precip_mm,
                condition=best_condition,
                wind_speed_ms=avg_wind,
                confidence=conf,
            ))

        agg.forecast = forecast
        return agg

    async def health_check(self) -> dict[str, bool]:
        results = await asyncio.gather(
            *[s.health_check() for s in self._sources],
            return_exceptions=True,
        )
        return {
            source.name: isinstance(result, bool) and result
            for source, result in zip(self._sources, results)
        }

    def _build_features(self, readings: list[WeatherReading], lat: float, lon: float) -> list[float]:
        now = datetime.now(timezone.utc)
        by_source = {r.source: r for r in readings}
        return [
            by_source.get("openweathermap", readings[0]).temperature_c,
            by_source.get("weatherapi", readings[0]).temperature_c,
            by_source.get("accuweather", readings[0]).temperature_c,
            by_source.get("open_meteo", readings[0]).temperature_c,
            by_source.get("openweathermap", readings[0]).pressure_hpa,
            by_source.get("open_meteo", readings[0]).pressure_hpa,
            sum(r.humidity_pct for r in readings) / len(readings),
            float(now.hour),
            float(now.month),
            lat,
            lon,
        ]
