from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from app.models.entities import Proposta


class Aguardando(str, Enum):
    PRODUTO = "produto"
    QUANTIDADE = "quantidade"
    VALOR = "valor"
    CONFIRMAR_PRECO = "confirmar_preco"


@dataclass(slots=True)
class ItemChat:
    """Item em construção durante a conversa."""

    texto_original: str
    descricao: str | None = None
    quantidade: Decimal | None = None
    valor: Decimal | None = None
    marca: str | None = None
    produto_id: int | None = None
    sugestao_valor: Decimal | None = None

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "ItemChat":
        return cls(
            texto_original=dados.get("texto_original", ""),
            descricao=dados.get("descricao"),
            quantidade=_decimal_ou_none(dados.get("quantidade")),
            valor=_decimal_ou_none(dados.get("valor")),
            marca=dados.get("marca"),
            produto_id=dados.get("produto_id"),
            sugestao_valor=_decimal_ou_none(dados.get("sugestao_valor")),
        )


@dataclass(slots=True)
class EstadoChat:
    """Memória persistida em JSON para manter contexto entre mensagens."""

    aguardando: Aguardando | None = None
    indice: int = 0
    itens: list[ItemChat] = field(default_factory=list)
    opcoes: list[int] = field(default_factory=list)
    item: ItemChat | None = None
    historico: list[dict[str, str]] = field(default_factory=list)
    contexto: dict[str, Any] = field(default_factory=dict)

    def registrar(self, origem: str, mensagem: str) -> None:
        self.historico.append({"origem": origem, "mensagem": mensagem})
        self.historico = self.historico[-50:]


def obter_estado(proposta: Proposta) -> EstadoChat:
    dados = proposta.estado_chat or {}
    aguardando = dados.get("aguardando")
    return EstadoChat(
        aguardando=Aguardando(aguardando) if aguardando else None,
        indice=dados.get("indice", 0),
        itens=[ItemChat.from_dict(item) for item in dados.get("itens", [])],
        opcoes=list(dados.get("opcoes", [])),
        item=ItemChat.from_dict(dados["item"]) if dados.get("item") else None,
        historico=list(dados.get("historico", [])),
        contexto=dict(dados.get("contexto", {})),
    )


def salvar_estado(proposta: Proposta, estado: EstadoChat) -> None:
    proposta.estado_chat = _serializar(asdict(estado))


def limpar_estado(proposta: Proposta) -> None:
    salvar_estado(proposta, EstadoChat())


def _serializar(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    return valor


def _decimal_ou_none(valor: Any) -> Decimal | None:
    if valor in (None, ""):
        return None
    return Decimal(str(valor))