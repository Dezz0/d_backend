from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import rooms, applications, auth, sensors, users, arduino_endpoint

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(sensors.router)
app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(applications.router)
app.include_router(users.router)
app.include_router(arduino_endpoint.router)
@app.get("/")
def root():
    return {"message": "Smart Home API is running 🚀"}
