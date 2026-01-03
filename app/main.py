from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import rooms, applications, temperature, light, ventilation, gas, auth, sensors, users, motion, humidity

app = FastAPI(
    title="Smart Home API",
    description="API для управления умным домом",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(sensors.router)
app.include_router(auth.router)
app.include_router(gas.router)
app.include_router(ventilation.router)
app.include_router(temperature.router)
app.include_router(light.router)
app.include_router(rooms.router)
app.include_router(applications.router)
app.include_router(users.router)
app.include_router(motion.router)
app.include_router(humidity.router)

@app.get("/")
def root():
    return {"message": "Smart Home API is running 🚀"}
