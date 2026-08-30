import pathlib

OUT = pathlib.Path(__file__).resolve().parent


def make_pdf(lines: list[str]) -> bytes:
    content = (
        "BT /F1 12 Tf 72 740 Td "
        + " ".join(f"({line}) Tj 0 -16 Td" for line in lines)
        + " ET"
    ).encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length " + str(len(content)).encode() + b" >> stream\n" + content + b"\nendstream\nendobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(len(out))
        out += obj
    xref = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer << /Size " + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    )
    return bytes(out)


SIMPLE = [
    "Referencia: PC-2026-100",
    "Cliente: Construtora Alfa",
    "CNPJ: 11.222.333/0001-81",
    "Total: R$ 2.297,00",
    "Produto Qtd Valor Total",
    "CIM-1 Cimento Premium 30 49.90 1497.00",
    "ARE-2 Areia Fina 10 80.00 800.00",
]
INVALID_CNPJ = [
    "Referencia: PC-7788",
    "Cliente: Ferragens Almeida",
    "CNPJ: 45.832.119/0001-10",
    "Total: R$ 550,00",
    "PAR-1 Parafuso 3/8 500 0.70 350.00",
    "POR-2 Porca sextavada 500 0.40 200.00",
]

(OUT / "pedido_simples.pdf").write_bytes(make_pdf(SIMPLE))
(OUT / "pedido_cnpj_invalido.pdf").write_bytes(make_pdf(INVALID_CNPJ))
print("fixtures geradas em", OUT)