from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String, default="user")  # 'user' or 'admin'

    # Кредитный баланс
    cash_credits = Column(Float, default=0.0)  # Купленные кредиты
    bonus_credits = Column(Float, default=0.0)  # Бонусные промо-кредиты

    predictions = relationship("Prediction", back_populates="owner")
    transactions = relationship("Transaction", back_populates="user")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result = Column(String, nullable=True)  # JSON string с ответом
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="predictions")


class PromoCode(Base):
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    value = Column(Float, nullable=False)  # Сколько бонусных кредитов дает
    is_active = Column(Boolean, default=True)
    max_activations = Column(Integer, default=100)
    activations_count = Column(Integer, default=0)


class UserPromoActivation(Base):
    __tablename__ = "user_promo_activations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    promo_id = Column(Integer, ForeignKey("promocodes.id"))
    activated_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Положительное или отрицательное значение
    type = Column(String, nullable=False)  # 'top_up', 'prediction_charge', 'promo_bonus'
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")