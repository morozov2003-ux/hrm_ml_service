# 🧬 HRM DNA Genotyping ML Service
### Облачный микросервисный комплекс автоматизированного генотипирования ДНК по кривым плавления высокого разрешения (High-Resolution Melting)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4-orange.svg)](https://scikit-learn.org/)
[![Docker Compose](https://img.shields.io/badge/docker--compose-v2-blue)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 О проекте

Данный проект представляет собой масштабируемый аналитический SaaS-сервис для автоматической интерпретации термодинамических профилей денатурации ДНК (HRM-кривых плавления). Сервис устраняет субъективность ручной разметки кривых оператором, автоматизирует физико-химическую предобработку зашумленных сигналов амплификатора и проводит высокоточное генотипирование на основе ансамблевых методов машинного обучения.

Проект разработан в предметной области автора (биоинформатика и молекулярная биофизика) с фокусом на экспресс-детекцию лекарственной устойчивости патогенов.

---

## 🔬 Научно-теоретическая база и предметная область

### 1. Архитектура машинного обучения для HRM
Концепция ML-пайплайна опирается на современные подходы к профилированию кривых денатурации:
> **Boussina, A., Langouche, L., Obirieze, A.C. et al.** *Machine learning based DNA melt curve profiling enables automated novel genotype detection.* **BMC Bioinformatics** 25, 185 (2024). [DOI: 10.1186/s12859-024-05747-0](https://doi.org/10.1186/s12859-024-05747-0)  
> *Исследование демонстрирует превосходство алгоритмов Random Forest и SVM при классификации кривых плавления после процедур нормировки.*

### 2. Математическое моделирование и синтез данных (Публикации автора)
Для обучения и тестирования моделей в условиях дефицита реальных выборок может быть применена авторская методология генерации синтетических профилей плавления с наложением экспоненциального фонового сигнала флуорофора и стохастического приборного шума:
> **Морозов Р. Р., Белов Ю. В., Буляница А. Л., Белов Д. А.** *Методика создания имитационных сигналов флуоресценции, формируемых при денатурации ДНК* // **Физические основы приборостроения**. – 2025. – Т. 14, № 4(58). – С. 104-110. – [DOI: 10.25210/jfop-2504-FSROIU](https://doi.org/10.25210/jfop-2504-FSROIU). – EDN: FSROIU.

### 3. Биологическая модель: Резистентность *Mycobacterium tuberculosis* к рифампицину
Ключевой прикладной задачей является детекция точечных мутаций (SNP) в гене **rpoB** (бета-субъединица РНК-полимеразы *M. tuberculosis*), мутации в так называемом «core-регионе» (RRDR) которого в 95%+ случаев обуславливают устойчивость к рифампицину (Rifampicin resistance):

* **Референс гена в NCBI:** [*Mycobacterium tuberculosis* rpoB (Gene ID: 888164)](https://www.ncbi.nlm.nih.gov/gene/888164)
* **Характеристика региона мутаций (RRDR):**  
  > *De Beenhouwer H. et al.* Rapid detection of rifampicin resistance in sputum and biopsy specimens from tuberculosis patients by PCR and line probe assay // *Tubercle and Lung Disease*. 1995. Vol. 76(5). P. 425–430.
* **Праймерная система для ампликонов:**  
  > *Valvatne H. et al.* Isoniazid and rifampicin resistance-associated mutations in Mycobacterium tuberculosis isolates from Yangon, Myanmar: implications for rapid molecular testing // *Journal of Antimicrobial Chemotherapy*. 2009. Vol. 64(4). P. 694–701.
* **HRM-анализ локуса:**  
  > *Yadav R. et al.* Rapid detection of rifampicin, isoniazid and streptomycin resistance in Mycobacterium tuberculosis clinical isolates by high-resolution melting curve analysis // *Journal of Applied Microbiology*. 2012. Vol. 113(4). P. 856–862.

---

## 🛠 Технологический стек

* **Язык программирования:** Python 3.10+
* **ML & Обработка сигналов:** Scikit-learn (Random Forest Classifier), NumPy, SciPy (фильтрация Савицкого-Голея, сплайн-интерполяция, аппроксимация касательных полиномами 2-го порядка)
* **Backend API:** FastAPI, Uvicorn, Pydantic v2
* **База данных & ORM:** PostgreSQL 15, SQLAlchemy 2.0 (пул транзакций, атомарные операции)
* **Асинхронные очереди (Task Queue):** Celery, Redis (изолированная неблокирующая обработка вычислений)
* **Безопасность:** JWT (JSON Web Tokens), PBKDF2-хеширование паролей, RBAC (Role-Based Access Control)
* **Frontend Dashboard:** Streamlit (визуализация $F(T)$ и $-dF/dT$, аналитика баланса, инференс)
* **Мониторинг:** Prometheus (`prometheus-fastapi-instrumentator`)
* **Контейнеризация:** Docker, Docker Compose

--
