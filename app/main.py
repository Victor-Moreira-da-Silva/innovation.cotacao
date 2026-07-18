from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database.init_db import init_db, seed_db
from app.database.session import SessionLocal
from app.routers.web import router
from app.routers import produtos

app = FastAPI(title="Sistema de Cotação Conversacional")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
app.include_router(produtos.router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
