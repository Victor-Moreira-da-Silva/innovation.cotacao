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
    TROCAR = "trocar"
    FINALIZAR = "finalizar"
    DESCONHECIDA = "desconhecida"


@dataclass(slots=True)
class ItemInterpretado:
    """Produto informado pelo usuário antes da resolução no cadastro."""

    texto_original: str
    descricao: str | None = None
    quantidade: Decimal | None = None
    valor: Decimal | None = None
    marca: str | None = None
    produto_id: int | None = None


@dataclass(slots=True)
class Intencao:
    """Resultado semântico extraído de uma mensagem do chat."""

    acao: Acao = Acao.DESCONHECIDA
    itens: list[ItemInterpretado] = field(default_factory=list)
    texto_original: str = ""
    resposta: str | None = None
    alvo: str | None = None
    substituto: str | None = None
    numero: int | None = None
    valor: Decimal | None = None
    quantidade: Decimal | None = None