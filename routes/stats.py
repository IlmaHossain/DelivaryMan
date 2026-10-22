from datetime import datetime, date
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session,select,func
from models import Order, OrderStatus
from database import get_session

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
)
@router.get("/daily")
def dailySummary(
        summary_date:date |None=Query(default=None,description="Date for  summary"),
        session:Session=Depends(get_session),
):
    if not summary_date:
        summary_date = date.today()
    start_date = datetime.combine(summary_date, datetime.min.time())
    end_date = datetime.combine(summary_date, datetime.max.time())
    summary = {}
    total = 0
    for status in OrderStatus:
        count=session.exec(
            select(func.count(Order.id)).where(
                Order.created_at>=start_date,
                Order.created_at<=end_date,
                Order.status==status,

            )

        ).one()
        summary[status.value] = count
        total += count
    return {
        "date": summary_date.isoformat(),
        "total_orders": total,
        "by_status": summary,
    }
