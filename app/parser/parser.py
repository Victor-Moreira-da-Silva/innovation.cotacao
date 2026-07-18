from sqlalchemy.orm import Session

from app.parser.alias_parser import find_product_by_alias
from app.parser.regex_parser import ParsedMessage, parse_regex


def parse_message(db: Session, message: str) -> tuple[ParsedMessage, object | None]:
    parsed = parse_regex(message)
    product = find_product_by_alias(db, parsed.produto_texto, parsed.marca)
    if product and not parsed.marca:
        parsed.marca = product.marca
    return parsed, product
