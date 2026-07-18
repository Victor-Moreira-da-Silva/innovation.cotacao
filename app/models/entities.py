from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Código do fornecedor (não é único)
    codigo: Mapped[str] = mapped_column(String(40), index=True)

    descricao: Mapped[str] = mapped_column(String(255), index=True)
    marca: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    unidade: Mapped[str] = mapped_column(String(30), default="UN")
    volume: Mapped[str | None] = mapped_column(String(80), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preco_padrao: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list["AliasProduto"]] = relationship(
        back_populates="produto"
    )


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(255), index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(30), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True)


class AliasProduto(Base):
    __tablename__ = "aliases_produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(180), index=True)

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produtos.id")
    )

    produto: Mapped[Produto] = relationship(
        back_populates="aliases"
    )


class Proposta(Base):
    __tablename__ = "propostas"

    id: Mapped[int] = mapped_column(primary_key=True)

    numero: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
    )

    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id"),
        nullable=True,
    )

    data: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="Em andamento",
    )

    observacoes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    # Memória da conversa
    estado_chat: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    cliente: Mapped[Cliente | None] = relationship()

    itens: Mapped[list["ItemProposta"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="proposta",
    )

    mensagens: Mapped[list["MensagemConversa"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="proposta",
    )


class ItemProposta(Base):
    __tablename__ = "itens_proposta"

    id: Mapped[int] = mapped_column(primary_key=True)

    proposta_id: Mapped[int] = mapped_column(
        ForeignKey("propostas.id")
    )

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produtos.id")
    )

    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3)
    )

    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    proposta: Mapped[Proposta] = relationship(
        back_populates="itens"
    )

    produto: Mapped[Produto] = relationship()


class HistoricoPreco(Base):
    __tablename__ = "historico_precos"

    id: Mapped[int] = mapped_column(primary_key=True)

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id")
    )

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produtos.id")
    )

    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3)
    )

    valor_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )

    data: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    cliente: Mapped[Cliente] = relationship()
    produto: Mapped[Produto] = relationship()


class MensagemConversa(Base):
    __tablename__ = "mensagens_conversa"

    id: Mapped[int] = mapped_column(primary_key=True)

    proposta_id: Mapped[int] = mapped_column(
        ForeignKey("propostas.id")
    )

    usuario: Mapped[str] = mapped_column(String(40))
    mensagem: Mapped[str] = mapped_column(Text)

    data: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    proposta: Mapped[Proposta] = relationship(
        back_populates="mensagens"
    )