import unicodedata
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import AliasProduto, Produto


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def find_product_by_alias(
    db: Session,
    text: str | None,
    marca: str | None = None,
) -> Produto | None:

    if not text:
        return None

    busca = normalize(text)

    # procura primeiro nos aliases
    aliases = (
        db.query(AliasProduto)
        .join(Produto)
        .filter(Produto.ativo.is_(True))
        .all()
    )

    for alias in aliases:

        alias_norm = normalize(alias.alias)

        if busca in alias_norm or alias_norm in busca:

            if (
                marca
                and alias.produto.marca
                and normalize(alias.produto.marca) != normalize(marca)
            ):
                continue

            return alias.produto

    # procura por descrição
    produtos = (
        db.query(Produto)
        .filter(Produto.ativo.is_(True))
        .all()
    )

    melhores = []

    for produto in produtos:

        descricao = normalize(produto.descricao)

        if busca in descricao:

            if (
                marca
                and produto.marca
                and normalize(produto.marca) != normalize(marca)
            ):
                continue

            melhores.append(produto)

    if not melhores:
        return None

    # prioriza descrições que começam com o texto pesquisado
    melhores.sort(
        key=lambda p: (
            not normalize(p.descricao).startswith(busca),
            len(normalize(p.descricao)),
        )
    )

    return melhores[0]