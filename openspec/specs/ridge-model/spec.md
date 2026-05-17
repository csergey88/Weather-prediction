## ADDED Requirements

### Requirement: Ridge baseline с нулевой дельтой
`forecast/model.py` SHALL реализовать `CorrectionModel` с методом `predict(features) -> float`, возвращающим 0.0 до обучения.

#### Scenario: Нулевая коррекция без модели
- **WHEN** модель не обучена (файл joblib отсутствует)
- **THEN** `predict()` возвращает 0.0

#### Scenario: Коррекция применяется к ensemble температуре
- **WHEN** ensemble_temp = 15.0, model.predict() = 0.5
- **THEN** corrected_temp = 15.5

### Requirement: Результат в допустимом диапазоне
Скорректированная температура SHALL оставаться в диапазоне −60..+60°C.

#### Scenario: Clamp экстремального значения
- **WHEN** ensemble_temp + delta выходит за −60..+60
- **THEN** результат зажимается до границ диапазона
