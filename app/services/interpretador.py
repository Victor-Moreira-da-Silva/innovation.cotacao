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
    original_sem_comando = re.sub(r"^(alterar|altera|editar|edita|mudar|muda|corrigir|corrige)\s+", "", original, flags=re.IGNORECASE).strip()
    valor = _extrair_valor_edicao(original_sem_comando, ("venda", "valor", "preco", "preço"), casas_decimais=2)
    quantidade = _extrair_valor_edicao(original_sem_comando, ("qtd", "qtde", "quantidade"), casas_decimais=3)
    alvo = texto
    substituto = None

    campo_primeiro = re.search(
        r"^(?P<campo>valor|preco|preço|venda|qtd|qtde|quantidade)\s+(?:(?:de|do|da)\s+)?(?P<alvo>.+?)\s+(?:para|por|=)\s*(?:r\$\s*)?(?P<numero>\d+(?:[.,]\d{1,3})?)$",
        original_sem_comando,
        re.IGNORECASE,
    )
    if campo_primeiro:
        alvo = campo_primeiro.group("alvo").strip()
        numero = Decimal(campo_primeiro.group("numero").replace(",", "."))
        if campo_primeiro.group("campo").lower() in {"qtd", "qtde", "quantidade"}:
            quantidade = numero
        else:
            valor = numero
    else:
        troca = re.search(r"(.+?)\s+(?:para|por|=)\s+(.+)$", texto)
        if troca:
            alvo = troca.group(1).strip()
            substituto = troca.group(2).strip()
            numero = _decimal_isolado(substituto)
            campo_alvo = alvo.split()[0] if alvo else ""
            if numero is not None and campo_alvo in {"qtd", "qtde", "quantidade", "valor", "preco", "preço", "venda"}:
                if campo_alvo in {"qtd", "qtde", "quantidade"}:
                    quantidade = numero
                else:
                    valor = numero
                substituto = None

    alvo = re.sub(r"\b(?:qtd|qtde|quantidade)\s*\d+(?:[.,]\d{1,3})?", "", alvo, flags=re.IGNORECASE).strip()
    alvo = re.sub(r"\b(?:venda|valor|preco|preço)\s*(?:r\$)?\s*\d+(?:[.,]\d{1,2})?", "", alvo, flags=re.IGNORECASE).strip()
    alvo = re.sub(r"^(?:qtd|qtde|quantidade|venda|valor|preco|preço)\s+", "", alvo, flags=re.IGNORECASE).strip()
    return Intencao(acao=Acao.EDITAR, texto_original=original, alvo=alvo, substituto=substituto, valor=valor, quantidade=quantidade)


def _extrair_valor_edicao(original: str, campos: tuple[str, ...], casas_decimais: int) -> Decimal | None:
    campos_regex = "|".join(re.escape(campo) for campo in campos)
    match = re.search(rf"(?:{campos_regex})\s*(?:r\$)?\s*(\d+(?:[.,]\d{{1,{casas_decimais}}})?)", original, re.IGNORECASE)
    return Decimal(match.group(1).replace(",", ".")) if match else None