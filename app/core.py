"""Extração local e conferência auditável de campos em múltiplos documentos."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import csv
import re
import unicodedata

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_CHARS = 500_000
SUPPORTED = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"}

@dataclass(frozen=True)
class Field:
    key: str
    title: str
    aliases: tuple[str, ...]
    kind: str = "text"

FIELDS = [
    Field("cliente", "Cliente", ("nome do cliente", "cliente", "comprador", "titular")),
    Field("venda", "Venda", ("numero da venda", "número da venda", "venda nº", "venda", "contrato nº"), "number"),
    Field("quadra", "Quadra", ("quadra", "qd")),
    Field("lote", "Lote", ("lote", "lt")),
    Field("loteamento", "Loteamento", ("loteamento", "empreendimento")),
    Field("valor_pago", "Valor pago", ("valor pago", "total pago", "valor recebido"), "money"),
    Field("data_venda", "Data da venda", ("data da venda", "data de venda"), "date"),
    Field("id_cliente", "ID do cliente", ("id do cliente", "id cliente", "codigo do cliente")),
]

@dataclass
class Document:
    name: str
    pages: list[tuple[str, str]]

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if not unicodedata.combining(c))

def normalize(value, kind):
    value = re.sub(r"\s+", " ", value).strip()
    if kind == "number":
        return re.sub(r"\D", "", value)
    if kind == "money":
        v = re.sub(r"[^\d,.\-]", "", value)
        if "," in v:
            v = v.replace(".", "").replace(",", ".")
        try:
            return str(Decimal(v).quantize(Decimal(".01")))
        except InvalidOperation:
            pass
    if kind == "date":
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                pass
    return re.sub(r"[^\w ]", "", fold(value)).strip()

def extract_text(name, data):
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in SUPPORTED:
        raise ValueError("Formato não suportado: " + name)
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Arquivo vazio ou maior que 20 MB")
    pages = []
    if ext == ".pdf":
        import fitz
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.page_count > 300:
                raise ValueError("PDF excede 300 páginas")
            pages = [(f"Página {i+1}", p.get_text(sort=True)) for i, p in enumerate(pdf)]
    elif ext == ".docx":
        from docx import Document as Word
        doc = Word(BytesIO(data))
        lines = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            lines.extend(" | ".join(c.text for c in row.cells) for row in table.rows)
        pages = [("Documento", "\n".join(lines))]
    elif ext == ".xlsx":
        from openpyxl import load_workbook
        book = load_workbook(BytesIO(data), data_only=True, read_only=True)
        try:
            for sheet in book:
                lines = []
                for i, row in enumerate(sheet.iter_rows(max_row=min(sheet.max_row or 0, 20000), max_col=min(sheet.max_column or 0, 100), values_only=True), 1):
                    lines.append(f"Linha {i}: " + " | ".join(str(v) if v is not None else "" for v in row))
                pages.append((f"Aba {sheet.title}", "\n".join(lines)))
        finally:
            book.close()
    elif ext in {".png", ".jpg", ".jpeg"}:
        import pytesseract
        from PIL import Image, ImageOps
        im = Image.open(BytesIO(data))
        if im.width * im.height > 25_000_000:
            raise ValueError("Imagem excede limite de pixels")
        pages = [("Imagem", pytesseract.image_to_string(ImageOps.exif_transpose(im), lang="por+eng"))]
    elif ext == ".csv":
        raw = data.decode("utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(raw[:4096], delimiters=";,\t|")
        except csv.Error:
            dialect = csv.excel
        pages = [("CSV", "\n".join(" | ".join(r) for r in csv.reader(raw.splitlines(), dialect)))]
    else:
        pages = [("Texto", data.decode("utf-8-sig", errors="replace"))]
    if sum(len(t) for _, t in pages) > MAX_CHARS:
        raise ValueError("Documento excede 500 mil caracteres")
    return Document(name, pages)

def hits(doc, field):
    found = {}
    for place, text in doc.pages:
        for line_no, line in enumerate(text.splitlines(), 1):
            if len(line) > 1000:
                continue
            folded = fold(line)
            for alias in sorted(field.aliases, key=len, reverse=True):
                pat = r"(?<!\w)" + re.escape(fold(alias)) + r"\s*(?:[:=\-–]|\s{2,})\s*"
                match = re.search(pat, folded)
                if match:
                    raw = line[match.end():].strip(" :;|\t.-")
                    raw = re.split(r"\s+\|\s+|\s{3,}", raw, maxsplit=1)[0].strip()
                    if raw:
                        key = normalize(raw, field.kind)
                        found.setdefault(key, {"value": raw[:160], "normalized": key, "place": place, "line": line_no, "evidence": line[:250]})
                    break
    return list(found.values())

def compare(documents, fields=None):
    if not 3 <= len(documents) <= 20:
        raise ValueError("Selecione de 3 a 20 documentos")
    if len({d.name.casefold() for d in documents}) != len(documents):
        raise ValueError("Arquivos devem ter nomes distintos")
    report = []
    for field in fields if fields is not None else FIELDS:
        entries = [{"document": doc.name, "matches": hits(doc, field)} for doc in documents]
        if any(len(x["matches"]) > 1 for x in entries):
            status = "ambíguo"
        elif any(not x["matches"] for x in entries):
            status = "ausente"
        elif len({x["matches"][0]["normalized"] for x in entries}) == 1:
            status = "correspondente"
        else:
            status = "divergente"
        report.append({"key": field.key, "title": field.title, "status": status, "documents": entries})
    return {"documents": [d.name for d in documents], "fields": report,
            "summary": {s: sum(f["status"] == s for f in report) for s in ("correspondente", "divergente", "ausente", "ambíguo")},
            "disclaimer": "Correspondência não comprova veracidade. Confira dados críticos em fontes oficiais."}
