import re
from dataclasses import dataclass
from decimal import Decimal

_NUM = r"\d+(?:[\.,]\d+)?"
_PRICE_PATTERNS = [
    re.compile(rf"(?:por|a|valor(?: de)?|r\$)\s*(?:r\$\s*)?({_NUM})", re.I),
    re.compile(rf"({_NUM})\s*(?:reais|real)\b", re.I),
]


@dataclass
class ParsedMessage:
    quantidade: Decimal | None = None
    produto_texto: str | None = None
    marca: str | None = None
    valor: Decimal | None = None


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(".", "").replace(",", "."))


def parse_regex(message: str) -> ParsedMessage:
    text = message.strip()
    result = ParsedMessage()
    qty = re.match(rf"^\s*({_NUM})\b", text)
    if qty:
        result.quantidade = _decimal(qty.group(1))
        text = text[qty.end():].strip()
    for pattern in _PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            result.valor = _decimal(match.group(1))
            text = (text[:match.start()] + text[match.end():]).strip()
            break
    words = text.split()
    if words:
        # Heurística: última palavra em TitleCase é marca; o restante é busca por produto/alias.
        if len(words) > 1 and words[-1][:1].isupper():
            result.marca = words[-1]
            words = words[:-1]
        result.produto_texto = " ".join(words) or None
    return result
