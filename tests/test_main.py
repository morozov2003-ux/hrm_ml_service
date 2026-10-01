import pytest
import numpy as np
from app.ml.data_processor import HRMProcessor
from app.ml.model_handler import HRMModelHandler


def test_hrm_processor_normalization():
    processor = HRMProcessor()
    # Эмулируем кривую плавления
    temps = np.linspace(70, 90, 100)
    # Сигмоида с линейным фоном
    fluo = 1.0 / (1.0 + np.exp((temps - 80) / 0.5)) + (0.5 - 0.002 * temps)

    t_clean, f_norm = processor.remove_background_and_normalize(temps, fluo)

    assert len(t_clean) == 100
    assert np.isclose(np.max(f_norm), 1.0)
    assert np.isclose(np.min(f_norm), 0.0)


def test_model_handler_prediction():
    handler = HRMModelHandler()
    handler.load_model()  # Сгенерирует данные и обучит RandomForest

    temps = np.linspace(70, 90, 100)
    # Генерируем выраженный WT (дикий тип) с Tm = 80.0
    fluo = 1.0 / (1.0 + np.exp((temps - 80.0) / 0.5)) + 0.1

    prediction = handler.predict(temps, fluo)

    assert "genotype" in prediction
    assert "confidence" in prediction
    assert "tm" in prediction
    assert prediction["confidence"] > 0.5