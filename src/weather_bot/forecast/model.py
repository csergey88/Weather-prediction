import os
from typing import Any


class CorrectionModel:
    _model: Any = None

    def __init__(self, model_path: str | None = None) -> None:
        if model_path and os.path.exists(model_path):
            try:
                import joblib
                self._model = joblib.load(model_path)
            except Exception:
                self._model = None

    def predict(self, features: list[float]) -> float:
        if self._model is None:
            return 0.0
        try:
            delta = float(self._model.predict([features])[0])
        except Exception:
            return 0.0
        return delta

    def correct_temperature(self, ensemble_temp: float, features: list[float]) -> float:
        corrected = ensemble_temp + self.predict(features)
        return max(-60.0, min(60.0, corrected))
