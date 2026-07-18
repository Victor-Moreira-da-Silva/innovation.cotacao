from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.entities import Proposta


def gerar_pdf(proposta: Proposta) -> bytes:
    buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    pdf.setFont("Helvetica-Bold", 16); pdf.drawString(40, y, f"Proposta {proposta.numero}"); y -= 30
    pdf.setFont("Helvetica", 10); pdf.drawString(40, y, f"Cliente: {proposta.cliente.razao_social if proposta.cliente else '-'}"); y -= 25
    pdf.drawString(40, y, "Qtd  Produto  Valor Unit.  Total"); y -= 15
    for item in proposta.itens:
        pdf.drawString(40, y, f"{item.quantidade}  {item.produto.descricao}  R$ {item.valor_unitario:.2f}  R$ {item.valor_total:.2f}"); y -= 15
    y -= 10; pdf.setFont("Helvetica-Bold", 12); pdf.drawString(40, y, f"Total: R$ {proposta.valor_total:.2f}")
    if proposta.observacoes:
        y -= 25; pdf.setFont("Helvetica", 10); pdf.drawString(40, y, f"Observações: {proposta.observacoes}")
    pdf.showPage(); pdf.save(); buffer.seek(0)
    return buffer.read()
