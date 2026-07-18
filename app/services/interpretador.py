from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from app.models.intencoes import Acao, Intencao, ItemInterpretado

CONFIRMAR = {"sim", "s", "ok", "pode", "confirmo", "confirmar", "usar", "usa", "use", "ultimo", "último", "use ultimo", "usa ultimo", "use último", "usa último"}
CANCELAR = {"nao", "não", "n", "cancelar", "cancela", "desistir", "parar"}
FINALIZAR = ("finalizar", "concluir", "fechar", "gerar proposta", "gere o pdf", "gerar pdf", "pdf")
REMOVER = ("remove", "remover", "apaga", "apagar", "excluir", "exclui", "tira", "retira")
EDITAR = ("alterar", "altera", "editar", "edita", "mudar", "muda", "corrigir", "corrige")


def interpretar(texto: str) -> Intencao:
    """Interpreta comandos comerciais sem depender de formulário."""
    original = texto.strip()
    normalizado = _normalizar(original)

    if not original:
        return Intencao(acao=Acao.DESCONHECIDA, texto_original=original)
    if normalizado in {_normalizar(v) for v in CONFIRMAR}:
        return Intencao(acao=Acao.CONFIRMAR, texto_original=original)
    if normalizado in {_normalizar(v) for v in CANCELAR}:
        return Intencao(acao=Acao.CANCELAR, texto_original=original)
    if any(p in normalizado for p in FINALIZAR):
        return Intencao(acao=Acao.FINALIZAR, texto_original=original)

    troca = re.search(r"\btroca(?:r)?\s+(.+?)\s+por\s+(.+)$", normalizado)
    if troca:
        return Intencao(acao=Acao.TROCAR, texto_original=original, alvo=troca.group(1).strip(), substituto=troca.group(2).strip())

    if any(normalizado.startswith(p) for p in REMOVER):
        alvo = re.sub(r"^(remove(?:r)?|apaga(?:r)?|exclu[íi]r?|tira|retira)\s+", "", normalizado).strip()
        return Intencao(acao=Acao.REMOVER, texto_original=original, alvo=alvo or "ultimo")

    if any(normalizado.startswith(p) for p in EDITAR):
        return _interpretar_edicao(original, normalizado)

    numero = _inteiro_isolado(normalizado)
    if numero is not None:
        return Intencao(acao=Acao.ESCOLHER_PRODUTO, texto_original=original, numero=numero)

    decimal = _decimal_isolado(original)
    if decimal is not None:
        return Intencao(acao=Acao.INFORMAR_PRECO, texto_original=original, valor=decimal, quantidade=decimal)

    itens = interpretar_itens(original)
    return Intencao(acao=Acao.ADICIONAR if itens else Acao.DESCONHECIDA, itens=itens, texto_original=original)


def interpretar_itens(texto: str) -> list[ItemInterpretado]:
    itens: list[ItemInterpretado] = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        venda = re.fullmatch(r"venda\s*(?:r\$)?\s*(\d+(?:[.,]\d{1,2})?)", linha, re.IGNORECASE)
        if venda and itens:
            itens[-1].valor = Decimal(venda.group(1).replace(",", "."))
            itens[-1].texto_original = f"{itens[-1].texto_original} {linha}"
            continue
        item = interpretar_item(linha)
        if item:
            itens.append(item)
    return itens


def interpretar_item(texto: str) -> ItemInterpretado | None:
    if not texto:
        return None
    item = ItemInterpretado(texto_original=texto)
    restante = texto.strip()

    qtd = re.match(r"^(\d+(?:[.,]\d{1,3})?)\s+(.+)$", restante)
    if qtd:
        item.quantidade = Decimal(qtd.group(1).replace(",", "."))
        restante = qtd.group(2).strip()

    preco = re.search(r"(?:\s|^)(?:por|a|valor(?: de)?|r\$)?\s*(?:r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:reais|real)?$", restante, re.IGNORECASE)
    if preco and (preco.group(0).strip().lower().startswith(("por", "a", "valor", "r$")) or re.search(r"[.,]\d{2}|reais|real", preco.group(0), re.I)):
        item.valor = Decimal(preco.group(1).replace(",", "."))
        restante = restante[: preco.start()].strip()

    marca = re.search(r"\b(?:marca|da|do)\s+([\wÀ-ÿ.-]+)$", restante, re.IGNORECASE)
    if marca:
        item.marca = marca.group(1)

    item.descricao = restante or None
    return item if item.descricao or item.quantidade or item.valor else None


def _normalizar(texto: str) -> str:
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(ch) != "Mn")
    return " ".join(sem_acento.replace("?", " ").replace(".", " ").split())


def _inteiro_isolado(texto: str) -> int | None:
    return int(texto) if re.fullmatch(r"\d{1,3}", texto) else None


def _decimal_isolado(texto: str) -> Decimal | None:
    if not re.fullmatch(r"\s*(?:r\$\s*)?\d+(?:[.,]\d{1,3})?\s*", texto, re.IGNORECASE):
        return None
    try:
        return Decimal(re.sub(r"[^\d,.]", "", texto).replace(",", "."))
    except InvalidOperation:
        return None


def _interpretar_edicao(original: str, normalizado: str) -> Intencao:
    texto = re.sub(r"^(alterar|altera|editar|edita|mudar|muda|corrigir|corrige)\s+", "", normalizado).strip()
    substituto = None
    alvo = texto
    troca = re.search(r"(.+?)\s+(?:para|por)\s+(.+)$", texto)
    if troca:
        alvo = troca.group(1).strip()
        substituto = troca.group(2).strip()
    valor = None
    quantidade = None
    valor_match = re.search(r"(?:venda|valor|preco|preço)\s*(?:r\$)?\s*(\d+(?:[.,]\d{1,2})?)", original, re.IGNORECASE)
    if valor_match:
        valor = Decimal(valor_match.group(1).replace(",", "."))
    qtd_match = re.search(r"(?:qtd|qtde|quantidade)\s*(\d+(?:[.,]\d{1,3})?)", original, re.IGNORECASE)
    if qtd_match:
        quantidade = Decimal(qtd_match.group(1).replace(",", "."))
    alvo = re.sub(r"\b(?:qtd|qtde|quantidade)\s*\d+(?:[.,]\d{1,3})?", "", alvo, flags=re.IGNORECASE).strip()
    alvo = re.sub(r"\b(?:venda|valor|preco|preço)\s*(?:r\$)?\s*\d+(?:[.,]\d{1,2})?", "", alvo, flags=re.IGNORECASE).strip()
    return Intencao(acao=Acao.EDITAR, texto_original=original, alvo=alvo, substituto=substituto, valor=valor, quantidade=quantidade)