# PlantCare – CareCalendarService

API REST (FastAPI + Pydantic) para gestionar un calendario de cuidados de plantas:
registrar tareas, consultarlas, listar recordatorios y marcarlas como completadas.
Primera versión con **almacenamiento en memoria** (los datos se pierden al reiniciar).
Sin autenticación, correos ni integraciones externas.

## Estructura

```
plantcare/
├── app/
│   ├── main.py         # App FastAPI, /health, y entrega de la interfaz web
│   ├── static/         # Interfaz web (HTML + CSS + JS, sin dependencias)
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   ├── routes.py       # Endpoints HTTP (sin lógica de negocio)
│   ├── service.py      # CareCalendarService: reglas de negocio
│   ├── repository.py   # Almacenamiento en memoria
│   ├── models.py       # Enums, esquemas Pydantic y entidad Task
│   └── exceptions.py   # Excepciones de dominio
├── tests/
│   ├── test_service.py # Pruebas unitarias de la lógica
│   └── test_api.py     # Pruebas de endpoints
├── requirements.txt / requirements-dev.txt / pytest.ini
```

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Ejecución

```bash
uvicorn app.main:app --reload
```

- Interfaz web: http://127.0.0.1:8000/
- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

## Pruebas

```bash
pytest
```

## Interfaz web

Disponible en `http://127.0.0.1:8000/`. Es una página estática que consume la API existente
(no duplica reglas de negocio: estados, vencimientos y validaciones los decide siempre el servidor).

- **Calendario:** planta, tipo de cuidado, fecha y estado de cada tarea.
- **Nueva tarea:** riego, fertilización o poda, con fecha y descripción opcional.
- **Completar:** botón en cada tarea pendiente o vencida.
- **Filtros:** por estado y por nombre de planta (nombre exacto, sin distinguir mayúsculas; el campo sugiere las plantas ya registradas).
- **Recordatorios:** vencidos y próximos 7, 14 o 30 días.
- Mensajes claros para listas vacías, validaciones y errores de conexión; diseño adaptable a móvil y modo oscuro automático.

## Endpoints

| Método | Ruta                     | Descripción                                   | Respuestas        |
|--------|--------------------------|-----------------------------------------------|-------------------|
| POST   | `/tasks`                 | Registrar tarea (queda `pendiente`)           | 201, 422          |
| GET    | `/tasks`                 | Listar calendario (`?status=`, `?plant_name=`)| 200, 422          |
| GET    | `/tasks/{id}`            | Consultar una tarea                           | 200, 404, 422     |
| POST   | `/tasks/{id}/complete`   | Marcar como completada (idempotente)          | 200, 404, 422     |
| GET    | `/reminders?days_ahead=7`| Vencidas y próximas a vencer (no completadas) | 200, 422          |
| GET    | `/health`                | Estado del servicio                           | 200               |

### Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"plant_name":"Monstera","care_type":"riego","scheduled_date":"2030-01-15","description":"Regar con poca agua"}'
```

Respuesta (201):

```json
{
  "id": "0b6f...",
  "plant_name": "Monstera",
  "care_type": "riego",
  "scheduled_date": "2030-01-15",
  "description": "Regar con poca agua",
  "status": "pendiente",
  "created_at": "2025-06-15T12:00:00Z",
  "completed_at": null
}
```

## Reglas de negocio implementadas

1. Tipos permitidos: `riego`, `fertilizacion`, `poda` (se aceptan mayúsculas y tildes, p. ej. "Fertilización").
2. `plant_name` y `scheduled_date` son obligatorios; el nombre no puede estar vacío.
3. Toda tarea nueva se crea como `pendiente`.
4. Una tarea no completada con fecha anterior a hoy se devuelve como `vencida`.
5. Una tarea completada siempre se devuelve como `completada`.
6. Datos inválidos → `422`; tarea inexistente → `404`.

## Decisiones de diseño

- **`vencida` se calcula, no se guarda.** Solo se persiste `completed_at`; el estado se deriva
  en cada consulta comparando con la fecha actual. Así nunca queda desactualizado.
- **Reloj inyectable** (`today_provider`) para probar el vencimiento con fechas fijas.
- **Se permite registrar tareas con fecha pasada** (p. ej. para cargar historial); aparecen como `vencida`.
- **Fecha sin zona horaria:** "hoy" es la fecha del servidor (`date.today()`).
- **Repositorio intercambiable:** para pasar a una base de datos basta implementar
  `add / get / update / list_all` con la misma interfaz.
