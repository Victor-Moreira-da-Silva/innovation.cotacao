from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.entities import Produto, Proposta
from app.models.intencoes import Acao, Intencao, ItemInterpretado
from app.services.estado_chat import Aguardando, EstadoChat, ItemChat, obter_estado, salvar_estado
from app.services.historico_service import sugestao_preco
from app.services.interpretador import interpretar
from app.services.proposta_service import adicionar_item, finalizar_proposta
from app.services.resolver_produtos import resolver_produto

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Orquestra o atendimento comercial conversacional de propostas."""

    def __init__(self, db: Session):
        self.db = db

    def processar(self, proposta: Proposta, mensagem: str) -> dict[str, str]:
        estado = obter_estado(proposta)
        estado.registrar("usuario", mensagem)
        intencao = interpretar(mensagem)

        try:
            if estado.aguardando:
                resposta = self._processar_pendencia(proposta, estado, intencao)
            else:
                resposta = self._processar_intencao(proposta, estado, intencao)
            estado.registrar("assistente", resposta["resposta"])
            salvar_estado(proposta, estado)
            self.db.commit()
            return resposta
        except (InvalidOperation, ValueError) as exc:
            logger.info("Mensagem inválida no chat da proposta %s: %s", proposta.id, exc)
            self.db.rollback()
            return {"status": "erro", "resposta": "Não consegui entender o valor informado. Pode repetir apenas o número?"}
        except Exception:
            logger.exception("Erro ao processar chat da proposta %s", proposta.id)
            self.db.rollback()
            return {"status": "erro", "resposta": "Ocorreu um erro ao processar sua mensagem. Tente novamente."}

    def _processar_intencao(self, proposta: Proposta, estado: EstadoChat, intencao: Intencao) -> dict[str, str]:
        if intencao.acao == Acao.FINALIZAR:
            finalizar_proposta(self.db, proposta)
            return {"status": "finalizada", "resposta": "Proposta finalizada. Você já pode gerar o PDF."}
        if intencao.acao == Acao.REMOVER:
            return self._remover_item(proposta, estado, intencao.alvo)
        if intencao.acao == Acao.TROCAR:
            return self._trocar_produto(proposta, intencao)
        if intencao.acao == Acao.CANCELAR:
            estado.itens.clear(); estado.item = None; estado.opcoes.clear(); estado.aguardando = None
            return {"status": "cancelado", "resposta": "Pendências canceladas. Qual produto deseja informar agora?"}
        if intencao.acao in {Acao.INFORMAR_PRECO, Acao.INFORMAR_QUANTIDADE}:
            return {"status": "contexto", "resposta": "Informe também o produto, por exemplo: 20 água sanitária 18,90."}
        if intencao.acao != Acao.ADICIONAR or not intencao.itens:
            return {"status": "desconhecida", "resposta": "Pode me dizer os produtos e quantidades da proposta?"}

        for item in intencao.itens:
            pendencia = self._adicionar_item_interpretado(estado, item)
            if pendencia:
                return pendencia
        return self._perguntar_proxima_pendencia(proposta, estado)

    def _processar_pendencia(self, proposta: Proposta, estado: EstadoChat, intencao: Intencao) -> dict[str, str]:
        if intencao.acao == Acao.CANCELAR:
            estado.aguardando = None; estado.item = None; estado.opcoes.clear()
            return {"status": "cancelado", "resposta": "Tudo bem, cancelei essa pendência. Qual o próximo produto?"}
        if estado.aguardando == Aguardando.PRODUTO:
            return self._selecionar_produto(estado, intencao)

        item = self._item_atual(estado)
        if not item:
            estado.aguardando = None
            return {"status": "ok", "resposta": "Não há pendências. Qual produto deseja adicionar?"}

        if estado.aguardando == Aguardando.QUANTIDADE:
            item.quantidade = intencao.quantidade or intencao.valor or self._decimal(intencao.texto_original)
            estado.aguardando = None
            return self._perguntar_proxima_pendencia(proposta, estado)

        if estado.aguardando == Aguardando.CONFIRMAR_PRECO:
            if intencao.acao == Acao.CONFIRMAR:
                item.valor = item.sugestao_valor
                estado.aguardando = None
                return self._perguntar_proxima_pendencia(proposta, estado)
            if intencao.acao == Acao.CANCELAR:
                estado.aguardando = Aguardando.VALOR
                return {"status": "valor", "resposta": f"Qual valor unitário devo usar para {item.descricao}?"}
            item.valor = intencao.valor or self._decimal(intencao.texto_original)
            estado.aguardando = None
            return self._perguntar_proxima_pendencia(proposta, estado)

        if estado.aguardando == Aguardando.VALOR:
            if intencao.acao == Acao.CONFIRMAR and item.sugestao_valor is not None:
                item.valor = item.sugestao_valor
            else:
                item.valor = intencao.valor or self._decimal(intencao.texto_original)
            estado.aguardando = None
            return self._perguntar_proxima_pendencia(proposta, estado)

        estado.aguardando = None
        return self._processar_intencao(proposta, estado, intencao)

    def _adicionar_item_interpretado(self, estado: EstadoChat, item: ItemInterpretado) -> dict[str, str] | None:
        resultado = resolver_produto(self.db, item.descricao)
        chat_item = ItemChat(item.texto_original, item.descricao, item.quantidade, item.valor, item.marca, item.produto_id)
        if resultado.encontrado:
            chat_item.produto_id = resultado.encontrado.id
            chat_item.descricao = resultado.encontrado.descricao
            estado.itens.append(chat_item)
            return None
        if resultado.opcoes:
            estado.aguardando = Aguardando.PRODUTO
            estado.opcoes = [p.id for p in resultado.opcoes]
            estado.item = chat_item
            lista = "\n".join(f"{i}. {p.descricao}" for i, p in enumerate(resultado.opcoes, start=1))
            return {"status": "escolher_produto", "resposta": f"Encontrei vários produtos:\n\n{lista}\n\nInforme o número."}
        return {"status": "nao_encontrado", "resposta": f"Não encontrei '{item.descricao}'. Pode informar outro nome, marca ou abreviação?"}

    def _perguntar_proxima_pendencia(self, proposta: Proposta, estado: EstadoChat) -> dict[str, str]:
        for indice, item in enumerate(estado.itens):
            estado.indice = indice
            if item.quantidade is None:
                estado.aguardando = Aguardando.QUANTIDADE
                return {"status": "quantidade", "resposta": f"Qual a quantidade de {item.descricao}?"}
            if item.valor is None:
                sugestao = sugestao_preco(self.db, proposta.cliente_id, item.produto_id) if item.produto_id else None
                if sugestao:
                    item.sugestao_valor = Decimal(str(sugestao["sugerido"]))
                    estado.aguardando = Aguardando.CONFIRMAR_PRECO
                    return {"status": "sugestao", "resposta": f"Último preço encontrado para {item.descricao}: R$ {item.sugestao_valor:.2f}. Deseja utilizar?"}
                estado.aguardando = Aguardando.VALOR
                return {"status": "valor", "resposta": f"Qual o valor unitário de {item.descricao}?"}

        adicionados = 0
        for item in estado.itens:
            if item.produto_id and item.quantidade is not None and item.valor is not None:
                adicionar_item(self.db, proposta, item.produto_id, item.quantidade, item.valor)
                adicionados += 1
        estado.itens.clear(); estado.indice = 0; estado.aguardando = None; estado.opcoes.clear(); estado.item = None
        return {"status": "adicionado", "resposta": f"{adicionados} item(ns) adicionados com sucesso. Deseja adicionar mais algum produto ou finalizar a proposta?"}

    def _selecionar_produto(self, estado: EstadoChat, intencao: Intencao) -> dict[str, str]:
        escolha = intencao.numero or int(self._decimal(intencao.texto_original))
        if escolha < 1 or escolha > len(estado.opcoes):
            return {"status": "erro", "resposta": "Opção inválida. Informe um dos números listados."}
        produto = self.db.get(Produto, estado.opcoes[escolha - 1])
        if not produto or not estado.item:
            estado.aguardando = None
            return {"status": "erro", "resposta": "Não consegui recuperar a opção escolhida. Informe o produto novamente."}
        estado.item.produto_id = produto.id
        estado.item.descricao = produto.descricao
        estado.itens.append(estado.item)
        estado.item = None; estado.opcoes.clear(); estado.aguardando = None
        return {"status": "ok", "resposta": "Produto selecionado."}

    def _remover_item(self, proposta: Proposta, estado: EstadoChat, alvo: str | None) -> dict[str, str]:
        if estado.itens:
            removido = estado.itens.pop() if not alvo or "ultimo" in alvo else estado.itens.pop(0)
            estado.aguardando = None
            return {"status": "removido", "resposta": f"Removi {removido.descricao}."}
        if proposta.itens:
            item = proposta.itens[-1]
            descricao = item.produto.descricao
            proposta.valor_total -= item.valor_total
            self.db.delete(item)
            return {"status": "removido", "resposta": f"Removi {descricao} da proposta."}
        return {"status": "vazio", "resposta": "Não há itens para remover."}

    def _trocar_produto(self, proposta: Proposta, intencao: Intencao) -> dict[str, str]:
        if not intencao.alvo or not intencao.substituto:
            return {"status": "erro", "resposta": "Informe no formato: troca produto atual por novo produto."}
        novo = resolver_produto(self.db, intencao.substituto)
        if not novo.encontrado:
            return {"status": "escolher_produto", "resposta": "Encontrei mais de uma opção para o novo produto. Informe a troca como um novo item, por favor."}
        alvo_norm = intencao.alvo.lower()
        for item in proposta.itens:
            if alvo_norm in item.produto.descricao.lower():
                item.produto_id = novo.encontrado.id
                return {"status": "trocado", "resposta": f"Troquei para {novo.encontrado.descricao}."}
        return {"status": "nao_encontrado", "resposta": "Não encontrei esse produto nos itens já adicionados."}

    def _item_atual(self, estado: EstadoChat) -> ItemChat | None:
        return estado.itens[estado.indice] if 0 <= estado.indice < len(estado.itens) else None

    def _decimal(self, texto: str) -> Decimal:
        return Decimal(texto.lower().replace("r$", "").strip().replace(",", "."))