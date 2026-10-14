"""Punto de entrada de la aplicación FastAPI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="PlantCare - CareCalendarService",
    description="API para gestionar el calendario de cuidados de plantas.",
    version="0.1.0",
)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Interfaz web (HTML estático que consume la API existente)."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
