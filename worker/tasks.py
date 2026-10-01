import json
from worker.celery_app import celery_app
from app.database import SessionLocal
from app import crud
from app.ml.model_handler import HRMModelHandler

model_handler = HRMModelHandler()
model_handler.load_model()  # Модель загружается при инициализации воркера


@celery_app.task(name="run_hrm_prediction_task")
def run_hrm_prediction_task(task_id: str, user_id: int, temperatures: list, fluorescence: list):
    db = SessionLocal()
    task = crud.get_prediction_by_task_id(db, task_id)
    if not task:
        db.close()
        return

    task.status = "processing"
    db.commit()

    try:
        # 1. Запуск ML предсказания и препроцессинга
        pred_res = model_handler.predict(temperatures, fluorescence)

        # 2. Попытка списания кредита за успешное вычисление
        success_billing = crud.process_charge(db, user_id=user_id, cost=1.0)

        if success_billing:
            task.status = "completed"
            task.result = json.dumps(pred_res)
        else:
            task.status = "failed"
            task.result = json.dumps({"error": "Failed billing: Insufficient credits at execution time."})

    except Exception as e:
        task.status = "failed"
        task.result = json.dumps({"error": str(e)})

    db.commit()
    db.close()