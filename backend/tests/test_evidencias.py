"""Evidencias de la apertura del lote: tipos permitidos, tamaño, guía obligatoria y aislamiento entre clientes."""
import unittest
from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import PDF, guia
from app.db import Base, get_db
from app.main import app
from app.models import Galpon, Granja, Organizacion, Usuario
from app.security import hash_password

CLAVE = "Clave#Prueba1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


class EvidenciasTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(self.engine)

        def db_prueba():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = db_prueba
        db = self.Session()
        self.galpon = {}
        for clave in ("a", "b"):
            org = Organizacion(nombre=f"Cliente {clave}", estado="ACTIVA", creada_en=datetime.now())
            db.add(org)
            db.flush()
            db.add(Usuario(nombre="Productor", email=f"prod@{clave}.pe", password_hash=hash_password(CLAVE), rol="PRODUCTOR", activo=1, debe_cambiar_clave=0, organizacion_id=org.id))
            granja = Granja(nombre="Granja", ubicacion="Puno", organizacion_id=org.id)
            db.add(granja)
            db.flush()
            galpon = Galpon(granja_id=granja.id, nombre="Galpón 01", capacidad=5000)
            db.add(galpon)
            db.flush()
            self.galpon[clave] = galpon.id
        db.commit()
        db.close()
        self.client = TestClient(app)
        self.h = {c: {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": f"prod@{c}.pe", "password": CLAVE}).json()["token"]} for c in ("a", "b")}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()

    def subir(self, quien, seccion, nombre, contenido, tipo="application/octet-stream"):
        return self.client.post("/api/adjuntos/temporales", headers=self.h[quien], data={"seccion": seccion}, files={"archivo": (nombre, contenido, tipo)})

    def abrir(self, quien, adjuntos):
        return self.client.post("/api/lotes", headers=self.h[quien], json={
            "galpon_id": self.galpon[quien], "linea": "Cobb 500", "fecha_ingreso": date.today().isoformat(), "proveedor": "San Fernando",
            "cantidad_recibida": 3000, "descarte_llegada": 0, "peso_llegada_g": 42, "precio_pollito": 2.3, "adjuntos": adjuntos})

    def test_solo_fotos_y_pdf_reales_de_hasta_5_mb(self):
        self.assertIn("Solo se aceptan", self.subir("a", "GUIA", "guia.pdf", b"MZ\x90\x00 programa").json()["detail"], "la extensión no basta")
        self.assertIn("5 MB", self.subir("a", "RECEPCION", "foto.png", PNG + b"0" * (5 * 1024 * 1024)).json()["detail"])
        self.assertEqual(self.subir("a", "OTRA", "foto.png", PNG).status_code, 400)
        ok = self.subir("a", "RECEPCION", "../../foto <x>.png", PNG)
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["tipo"], "image/png")
        self.assertNotIn("/", ok.json()["nombre"])

    def test_guia_obligatoria_y_archivos_de_cada_cliente(self):
        foto = self.subir("a", "RECEPCION", "pollitos.png", PNG).json()["id"]
        self.assertIn("guía de remisión", self.abrir("a", [foto]).json()["detail"])
        ajena = guia(self.client, self.h["b"])
        self.assertIn("guía de remisión", self.abrir("a", [foto, ajena]).json()["detail"], "no puede usar la guía de otro cliente")
        lote = self.abrir("a", [foto, guia(self.client, self.h["a"])])
        self.assertEqual(lote.status_code, 200, lote.text)
        lista = self.client.get(f"/api/lotes/{lote.json()['id']}/adjuntos", headers=self.h["a"]).json()
        self.assertEqual(sorted(a["seccion"] for a in lista["adjuntos"]), ["GUIA", "RECEPCION"])
        guia_id = next(a["id"] for a in lista["adjuntos"] if a["seccion"] == "GUIA")
        archivo = self.client.get(f"/api/adjuntos/{guia_id}/archivo", headers=self.h["a"])
        self.assertEqual(archivo.content, PDF)
        self.assertEqual(self.client.get(f"/api/adjuntos/{guia_id}/archivo", headers=self.h["b"]).status_code, 404, "otro cliente no lo ve")
        self.assertIn("obligatoria", self.client.delete(f"/api/adjuntos/{guia_id}", headers=self.h["a"]).json()["detail"])

    def test_evidencias_del_registro_del_dia(self):
        lote = self.abrir("a", [guia(self.client, self.h["a"])]).json()["id"]
        db = self.Session()
        org = db.query(Usuario).filter_by(email="prod@a.pe").one().organizacion_id
        db.add(Usuario(nombre="Operario", email="ope@a.pe", password_hash=hash_password(CLAVE), rol="OPERARIO", activo=1, debe_cambiar_clave=0, organizacion_id=org))
        db.commit()
        db.close()
        ope = {"Authorization": "Bearer " + self.client.post("/api/auth/login", json={"email": "ope@a.pe", "password": CLAVE}).json()["token"]}
        subir = lambda seccion: self.client.post("/api/adjuntos/temporales", headers=ope, data={"seccion": seccion}, files={"archivo": ("foto.png", PNG, "image/png")})  # noqa: E731

        self.assertEqual(subir("GUIA").status_code, 403, "el operario no adjunta documentos de la apertura")
        bajas, pesaje = subir("BAJAS").json()["id"], subir("PESAJE").json()["id"]
        r = self.client.post(f"/api/lotes/{lote}/registros", headers=ope, json={
            "fecha": date.today().isoformat(), "mortalidad": 3, "alimento_kg": 50, "agua_l": 100, "peso_muestra_g": 42, "adjuntos": [bajas, pesaje]})
        self.assertEqual(r.status_code, 200, r.text)
        lista = self.client.get(f"/api/lotes/{lote}/adjuntos", headers=self.h["a"]).json()["adjuntos"]
        del_registro = {a["seccion"]: a["registro_fecha"] for a in lista if a["seccion"] in ("BAJAS", "PESAJE")}
        self.assertEqual(del_registro, {"BAJAS": date.today().isoformat(), "PESAJE": date.today().isoformat()})
        self.assertEqual(self.client.delete(f"/api/adjuntos/{bajas}", headers=ope).status_code, 403, "una vez guardado, el operario no lo quita")
        directo = self.client.post(f"/api/lotes/{lote}/adjuntos", headers=self.h["a"], data={"seccion": "BAJAS"}, files={"archivo": ("f.png", PNG, "image/png")})
        self.assertIn("registro del día", directo.json()["detail"])


if __name__ == "__main__":
    unittest.main()
