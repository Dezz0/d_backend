from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app import models, schemas


router = APIRouter(prefix="/outdoor-temperature", tags=["Outdoor Temperature"])

"""
Эндпоинт для приема данных от Arduino по температуре периметра
Пример:
{
  "temperatures": [
    { "side": "north", "value": -5.2 },
    { "side": "south", "value": -3.8 },
    { "side": "west",  "value": -4.1 },
    { "side": "east",  "value": -5.0 }
  ]
}
"""
@router.post("/", response_model=schemas.OutdoorTemperatureResponse)
def receive_outdoor_temperature(
    data: schemas.OutdoorTemperatureCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if len(data.temperatures) != 4:
        raise HTTPException(status_code=400, detail="Exactly 4 temperature sensors required")

    values = [item.value for item in data.temperatures]

    min_temp = min(values)
    max_temp = max(values)

    record = models.OutdoorTemperature(
        user_id=current_user.id,
        temperatures=[item.model_dump() for item in data.temperatures],
        min_temperature=min_temp,
        max_temperature=max_temp
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record

# Получение списка температур вокруг дома для пользователя
@router.get("/latest", response_model=schemas.OutdoorTemperatureResponse)
def get_latest_outdoor_temperature(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    record = (
        db.query(models.OutdoorTemperature)
        .filter(models.OutdoorTemperature.user_id == current_user.id)
        .order_by(models.OutdoorTemperature.created_at.desc())
        .first()
    )

    if not record:
        # Возвращаем пустую структуру
        return schemas.OutdoorTemperatureResponse(
            temperatures=[],
            min_temperature=0.0,
            max_temperature=0.0,
            created_at=datetime.utcnow(),
        )

    return record