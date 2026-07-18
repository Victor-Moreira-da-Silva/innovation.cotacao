from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy.orm import Session
import tempfile
import os

from app.database.session import get_db
from app.models.entities import Produto
from app.services.importador_bling import importar_produtos

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/produtos", response_class=HTMLResponse)
def tela_produtos(request: Request, db: Session = Depends(get_db)):
    produtos = db.query(Produto).order_by(Produto.descricao).all()

    return templates.TemplateResponse(
        request=request,
        name="produtos.html",
        context={
            "request": request,
            "produtos": produtos,
        },
    )


@router.post("/produtos/importar")
async def importar_pdf(
    request: Request,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        temp.write(await arquivo.read())
        caminho = temp.name

    resultado = importar_produtos(caminho, db)

    os.remove(caminho)

    return templates.TemplateResponse(
    request=request,
    name="produtos.html",
    context={
        "request": request,
        "produtos": db.query(Produto).order_by(Produto.descricao).all(),
        "resultado": resultado,
    },
)