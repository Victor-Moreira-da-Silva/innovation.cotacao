from sqlalchemy.orm import Session

from app.models.entities import Proposta
from app.services.chat.engine import ConversationEngine


def processar_mensagem(
    db: Session,
    proposta: Proposta,
    mensagem: str
):
    engine = ConversationEngine(db)

    return engine.processar(
        proposta,
        mensagem
    )