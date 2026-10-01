from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User, PromoCode, UserPromoActivation, Transaction, Prediction
from app.core.security import get_password_hash


# --- Юзеры ---
def get_user_by_email(db: Session, email: str):
    return db.execute(select(User).where(User.email == email)).scalars().first()


def create_user(db: Session, user_in) -> User:
    hashed_pwd = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        cash_credits=0.0,
        bonus_credits=0.0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Биллинг ---
def process_charge(db: Session, user_id: int, cost: float = 1.0) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False

    total_balance = user.bonus_credits + user.cash_credits
    if total_balance < cost:
        return False

    if user.bonus_credits >= cost:
        user.bonus_credits -= cost
    else:
        remaining = cost - user.bonus_credits
        user.bonus_credits = 0.0
        user.cash_credits -= remaining

    txn = Transaction(user_id=user_id, amount=-cost, type="prediction_charge")
    db.add(txn)
    db.commit()
    return True


def activate_promocode(db: Session, user_id: int, code_str: str) -> str:
    user = db.get(User, user_id)
    promo = db.execute(select(PromoCode).where(PromoCode.code == code_str)).scalars().first()

    if not promo or not promo.is_active:
        return "Промокод не существует или не активен"

    if promo.activations_count >= promo.max_activations:
        return "Лимит активаций промокода исчерпан"

    already_activated = db.execute(
        select(UserPromoActivation)
        .where(UserPromoActivation.user_id == user_id, UserPromoActivation.promo_id == promo.id)
    ).scalars().first()

    if already_activated:
        return "Вы уже активировали данный промокод"

    user.bonus_credits += promo.value
    promo.activations_count += 1

    activation = UserPromoActivation(user_id=user_id, promo_id=promo.id)
    txn = Transaction(user_id=user_id, amount=promo.value, type="promo_bonus")

    db.add(activation)
    db.add(txn)
    db.commit()
    return "success"


# --- Задачи на предсказания ---
def create_prediction_task(db: Session, task_id: str, owner_id: int) -> Prediction:
    task = Prediction(task_id=task_id, status="pending", owner_id=owner_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_prediction_by_task_id(db: Session, task_id: str) -> Prediction:
    return db.execute(select(Prediction).where(Prediction.task_id == task_id)).scalars().first()