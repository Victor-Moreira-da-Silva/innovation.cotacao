from dataclasses import asdict, dataclass, field
from typing import Any

from app.models.entities import Proposta


@dataclass
class EstadoChat:

    aguardando: str | None = None

    indice: int = 0

    itens: list[dict] = field(default_factory=list)

    opcoes: list[int] = field(default_factory=list)

    item: dict | None = None


def obter_estado(proposta: Proposta) -> EstadoChat:

    dados = proposta.estado_chat or {}

    return EstadoChat(

        aguardando=dados.get("aguardando"),

        indice=dados.get("indice", 0),

        itens=dados.get("itens", []),

        opcoes=dados.get("opcoes", []),

        item=dados.get("item"),
    )


def salvar_estado(
    proposta: Proposta,
    estado: EstadoChat,
):

    proposta.estado_chat = asdict(estado)


def limpar_estado(
    proposta: Proposta,
):

    proposta.estado_chat = asdict(EstadoChat())


def adicionar_item(
    estado: EstadoChat,
    item: dict,
):

    estado.itens.append(item)


def item_atual(
    estado: EstadoChat,
) -> dict | None:

    if estado.indice >= len(estado.itens):

        return None

    return estado.itens[estado.indice]


def proximo_item(
    estado: EstadoChat,
):

    estado.indice += 1


def finalizar_itens(
    estado: EstadoChat,
):

    estado.itens.clear()

    estado.indice = 0

    estado.aguardando = None

    estado.opcoes.clear()

    estado.item = None