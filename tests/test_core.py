from app.core import Document, Field, compare, normalize

FIELDS = [Field("venda", "Venda", ("venda",), "number"), Field("valor", "Valor", ("valor pago",), "money")]

def test_correspondentes():
    docs = [Document(str(i), [("Página 1", f"Venda: 4504\nValor pago: {v}")]) for i, v in enumerate(["R$ 1.200,50", "1200,50", "R$ 1.200,50"])]
    assert compare(docs, FIELDS)["summary"]["correspondente"] == 2

def test_divergencia_e_ausencia():
    docs = [Document(str(i), [("P1", t)]) for i, t in enumerate(["Venda: 4504\nValor pago: 10,00", "Venda: 4505\nValor pago: 10,00", "Venda: 4504"])]
    r = compare(docs, FIELDS)
    assert r["summary"]["divergente"] == 1
    assert r["summary"]["ausente"] == 1

def test_ambiguidade():
    docs = [Document(str(i), [("P1", t)]) for i, t in enumerate(["Venda: 1\nVenda: 2", "Venda: 1", "Venda: 1"])]
    assert compare(docs, FIELDS)["summary"]["ambíguo"] == 1

def test_normalizacao():
    assert normalize("R$ 1.234,56", "money") == "1234.56"
    assert normalize("31/12/2025", "date") == "2025-12-31"
