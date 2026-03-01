from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app import models, schemas
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/outdoor-light", tags=["Outdoor Light"])

@router.post("/", response_model=schemas.OutdoorLightResponse)
def receive_outdoor_light(
    data: schemas.OutdoorLightCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if len(data.lights) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 light sensors required (front and back)")

    record = models.OutdoorLight(
        user_id=current_user.id,
        lights=[item.model_dump() for item in data.lights]
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record

@router.get("/latest", response_model=schemas.OutdoorLightResponse)
def get_latest_outdoor_light(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    record = (
        db.query(models.OutdoorLight)
        .filter(models.OutdoorLight.user_id == current_user.id)
        .order_by(models.OutdoorLight.created_at.desc())
        .first()
    )

    if not record:
        return schemas.OutdoorLightResponse(
            lights=[
                {"side": "front", "is_on": False},
                {"side": "back", "is_on": False}
            ],
            created_at=datetime.utcnow(),
        )

    return record