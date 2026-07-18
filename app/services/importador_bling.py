import re
import pdfplumber
from sqlalchemy.orm import Session

from app.models.entities import Produto


REGEX_PRODUTO = re.compile(
    r"^(INN\d+)\s+(.+?)\s+(\d+,\d+)$"
)


def importar_produtos(caminho_pdf: str, db: Session):

    encontrados = 0
    adicionados = 0
    existentes = 0

    with pdfplumber.open(caminho_pdf) as pdf:

        for pagina in pdf.pages:

            texto = pagina.extract_text()

            if not texto:
                continue

            for linha in texto.splitlines():

                linha = linha.strip()

                resultado = REGEX_PRODUTO.match(linha)

                if not resultado:
                    continue

                codigo = resultado.group(1).strip()

                descricao = resultado.group(2).strip()

                encontrados += 1

                produto = (
                    db.query(Produto)
                    .filter(Produto.codigo == codigo)
                    .first()
                )

                if produto:

                    existentes += 1
                    continue

                marca = None

                if " - " in descricao:

                    descricao, marca = descricao.rsplit(" - ", 1)

                    descricao = descricao.strip()
                    marca = marca.strip()

                novo = Produto(

                    codigo=codigo,

                    descricao=descricao,

                    marca=marca,

                    unidade="UN",

                    ativo=True,

                )

                db.add(novo)

                adicionados += 1

    db.commit()

    return {

        "encontrados": encontrados,

        "adicionados": adicionados,

        "existentes": existentes,

    }