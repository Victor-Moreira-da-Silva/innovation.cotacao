import hashlib
from sqlalchemy.orm import Session

from app.database.session import Base, engine
from app.models.entities import AliasProduto, Cliente, Produto, Usuario

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_db(db: Session) -> None:
    if not db.query(Usuario).first():
        db.add(Usuario(nome="Administrador", email="admin@example.com", senha_hash=hash_password("admin")))
    if not db.query(Produto).first():
        p1 = Produto(codigo="DET5", descricao="Detergente 5L", marca="Audax", unidade="GL", volume="5L", categoria="Limpeza", preco_padrao=15)
        p2 = Produto(codigo="SAN5", descricao="Água Sanitária 5L", marca="Audax", unidade="GL", volume="5L", categoria="Limpeza", preco_padrao=10)
        p3 = Produto(codigo="PAP", descricao="Papel Toalha", marca="Nobre", unidade="FD", categoria="Descartáveis", preco_padrao=22)
        db.add_all([p1, p2, p3]); db.flush()
        db.add_all([AliasProduto(alias="detergente", produto=p1), AliasProduto(alias="detergentes", produto=p1), AliasProduto(alias="agua sanitaria", produto=p2), AliasProduto(alias="água sanitária", produto=p2), AliasProduto(alias="papel", produto=p3)])
    if not db.query(Cliente).first():
        db.add(Cliente(razao_social="Prefeitura de Salto", nome_fantasia="Prefeitura de Salto", cidade="Salto"))
    db.commit()
