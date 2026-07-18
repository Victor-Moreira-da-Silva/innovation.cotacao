from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Cliente, Produto, Proposta
from app.services.chat_service import processar_mensagem
from app.services.pdf_service import gerar_pdf
from app.services.proposta_service import (
    criar_proposta,
    finalizar_proposta,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "clientes": db.query(Cliente).all(),
            "produtos": db.query(Produto).all(),
            "propostas": db.query(Proposta).all(),
        },
    )

@router.get("/clientes", response_class=HTMLResponse)
def tela_clientes(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="lista.html",
        context={
            "request": request,
            "titulo": "Clientes",
            "colunas": ["Razão social", "Nome fantasia", "CNPJ", "Telefone", "E-mail"],
            "linhas": [[c.razao_social, c.nome_fantasia or "-", c.cnpj or "-", c.telefone or "-", c.email or "-"] for c in db.query(Cliente).order_by(Cliente.razao_social).all()],
        },
    )


@router.get("/propostas", response_class=HTMLResponse)
def tela_propostas(request: Request, db: Session = Depends(get_db)):
    propostas = db.query(Proposta).order_by(Proposta.data.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="lista.html",
        context={
            "request": request,
            "titulo": "Propostas",
            "colunas": ["Número", "Cliente", "Status", "Total", "Abrir"],
            "linhas": [[p.numero, p.cliente.razao_social if p.cliente else "-", p.status, f"R$ {p.valor_total:.2f}", f"<a href='/propostas/{p.id}'>Abrir</a>"] for p in propostas],
            "html_seguro": True,
        },
    )


@router.get("/historico", response_class=HTMLResponse)
def tela_historico(request: Request):
    return templates.TemplateResponse(request=request, name="mensagem.html", context={"request": request, "titulo": "Histórico", "mensagem": "O histórico de preços é salvo ao finalizar propostas."})


@router.get("/configuracoes", response_class=HTMLResponse)
def tela_configuracoes(request: Request):
    return templates.TemplateResponse(request=request, name="mensagem.html", context={"request": request, "titulo": "Configurações", "mensagem": "Configurações em desenvolvimento."})



@router.post("/propostas")
def nova_proposta(cliente_id: int = Form(...), db: Session = Depends(get_db)):
    proposta = criar_proposta(db, cliente_id)
    return {
        "id": proposta.id,
        "numero": proposta.numero,
    }


@router.get("/propostas/{proposta_id}", response_class=HTMLResponse)
def tela_proposta(
    proposta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    proposta = db.get(Proposta, proposta_id)

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    return templates.TemplateResponse(
        request=request,
        name="proposta.html",
        context={
            "request": request,
            "proposta": proposta,
        },
    )


@router.post("/propostas/{proposta_id}/chat")
def chat(
    proposta_id: int,
    mensagem: str = Form(...),
    db: Session = Depends(get_db),
):
    proposta = db.get(Proposta, proposta_id)

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    return processar_mensagem(db, proposta, mensagem)


@router.post("/propostas/{proposta_id}/finalizar")
def finalizar(
    proposta_id: int,
    db: Session = Depends(get_db),
):
    proposta = db.get(Proposta, proposta_id)

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    finalizar_proposta(db, proposta)

    return {"status": proposta.status}


@router.get("/propostas/{proposta_id}/pdf")
def pdf(
    proposta_id: int,
    db: Session = Depends(get_db),
):
    proposta = db.get(Proposta, proposta_id)

    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    return Response(
        content=gerar_pdf(proposta),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="proposta-{proposta.numero}.pdf"'
        },
    )