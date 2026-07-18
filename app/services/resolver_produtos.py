from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

try:
    from rapidfuzz import fuzz
except ModuleNotFoundError:  # pragma: no cover - fallback para ambientes sem dependências instaladas
    from difflib import SequenceMatcher

    class _FuzzFallback:
        @staticmethod
        def WRatio(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio() * 100

        @staticmethod
        def token_set_ratio(a: str, b: str) -> float:
            sa, sb = set(a.split()), set(b.split())
            if not sa or not sb:
                return 0
            inter = " ".join(sorted(sa & sb))
            return max(SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, inter, " ".join(sorted(sa | sb))).ratio()) * 100

        @staticmethod
        def partial_token_set_ratio(a: str, b: str) -> float:
            curto, longo = (a, b) if len(a) <= len(b) else (b, a)
            if curto in longo:
                return 100
            return SequenceMatcher(None, curto, longo).ratio() * 100

    fuzz = _FuzzFallback()
from sqlalchemy.orm import Session, selectinload

from app.models.entities import AliasProduto, Produto

ALIASES_PADRAO = {
    "agua sanit": "agua sanitaria",
    "agua sanitária": "agua sanitaria",
    "qboa": "agua sanitaria",
    "q boa": "agua sanitaria",
    "interfolha": "papel toalha interfolha",
    "papel interfolha": "papel toalha interfolha",
    "det": "detergente",
}


@dataclass(slots=True)
class CandidatoProduto:
    produto: Produto
    score: float
    origem: str


@dataclass(slots=True)
class ResultadoProduto:
    encontrado: Produto | None = None
    opcoes: list[Produto] = field(default_factory=list)
    score: float = 0
    ranking: list[CandidatoProduto] = field(default_factory=list)


def normalizar(texto: str | None) -> str:
    texto = texto or ""
    texto = "".join(ch for ch in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(ch) != "Mn")
    for antigo in ("-", "/", ".", ","):
        texto = texto.replace(antigo, " ")
    palavras = [_singularizar(p) for p in texto.split()]
    return " ".join(palavras)


def resolver_produto(db: Session, texto: str | None, limite: int = 5) -> ResultadoProduto:
    """Resolve um produto por descrição, marca, aliases e similaridade."""
    consulta = normalizar(texto)
    consulta = ALIASES_PADRAO.get(consulta, consulta)
    resultado = ResultadoProduto()
    if not consulta:
        return resultado

    produtos = db.query(Produto).options(selectinload(Produto.aliases)).filter(Produto.ativo.is_(True)).all()
    ranking: dict[int, CandidatoProduto] = {}

    for produto in produtos:
        campos = [(produto.descricao, 1.0), (f"{produto.descricao} {produto.marca or ''}", 1.0), (produto.codigo, 0.85), (produto.categoria, 0.7), (produto.marca, 0.65)]
        campos.extend((alias.alias, 1.0) for alias in produto.aliases)
        campos.extend((f"{alias.alias} {produto.marca or ''}", 1.0) for alias in produto.aliases)
        melhor_score = 0.0
        melhor_origem = "descricao"
        for campo, peso in campos:
            normal = normalizar(campo)
            if not normal:
                continue
            score = max(
                fuzz.WRatio(consulta, normal),
                fuzz.token_set_ratio(consulta, normal),
                fuzz.partial_token_set_ratio(consulta, normal) * 0.95,
            )
            if consulta == normal:
                score = 100
            score *= peso
            if score > melhor_score:
                melhor_score = score
                melhor_origem = campo or "descricao"
        if melhor_score >= 45:
            ranking[produto.id] = CandidatoProduto(produto=produto, score=melhor_score, origem=melhor_origem)

    ordenado = sorted(ranking.values(), key=lambda c: c.score, reverse=True)
    resultado.ranking = ordenado[:limite]
    if not ordenado:
        return resultado

    resultado.score = ordenado[0].score
    if ordenado[0].score >= 92 and (len(ordenado) == 1 or ordenado[0].score - ordenado[1].score >= 8):
        resultado.encontrado = ordenado[0].produto
        return resultado

    proximos = [c.produto for c in ordenado if c.score >= max(55, ordenado[0].score - 7)][:limite]
    if len(proximos) == 1 and ordenado[0].score >= 75:
        resultado.encontrado = proximos[0]
    else:
        resultado.opcoes = proximos or [c.produto for c in ordenado[:limite]]
    return resultado


def criar_alias(db: Session, produto_id: int, alias: str) -> AliasProduto:
    existente = db.query(AliasProduto).filter(AliasProduto.produto_id == produto_id, AliasProduto.alias == alias).first()
    if existente:
        return existente
    novo = AliasProduto(produto_id=produto_id, alias=alias)
    db.add(novo)
    return novo


def _singularizar(palavra: str) -> str:
    if len(palavra) > 4 and palavra.endswith("oes"):
        return palavra[:-3] + "ao"
    if len(palavra) > 3 and palavra.endswith("is"):
        return palavra[:-2] + "l"
    if len(palavra) > 3 and palavra.endswith("s"):
        return palavra[:-1]
    return palavra
