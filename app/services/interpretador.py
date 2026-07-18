import re
from decimal import Decimal

from app.models.intencoes import (
    Acao,
    Intencao,
    ItemInterpretado,
)


CONFIRMAR = {
    "sim",
    "s",
    "ok",
    "pode",
    "usar",
    "usa",
    "último",
    "ultimo",
}

CANCELAR = {
    "nao",
    "não",
    "cancelar",
}

FINALIZAR = {
    "finalizar",
    "concluir",
    "fechar",
    "gerar proposta",
}

REMOVER = {
    "remover",
    "apagar",
    "excluir",
}


def interpretar(texto: str) -> Intencao:

    texto = texto.strip()

    texto_lower = texto.lower()

    # --------------------
    # confirmações
    # --------------------

    if texto_lower in CONFIRMAR:

        return Intencao(
            acao=Acao.CONFIRMAR,
            texto_original=texto,
        )

    # --------------------

    if texto_lower in CANCELAR:

        return Intencao(
            acao=Acao.CANCELAR,
            texto_original=texto,
        )

    # --------------------

    if any(p in texto_lower for p in FINALIZAR):

        return Intencao(
            acao=Acao.FINALIZAR,
            texto_original=texto,
        )

    # --------------------

    if "ultimo item" in texto_lower:

        return Intencao(
            acao=Acao.REMOVER,
            texto_original=texto,
        )

    # --------------------
    # múltiplas linhas
    # --------------------

    linhas = []

    for linha in texto.splitlines():

        linha = linha.strip()

        if linha:

            linhas.append(linha)

    if not linhas:

        linhas = [texto]

    itens = []

    for linha in linhas:

        item = interpretar_item(linha)

        if item:

            itens.append(item)

    return Intencao(

        acao=Acao.ADICIONAR,

        itens=itens,

        texto_original=texto,
    )


def interpretar_item(texto: str):

    texto = texto.strip()

    item = ItemInterpretado(

        texto_original=texto

    )

    # ----------------------
    # quantidade no início
    # ----------------------

    m = re.match(

        r"^(\d+(?:[.,]\d+)?)\s+(.*)$",

        texto,

    )

    restante = texto

    if m:

        item.quantidade = Decimal(

            m.group(1).replace(",", ".")

        )

        restante = m.group(2)

    # ----------------------
    # preço no final
    # ----------------------

    m = re.search(

        r"(\d+[.,]\d{2})$",

        restante,

    )

    if m:

        item.valor = Decimal(

            m.group(1).replace(",", ".")

        )

        restante = restante[:m.start()].strip()

    item.descricao = restante

    return item