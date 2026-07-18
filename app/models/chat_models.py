from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ItemChat:

    produto_id: int | None = None

    descricao: str | None = None

    marca: str | None = None

    quantidade: Decimal | None = None

    valor: Decimal | None = None

    resolvido: bool = False


@dataclass
class EstadoChat:

    itens: list[ItemChat] = field(default_factory=list)

    aguardando: str | None = None

    indice: int = 0