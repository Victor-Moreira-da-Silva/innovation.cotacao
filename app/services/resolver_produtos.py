from dataclasses import dataclass

from rapidfuzz import fuzz

from sqlalchemy.orm import Session

from app.models.entities import Produto


@dataclass
class ResultadoProduto:

    encontrado: Produto | None = None

    opcoes: list[Produto] | None = None

    score: int = 0


def normalizar(texto: str):

    texto = texto.lower()

    texto = texto.replace("-", " ")

    texto = texto.replace("/", " ")

    texto = " ".join(texto.split())

    return texto


def resolver_produto(
    db: Session,
    texto: str
):

    texto = normalizar(texto)

    produtos = db.query(Produto).all()

    ranking = []

    for produto in produtos:

        descricao = normalizar(produto.descricao)

        score = fuzz.token_set_ratio(
            texto,
            descricao
        )

        ranking.append(
            (
                score,
                produto
            )
        )

    ranking.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    resultado = ResultadoProduto()

    if not ranking:

        return resultado

    melhor_score = ranking[0][0]

    resultado.score = melhor_score

    if melhor_score < 55:

        return resultado

    melhores = []

    for score, produto in ranking:

        if score >= melhor_score - 5:

            melhores.append(produto)

    if len(melhores) == 1:

        resultado.encontrado = melhores[0]

    else:

        resultado.opcoes = melhores[:5]

    return resultado