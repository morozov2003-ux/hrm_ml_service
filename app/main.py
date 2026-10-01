from fastapi import FastAPI
from app.core.config import settings
from app.api.routers import api_router
from app.database import engine
from app.models import Base, PromoCode
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

# Автоматическое создание всех таблиц при запуске в БД
Base.metadata.create_all(bind=engine)

# Наполнение базовым демо-промокодом
db = Session(bind=engine)
if not db.query(PromoCode).filter(PromoCode.code == "WELCOME100").first():
    promo = PromoCode(code="WELCOME100", value=100.0, is_active=True, max_activations=1000)
    db.add(promo)
    db.commit()
db.close()

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Настройка Prometheus-метрик
Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to DNA HRM Genotyping ML Service API!"}