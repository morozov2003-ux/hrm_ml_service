import math
import numpy as np
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d

# --- Константы для типов кривых ---
CURVE_TYPE_DECREASING = "decreasing"  # Прямое плавление (интеркалятор, F падает)
CURVE_TYPE_INCREASING = "increasing"  # Прямое плавление (гаситель/зонд, F растет)
CURVE_TYPE_REVERSE_DECREASING = "reverse_decreasing"  # Охлаждение/отжиг (F падает)
CURVE_TYPE_REVERSE_INCREASING = "reverse_increasing"  # Охлаждение/отжиг (F растет)


def quadratic_polynomial(x, a, b, c):
    """Квадратичный полином: ax^2 + bx + c"""
    return a * x ** 2 + b * x + c


def derivative_quadratic(x, a, b):
    """Производная квадратичного полинома: 2ax + b"""
    return 2 * a * x + b


def find_min_excluding_ends(arr):
    """Поиск индекса минимума, исключая крайние элементы."""
    if len(arr) <= 2:
        return -1
    inner_arr = arr[1:-1]
    if len(inner_arr) == 0:
        return -1
    return np.argmin(inner_arr) + 1


def calculate_r_squared(y_true, y_pred):
    if len(y_true) == 0 or len(y_pred) == 0:
        return np.nan
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - (ss_res / ss_tot)


def calculate_penalty_and_score(interval_length, start_offset_towards_expansion, max_possible_offset,
                                penalty_weight=0.01, bonus_weight=0.005):
    penalty = penalty_weight * interval_length
    normalized_offset = max_possible_offset if max_possible_offset > 0 else 1e-6
    bonus = bonus_weight * (
                start_offset_towards_expansion / normalized_offset) if start_offset_towards_expansion > 0 else 0
    return penalty - bonus


class HRMProcessor:
    """
    Промышленный процессор биофизических HRM-кривых.
    Включает автоопределение типа сигнала, фильтрацию Савицкого-Голея,
    поиск оптимальных интервалов по второй производной и нормализацию по касательным L1/L2.
    """

    def __init__(self, target_temp_grid=None):
        if target_temp_grid is None:
            self.target_temp_grid = np.linspace(70.0, 90.0, 200)
        else:
            self.target_temp_grid = target_temp_grid

    def detect_and_standardize_curve(self, temperatures, fluorescence):
        """
        Определяет тип кривой (прямая/обратная, интеркалятор/гаситель)
        и приводит её к каноническому виду:
        T монотонно возрастает, F монотонно спадает в зоне плавления.
        """
        temp = np.array(temperatures, dtype=float)
        fluo = np.array(fluorescence, dtype=float)

        # 1. Проверяем направление изменения температуры
        is_cooling = temp[0] > temp[-1]
        if is_cooling:
            # Разворачиваем, чтобы температура всегда росла
            idx_sort = np.argsort(temp)
            temp = temp[idx_sort]
            fluo = fluo[idx_sort]

        # 2. Проверяем тренд флуоресценции (начало vs конец)
        start_f = np.mean(fluo[:max(3, int(len(fluo) * 0.1))])
        end_f = np.mean(fluo[-max(3, int(len(fluo) * 0.1)):])
        is_increasing = end_f > start_f

        # Определение типа кривой
        if not is_cooling and not is_increasing:
            curve_type = CURVE_TYPE_DECREASING
        elif not is_cooling and is_increasing:
            curve_type = CURVE_TYPE_INCREASING
        elif is_cooling and not is_increasing:
            curve_type = CURVE_TYPE_REVERSE_DECREASING
        else:
            curve_type = CURVE_TYPE_REVERSE_INCREASING

        # Приведение к стандартному виду (спад при росте T)
        if is_increasing:
            # Инвертируем флуоресценцию для унификации математики
            fluo = np.max(fluo) + np.min(fluo) - fluo

        return temp, fluo, curve_type

    def calculated_savgol_filter(self, temperature_input, fluorescence_input):
        """Фильтрация шума алгоритмом Савицкого-Голея с адаптивным окном."""
        temp_step = temperature_input[1] - temperature_input[0] if len(temperature_input) > 1 else 0.5
        rec_window = 1.0 / abs(temp_step) + 1
        window_length = int(rec_window * 2 + 1)
        if window_length % 2 == 0:
            window_length += 1
        if window_length < 5:
            window_length = 5
        if window_length >= len(fluorescence_input):
            window_length = len(fluorescence_input) - 1 if (len(fluorescence_input) - 1) % 2 != 0 else len(
                fluorescence_input) - 2

        poly_order = 2
        return savgol_filter(fluorescence_input, max(3, window_length), poly_order)

    def find_optimal_interval(self, temperature_data, derivative_data, initial_start_temp, initial_end_temp,
                              min_temp_step, max_expansion_steps, search_direction,
                              penalty_weight=0.01, bonus_weight=0.005, min_interval_length=1.5, sampling_rate=0.05):
        """
        Поиск оптимального интервала аппроксимации квадратичным полиномом и точки касания.
        """
        best_r_squared = -np.inf
        best_score = np.inf
        best_tangent_temp = np.nan
        original_start_point_temp = initial_start_temp
        max_offset_for_scaling = max_expansion_steps * min_temp_step

        for i in range(max_expansion_steps + 1):
            current_expansion = i * min_temp_step
            configs = [
                (initial_start_temp, initial_end_temp + search_direction * current_expansion, 0),
                (initial_start_temp + search_direction * current_expansion, initial_end_temp,
                 (initial_start_temp + search_direction * current_expansion) - original_start_point_temp)
            ]

            for start_t, end_t, offset_candidate in configs:
                t1, t2 = sorted([start_t, end_t])
                indices = np.where((temperature_data >= t1) & (temperature_data <= t2))[0]
                if len(indices) < 4:
                    continue

                curr_temps = temperature_data[indices]
                curr_derivs = derivative_data[indices]

                try:
                    params, _ = curve_fit(quadratic_polynomial, curr_temps, curr_derivs)
                    a, b, c = params
                    approx = quadratic_polynomial(curr_temps, a, b, c)
                    r2 = calculate_r_squared(curr_derivs, approx)
                    interval_len = t2 - t1
                    if interval_len < min_interval_length:
                        continue

                    offset_bonus = abs(offset_candidate)
                    score = calculate_penalty_and_score(interval_len, offset_bonus, max_offset_for_scaling,
                                                        penalty_weight, bonus_weight)

                    dense_temps = np.linspace(t1, t2, 50)
                    deriv_vals = derivative_quadratic(dense_temps, a, b)
                    idx_min = find_min_excluding_ends(deriv_vals)

                    if idx_min != -1:
                        tangent_t = dense_temps[idx_min]
                        if r2 > best_r_squared or (np.isclose(r2, best_r_squared, atol=1e-3) and score < best_score):
                            best_r_squared = r2
                            best_score = score
                            best_tangent_temp = tangent_t
                except Exception:
                    continue

        return best_tangent_temp

    def normalize_by_tangents(self, temp, fluo, t1, t2, first_grad):
        """
        Нормализация кривой флуоресценции по двум базовым касательным L1 и L2.
        """
        idx1 = np.argmin(np.abs(temp - t1))
        idx2 = np.argmin(np.abs(temp - t2))

        slope1 = first_grad[idx1]
        slope2 = first_grad[idx2]
        y1 = fluo[idx1]
        y2 = fluo[idx2]

        L1 = slope1 * (temp - t1) + y1
        L2 = slope2 * (temp - t2) + y2

        denom = L2 - L1
        denom[np.abs(denom) < 1e-5] = 1e-5
        fluo_norm = (fluo - L1) / denom

        # Обрезаем возможные выбросы за пределы [0, 1]
        return np.clip(fluo_norm, 0.0, 1.0)

    def extract_features(self, temperatures, fluorescence):
        """
        Главный метод препроцессинга для подачи в ML:
        1. Автоопределение типа кривой и канонизация
        2. Фильтрация Савицкого-Голея
        3. Поиск пиков второй производной и расчет T1, T2
        4. Нормализация по касательным (с fallback при сбоях)
        5. Интерполяция на фиксированную температурную сетку
        """
        # 1. Стандартизация
        temp, fluo, curve_type = self.detect_and_standardize_curve(temperatures, fluorescence)

        # 2. Фильтрация и производные
        fluo_filt = self.calculated_savgol_filter(temp, fluo)
        first_grad = np.gradient(fluo_filt, temp)
        second_grad = np.gradient(first_grad, temp)
        third_grad = np.gradient(second_grad, temp)

        temp_step = np.mean(np.diff(temp)) if len(temp) > 1 else 0.2

        # 3. Поиск экстремумов второй производной
        max_indices = np.where(np.diff(np.sign(third_grad)) < 0)[0]
        min_indices = np.where(np.diff(np.sign(third_grad)) > 0)[0]

        idx_max_2nd = max_indices[np.argmax(second_grad[max_indices])] if len(max_indices) > 0 else np.argmax(
            second_grad)
        idx_min_2nd = min_indices[np.argmin(second_grad[min_indices])] if len(min_indices) > 0 else np.argmin(
            second_grad)

        temp_max_2 = temp[idx_max_2nd]
        temp_min_2 = temp[idx_min_2nd]

        # 4. Поиск касательных точек T1 и T2
        t2_algo = self.find_optimal_interval(temp, first_grad, temp_max_2, temp_max_2 + 2.0,
                                             min_temp_step=temp_step, max_expansion_steps=12, search_direction=1)
        t1_algo = self.find_optimal_interval(temp, first_grad, temp_min_2 - 2.0, temp_min_2,
                                             min_temp_step=temp_step, max_expansion_steps=12, search_direction=-1)

        # Fallback: если аппроксимация не сошлась, берем точки перегиба второй производной
        if np.isnan(t1_algo):
            t1_algo = temp[int(len(temp) * 0.15)]
        if np.isnan(t2_algo):
            t2_algo = temp[int(len(temp) * 0.85)]

        # 5. Нормализация по касательным L1/L2
        fluo_norm = self.normalize_by_tangents(temp, fluo_filt, t1_algo, t2_algo, first_grad)

        # 6. Интерполяция на фиксированную сетку (200 точек)
        f_interp = interp1d(temp, fluo_norm, kind='linear', fill_value="extrapolate")
        f_grid = f_interp(self.target_temp_grid)
        f_grid = np.clip(f_grid, 0.0, 1.0)

        # 7. Численная производная -dF/dT для поиска формы пика плавления
        dT = self.target_temp_grid[1] - self.target_temp_grid[0]
        df_grid = -np.gradient(f_grid, dT)

        # Итоговый вектор признаков: 200 точек кривой + 200 точек производной = 400 фичей
        features = np.concatenate([f_grid, df_grid])

        info = {
            "curve_type": curve_type,
            "t1": float(round(t1_algo, 2)),
            "t2": float(round(t2_algo, 2)),
            "tm_estimate": float(round(self.target_temp_grid[np.argmax(df_grid)], 2))
        }
        return features, info