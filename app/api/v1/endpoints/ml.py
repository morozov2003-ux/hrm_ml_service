from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import json

from app.database import get_db
from app.api.v1.endpoints.users import get_current_user
from app.models import User
from app.schemas import HRMInput, TaskResponse, PredictionResult
from app import crud
# Важно: импортируем саму задачу
from worker.tasks import run_hrm_prediction_task

router = APIRouter()


@router.post("/predict", response_model=TaskResponse)
def predict_hrm(payload: HRMInput, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Проверка баланса: кредиты + бонусы + бесплатные триалы
    # Используем getattr на случай, если в базе еще нет колонки
    total_balance = (getattr(current_user, 'cash_credits', 0) or 0) + \
                    (getattr(current_user, 'bonus_credits', 0) or 0) + \
                    (getattr(current_user, 'free_trials', 0) or 0)

    if total_balance < 1.0:
        raise HTTPException(status_code=402, detail="Insufficient credits.")

    # Исправляем ошибку UUID: обязательно оборачиваем в str()
    task_id = str(uuid.uuid4())

    # Создаем запись в БД через наш crud.py
    crud.create_prediction_task(db, task_id=task_id, owner_id=current_user.id)

    # Запускаем задачу в Celery
    run_hrm_prediction_task.delay(task_id, current_user.id, payload.temperatures, payload.fluorescence)

    return {"task_id": task_id, "status": "pending"}


@router.get("/result/{task_id}", response_model=PredictionResult)
def get_result(task_id: str, db: Session = Depends(get_db)):
    task = crud.get_prediction_by_task_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    res_data = json.loads(task.result) if task.result else {}

    return {
        "task_id": task.task_id,
        "status": task.status,
        "genotype": res_data.get("genotype"),
        "confidence": res_data.get("confidence"),
        "tm": res_data.get("tm"),
        "probabilities": res_data.get("probabilities"),
        "error": res_data.get("error")
    }