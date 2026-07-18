from app.database.init_db import seed_db
from app.database.session import Base
from app.models.entities import Cliente
from app.parser.regex_parser import parse_regex
from app.services.chat_service import processar_mensagem
from app.services.proposta_service import criar_proposta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_parse_full_message():
    parsed = parse_regex("10 detergentes Audax por 15 reais")
    assert parsed.quantidade == 10
    assert parsed.produto_texto == "detergentes"
    assert parsed.marca == "Audax"
    assert parsed.valor == 15


def test_chat_adds_complete_item(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_db(db)
    cliente = db.query(Cliente).first()
    proposta = criar_proposta(db, cliente.id)
    result = processar_mensagem(db, proposta, "10 detergentes Audax por 15 reais")
    assert result["status"] == "adicionado"
    db.refresh(proposta)
    assert len(proposta.itens) == 1
    assert float(proposta.valor_total) == 150.0
