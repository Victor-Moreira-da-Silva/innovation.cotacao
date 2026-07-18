from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.entities import HistoricoPreco, ItemProposta, Proposta


def criar_proposta(db: Session, cliente_id: int | None = None) -> Proposta:
    numero = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    proposta = Proposta(numero=numero, cliente_id=cliente_id)
    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return proposta


def adicionar_item(db: Session, proposta: Proposta, produto_id: int, quantidade: Decimal, valor_unitario: Decimal) -> ItemProposta:
    total = quantidade * valor_unitario
    item = ItemProposta(
        proposta_id=proposta.id,
        produto_id=produto_id,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
        valor_total=total,
    )
    db.add(item)
    db.flush()
    proposta.valor_total = sum((i.valor_total for i in proposta.itens), Decimal("0"))
    db.commit()
    db.refresh(item)
    db.refresh(proposta)
    return item


def finalizar_proposta(db: Session, proposta: Proposta) -> Proposta:
    proposta.status = "Finalizada"
    for item in proposta.itens:
        if proposta.cliente_id:
            db.add(
                HistoricoPreco(
                    cliente_id=proposta.cliente_id,
                    produto_id=item.produto_id,
                    quantidade=item.quantidade,
                    valor_unitario=item.valor_unitario,
                )
            )
    db.commit()
    db.refresh(proposta)
    return proposta