"""Ayuda para las pruebas: sube una guía de remisión de ejemplo (PDF mínimo) como evidencia temporal."""
import os
import tempfile

os.environ.setdefault("AVISMART_ADJUNTOS", tempfile.mkdtemp(prefix="avismart_adjuntos_"))

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def guia(client, headers) -> int:
    r = client.post("/api/adjuntos/temporales", headers=headers, data={"seccion": "GUIA"}, files={"archivo": ("guia.pdf", PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()["id"]
