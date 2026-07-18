from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Acao(str, Enum):
    ADICIONAR = "adicionar"
    INFORMAR_PRECO = "informar_preco"
    INFORMAR_QUANTIDADE = "informar_quantidade"
    ESCOLHER_PRODUTO = "escolher_produto"
    CONFIRMAR = "confirmar"
    CANCELAR = "cancelar"
    REMOVER = "remover"
    FINALIZAR = "finalizar"
    DESCONHECIDA = "desconhecida"


@dataclass
class ItemInterpretado:

    texto_original: str

    descricao: str | None = None

    quantidade: Decimal | None = None

    valor: Decimal | None = None

    marca: str | None = None

    produto_id: int | None = None


@dataclass
class Intencao:

    acao: Acao = Acao.DESCONHECIDA

    itens: list[ItemInterpretado] = field(default_factory=list)

    resposta: str | None = None