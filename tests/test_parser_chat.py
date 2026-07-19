from app.database.init_db import seed_db
from app.database.session import Base
from app.models.entities import Cliente, Produto
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


def _proposta_teste(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_db(db)
    cliente = db.query(Cliente).first()
    proposta = criar_proposta(db, cliente.id)
    return db, proposta


def test_chat_adds_multiple_items_and_reports_missing_product(tmp_path):
    db, proposta = _proposta_teste(tmp_path)
    result = processar_mensagem(
        db,
        proposta,
        """2 detergentes Audax
Venda 15,00
3 produto inexistente
Venda 9,99
4 papel
Venda22,00""",
    )
    assert result["status"] == "adicionado"
    assert "Não encontrei" in result["resposta"]
    db.refresh(proposta)
    assert len(proposta.itens) == 2
    assert float(proposta.valor_total) == 118.0


def test_chat_edits_and_confirms_delete_item(tmp_path):
    db, proposta = _proposta_teste(tmp_path)
    processar_mensagem(db, proposta, "2 detergentes Audax por 15 reais")

    result = processar_mensagem(db, proposta, "alterar detergente quantidade 3 valor 20")
    assert result["status"] == "editado"
    db.refresh(proposta)
    assert float(proposta.itens[0].quantidade) == 3.0
    assert float(proposta.itens[0].valor_unitario) == 20.0
    assert float(proposta.valor_total) == 60.0

    result = processar_mensagem(db, proposta, "excluir detergente")
    assert result["status"] == "confirmar_exclusao"
    result = processar_mensagem(db, proposta, "sim")
    assert result["status"] == "removido"
    db.refresh(proposta)
    assert proposta.itens == []
    assert float(proposta.valor_total) == 0.0

def test_chat_adds_item_after_ambiguous_product_selection(tmp_path):
    db, proposta = _proposta_teste(tmp_path)
    db.add(Produto(codigo="SAN5B", descricao="Agua Sanitaria 5L", marca="Outra", unidade="GL", volume="5L", categoria="Limpeza", preco_padrao=9))
    db.commit()

    result = processar_mensagem(db, proposta, "10 Água Sanitária 5L por 2 reais")
    assert result["status"] == "escolher_produto"

    result = processar_mensagem(db, proposta, "1")

    assert result["status"] == "adicionado"
    assert "1 item(ns) adicionados" in result["resposta"]
    assert len(result["itens"]) == 1
    assert result["valor_total"] == 20.0
    db.refresh(proposta)
    assert len(proposta.itens) == 1
    assert float(proposta.valor_total) == 20.0