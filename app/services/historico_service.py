from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.entities import HistoricoPreco


def sugestao_preco(db: Session, cliente_id: int, produto_id: int) -> dict | None:
    ultimo_cliente = db.query(HistoricoPreco).filter_by(cliente_id=cliente_id, produto_id=produto_id).order_by(desc(HistoricoPreco.data)).first()
    ultimo_geral = db.query(HistoricoPreco).filter_by(produto_id=produto_id).order_by(desc(HistoricoPreco.data)).first()
    media = db.query(func.avg(HistoricoPreco.valor_unitario)).filter_by(produto_id=produto_id).scalar()
    base = ultimo_cliente or ultimo_geral
    if not base and media is None:
        return None
    return {"ultimo_cliente": ultimo_cliente, "ultimo_geral": ultimo_geral, "media": media, "sugerido": base.valor_unitario if base else media}
