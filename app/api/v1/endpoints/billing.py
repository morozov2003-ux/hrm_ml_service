from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.v1.endpoints.users import get_current_user
from app.models import User, Transaction
from app.schemas import PromoActivate, TopUp
from app import crud

router = APIRouter()


@router.post("/promo/activate")
def activate_promo(schema: PromoActivate, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    result = crud.activate_promocode(db, current_user.id, schema.code)
    if result != "success":
        raise HTTPException(status_code=400, detail=result)
    return {"message": "Promo code activated successfully"}


@router.post("/top-up")
def top_up_balance(schema: TopUp, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Учебная заглушка (Mock-интеграция) платежного шлюза.
    """
    if schema.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    current_user.cash_credits += schema.amount
    txn = Transaction(user_id=current_user.id, amount=schema.amount, type="top_up")
    db.add(txn)
    db.commit()
    return {"message": "Balance topped up", "new_balance": current_user.cash_credits}