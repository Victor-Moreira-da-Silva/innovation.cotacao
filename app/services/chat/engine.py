from sqlalchemy.orm import Session

from app.models.entities import Proposta

from app.services.interpretador import interpretar
from app.services.resolver_produtos import resolver_produto
from app.services.estado_chat import (
    obter_estado,
    salvar_estado,
)

from app.services.proposta_service import adicionar_item
from app.services.historico_service import sugestao_preco


class ConversationEngine:

    def __init__(self, db: Session):
        self.db = db

    def processar(
        self,
        proposta: Proposta,
        mensagem: str
    ):

        estado = obter_estado(proposta)

        # 1 - Interpretar mensagem
        itens = interpretar(mensagem)

        # 2 - Se usuário respondeu alguma pendência
        if estado["aguardando"]:

            resposta = self._processar_pendencia(
                proposta,
                estado,
                mensagem
            )

            salvar_estado(proposta, estado)
            self.db.commit()

            return resposta

        # 3 - Novo pedido
        for item in itens:

            resultado = resolver_produto(
                self.db,
                item.produto
            )

            if resultado.encontrado is None:

                if resultado.opcoes:

                    estado["aguardando"] = "produto"

                    estado["opcoes"] = [
                        p.id for p in resultado.opcoes
                    ]

                    estado["item"] = item.__dict__

                    salvar_estado(proposta, estado)

                    self.db.commit()

                    lista = []

                    for i, p in enumerate(resultado.opcoes):

                        lista.append(
                            f"{i+1}. {p.descricao}"
                        )

                    return {
                        "status": "escolher_produto",
                        "resposta":
                            "Encontrei vários produtos:\n\n"
                            + "\n".join(lista)
                    }

                return {
                    "status": "erro",
                    "resposta": f"Não encontrei '{item.produto}'."
                }

            item.produto_id = resultado.encontrado.id
            item.descricao = resultado.encontrado.descricao

            estado["itens"].append(item.__dict__)

        # 4 - Perguntar o que falta

        for i, item in enumerate(estado["itens"]):

            if item["quantidade"] is None:

                estado["indice"] = i
                estado["aguardando"] = "quantidade"

                salvar_estado(proposta, estado)
                self.db.commit()

                return {
                    "status": "quantidade",
                    "resposta": f"Qual a quantidade de {item['descricao']}?"
                }

            if item["valor"] is None:

                sugestao = sugestao_preco(
                    self.db,
                    proposta.cliente_id,
                    item["produto_id"]
                )

                estado["indice"] = i
                estado["aguardando"] = "valor"

                salvar_estado(proposta, estado)
                self.db.commit()

                if sugestao:

                    return {
                        "status": "sugestao",
                        "resposta":
                            f"Último preço encontrado: "
                            f"R$ {sugestao['sugerido']:.2f}. "
                            "Deseja utilizar?"
                    }

                return {
                    "status": "valor",
                    "resposta": f"Qual o valor de {item['descricao']}?"
                }

        # 5 - Tudo completo

        for item in estado["itens"]:

            adicionar_item(
                self.db,
                proposta,
                item["produto_id"],
                item["quantidade"],
                item["valor"]
            )

        estado["itens"] = []
        estado["aguardando"] = None
        estado["indice"] = 0

        salvar_estado(proposta, estado)

        self.db.commit()

        return {
            "status": "ok",
            "resposta":
                "Itens adicionados com sucesso.\n\n"
                "Deseja adicionar mais algum produto?"
        }

    def _processar_pendencia(
        self,
        proposta,
        estado,
        mensagem
    ):

        indice = estado["indice"]

        item = estado["itens"][indice]

        if estado["aguardando"] == "quantidade":

            from decimal import Decimal

            item["quantidade"] = Decimal(
                mensagem.replace(",", ".")
            )

            estado["aguardando"] = None

            return {
                "status": "ok",
                "resposta": "Quantidade registrada."
            }

        if estado["aguardando"] == "valor":

            from decimal import Decimal

            texto = mensagem.lower()

            if texto in [
                "sim",
                "usar",
                "usa",
                "ultimo",
                "último"
            ]:

                sugestao = sugestao_preco(
                    self.db,
                    proposta.cliente_id,
                    item["produto_id"]
                )

                if sugestao:

                    item["valor"] = sugestao["sugerido"]

                    estado["aguardando"] = None

                    return {
                        "status": "ok",
                        "resposta": "Preço aplicado."
                    }

            item["valor"] = Decimal(
                mensagem.replace(",", ".")
            )

            estado["aguardando"] = None

            return {
                "status": "ok",
                "resposta": "Preço registrado."
            }

        if estado["aguardando"] == "produto":

            try:

                escolha = int(mensagem)

            except:

                return {
                    "status": "erro",
                    "resposta": "Informe apenas o número do produto."
                }

            produtos = estado["opcoes"]

            if escolha < 1 or escolha > len(produtos):

                return {
                    "status": "erro",
                    "resposta": "Opção inválida."
                }

            produto = self.db.get(
                __import__(
                    "app.models.entities",
                    fromlist=["Produto"]
                ).Produto,
                produtos[escolha - 1]
            )

            estado["item"]["produto_id"] = produto.id
            estado["item"]["descricao"] = produto.descricao

            estado["itens"].append(
                estado["item"]
            )

            estado.pop("item")
            estado.pop("opcoes")

            estado["aguardando"] = None

            return {
                "status": "ok",
                "resposta": "Produto selecionado."
            }

        return {
            "status": "ok"
        }