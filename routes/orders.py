from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException,Query
from sqlmodel import Session, select

from database import get_session
from models import Order, OrderCreate, OrderUpdate, StatusLog, OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=Order)
def create_order(order: OrderCreate, session: Session = Depends(get_session)):
    db_order=Order(**order.model_dump())
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order

@router.get("/", response_model=list[Order])
def list_orders(
        status:OrderStatus |  None=Query(default=None,description="Filter by order status"),
        created_date:date | None =Query(default=None,description="Filter by order created date"),
        skip:int =Query(default=0,ge=0),
        limit:int =Query(default=20,ge=1,le=100),
        session: Session = Depends(get_session),
):
    query=select(Order)
    if status:
        query=query.where(Order.status == status)
    if created_date:
        start_date=datetime.combine(created_date,datetime.min.time())
        end_date=datetime.combine(created_date,datetime.max.time())
        query=query.where(Order.created_at>=start_date, Order.created_at<=end_date)
    query=query.offset(skip).limit(limit)
    return session.exec(query).all()

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/{order_id}", response_model=Order)
def update_order(order_id: int, update: OrderUpdate, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    changes = update.model_dump(exclude_unset=True, exclude_none=True)
    if "status" in changes and changes["status"] != order.status:
        session.add(StatusLog(
            order_id=order.id,
            old_status=order.status.value,
            new_status=changes["status"].value,
        ))
    for field, value in changes.items():
        setattr(order, field, value)
    order.updated_at = datetime.now(timezone.utc)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order

@router.get("/{order_id}/history", response_model=list[StatusLog])
def get_order_history(order_id: int, session: Session = Depends(get_session)):
    if not session.get(Order, order_id):
        raise HTTPException(status_code=404, detail="Order not found")
    query = select(StatusLog).where(StatusLog.order_id == order_id).order_by(StatusLog.changed_at)
    return session.exec(query).all()

@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for log in session.exec(select(StatusLog).where(StatusLog.order_id == order_id)).all():
        session.delete(log)
    session.delete(order)
    session.commit()

