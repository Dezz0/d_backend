from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/home-control", tags=["Home Control"])

# Получение режима управления - пользователь/arduino
@router.get("/mode", response_model=schemas.HomeControlModeResponse)
def get_home_control_mode(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mode = db.query(models.HomeControlMode).filter(
        models.HomeControlMode.user_id == current_user.id
    ).first()

    if not mode:
        mode = models.HomeControlMode(
            user_id=current_user.id,
            is_manual=False
        )
        db.add(mode)
        db.commit()
        db.refresh(mode)

    return mode

# Переключение режима управления - пользователь
@router.patch("/mode", response_model=schemas.HomeControlModeResponse)
def update_home_control_mode(
    data: schemas.HomeControlModeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mode = db.query(models.HomeControlMode).filter(
        models.HomeControlMode.user_id == current_user.id
    ).first()

    if not mode:
        mode = models.HomeControlMode(
            user_id=current_user.id,
            is_manual=data.is_manual
        )
        db.add(mode)
    else:
        mode.is_manual = data.is_manual

    db.commit()
    db.refresh(mode)

    return mode

# Позволяет управлять состоянием датчика через телефон - пользователь
@router.patch("/toggle-device")
def toggle_device(
    data: schemas.ToggleDeviceRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if data.type not in ["light", "ventilation"]:
        raise HTTPException(status_code=400, detail="Invalid device type")

    if data.type == "light":
        device = db.query(models.LightSensor).filter(
            models.LightSensor.room_id == data.room_id,
            models.LightSensor.sensor_id == data.sensor_id
        ).first()
    else:
        device = db.query(models.VentilationSensor).filter(
            models.VentilationSensor.room_id == data.room_id,
            models.VentilationSensor.sensor_id == data.sensor_id
        ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_on = data.is_on
    db.commit()
    db.refresh(device)

    return {"success": True, "is_on": device.is_on}