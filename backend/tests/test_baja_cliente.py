"""Eliminación definitiva de un cliente: solo suspendido, con confirmación, respaldo y exportación."""
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.evidencia_prueba import guia
from app.db import Base, get_db
from app.main import app
from app.models import Alerta, Configuracion, Galpon, Granja, Lote, Organizacion, RegistroDiario, SolicitudContacto, Usuario
from app.security import hash_password

CLAVE = "ClavePrueba123"


class BajaClienteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entorno = patch.dict(os.environ, {"AVISMART_RESPALDOS": self.tmp.name, "AVISMART_PROXIES_CONFIABLES": "testclient"})
        self.entorno.start()
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
        db.add(Usuario(nombre="Dueño", email="duenio@avismart.pe", password_hash=hash_password(CLAVE), rol="PLATAFORMA", activo=1, debe_cambiar_clave=0))
        self.ids = {}
        for nombre, correo in (("Avícola Andina", "ana@andina.pe"), ("Granja Sur", "luis@sur.pe")):
            org = Organizacion(nombre=nombre, estado="ACTIVA", creada_en=datetime.now())
            db.add(org)
            db.flush()
            usuario = Usuario(nombre=nombre, email=correo, password_hash=hash_password(CLAVE), rol="PRODUCTOR", activo=1, debe_cambiar_clave=0, organizacion_id=org.id)
            granja = Granja(nombre=f"Granja {nombre}", ubicacion="Puno", organizacion_id=org.id)
            db.add_all([usuario, granja])
            db.flush()
            galpon = Galpon(granja_id=granja.id, nombre="Galpón 1", capacidad=5000)
            db.add(galpon)
            db.flush()
            lote = Lote(galpon_id=galpon.id, linea="Cobb", fecha_ingreso=date.today() - timedelta(days=10), poblacion_inicial=3000, estado="ACTIVO")
            db.add(lote)
            db.flush()
            db.add(RegistroDiario(lote_id=lote.id, usuario_id=usuario.id, fecha=date.today(), mortalidad=2, alimento_kg=100, agua_l=200, peso_muestra_g=300))
            db.add(Alerta(lote_id=lote.id, tipo="SALUD", mensaje="Prueba", estado="ATENDIDA", creada_en=datetime.now(), atendida_por=usuario.id))
            db.add(Configuracion(clave=f"mortalidad_diaria:{org.id}", valor="15"))
            self.ids[nombre] = org.id
        db.commit()
        db.close()
        self.client = TestClient(app)
        token = self.client.post("/api/auth/login", json={"email": "duenio@avismart.pe", "password": CLAVE}).json()["token"]
        self.h = {"Authorization": f"Bearer {token}"}
        self.andina = self.ids["Avícola Andina"]

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.entorno.stop()
        self.tmp.cleanup()

    def eliminar(self, confirmacion):
        return self.client.post(f"/api/plataforma/organizaciones/{self.andina}/eliminar", json={"confirmacion": confirmacion}, headers=self.h)

    def suspender(self):
        self.client.patch(f"/api/plataforma/organizaciones/{self.andina}", json={"estado": "SUSPENDIDA"}, headers=self.h)

    def test_solo_se_elimina_un_cliente_suspendido(self):
        r = self.eliminar("Avícola Andina")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Primero suspende", r.json()["detail"])

    def test_exige_escribir_el_nombre(self):
        self.suspender()
        r = self.eliminar("otro nombre")
        self.assertEqual(r.status_code, 400)
        self.assertIn("escribe exactamente el nombre", r.json()["detail"])
        db = self.Session()
        self.assertIsNotNone(db.get(Organizacion, self.andina), "no se borra nada si no confirma")
        db.close()

    def test_elimina_solo_ese_cliente_con_respaldo_y_exportacion(self):
        self.suspender()
        r = self.eliminar("  avícola andina ")
        self.assertEqual(r.status_code, 200, r.text)
        cuerpo = r.json()

        respaldo = Path(self.tmp.name) / cuerpo["respaldo"]
        self.assertTrue(respaldo.exists())
        copia = sqlite3.connect(respaldo)
        self.assertEqual(copia.execute("select count(*) from organizaciones").fetchone()[0], 2, "el respaldo es de antes de borrar")
        copia.close()

        exportacion = Path(self.tmp.name) / "clientes" / cuerpo["exportacion"]
        datos = json.loads(exportacion.read_text(encoding="utf-8"))
        self.assertEqual(datos["cliente"]["nombre"], "Avícola Andina")
        self.assertEqual(len(datos["tablas"]["lotes"]), 1)
        self.assertEqual(len(datos["tablas"]["registros_diarios"]), 1)
        self.assertNotIn("password_hash", json.dumps(datos), "la exportación no incluye claves")
        self.assertEqual(cuerpo["datos"]["cliente"]["nombre"], "Avícola Andina")

        db = self.Session()
        self.assertIsNone(db.get(Organizacion, self.andina))
        self.assertEqual(db.query(Usuario).filter_by(email="ana@andina.pe").count(), 0)
        self.assertEqual(db.query(Lote).count(), 1, "el lote del otro cliente sigue")
        self.assertEqual(db.query(RegistroDiario).count(), 1)
        self.assertEqual(db.query(Alerta).count(), 1)
        self.assertIsNone(db.get(Configuracion, f"mortalidad_diaria:{self.andina}"))
        self.assertIsNotNone(db.get(Organizacion, self.ids["Granja Sur"]))
        db.close()
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).status_code, 200)

    def test_la_solicitud_del_cliente_eliminado_queda_dada_de_baja(self):
        db = self.Session()
        solicitud = SolicitudContacto(nombre="Ana", email="ana@andina.pe", empresa="Avícola Andina", pais="Perú", motivo="COMERCIAL",
                                      mensaje="Quiero ordenar mis galpones", estado="CLIENTE", creada_en=datetime.now())
        db.add(solicitud)
        db.flush()
        db.get(Organizacion, self.andina).solicitud_id = solicitud.id
        db.commit()
        solicitud_id = solicitud.id
        db.close()
        self.suspender()
        self.assertEqual(self.eliminar("Avícola Andina").status_code, 200)
        db = self.Session()
        self.assertEqual(db.get(SolicitudContacto, solicitud_id).estado, "BAJA", "ya no figura como cliente vigente")
        db.close()

    def test_correo_que_ya_es_cliente_no_crea_duplicado(self):
        db = self.Session()
        db.add(SolicitudContacto(nombre="Ana", email="ana@andina.pe", empresa="Andina Dos", pais="Perú", motivo="COMERCIAL",
                                 mensaje="Quiero volver a usar AviSmart", estado="NUEVA", creada_en=datetime.now()))
        db.commit()
        db.close()
        self.suspender()
        lista = self.client.get("/api/plataforma/solicitudes", headers=self.h).json()
        existente = lista[0]["cuenta_existente"]
        self.assertEqual(existente["organizacion"]["nombre"], "Avícola Andina")
        self.assertEqual(existente["organizacion"]["estado"], "SUSPENDIDA")
        r = self.client.post("/api/plataforma/organizaciones", headers=self.h,
                             json={"nombre": "Andina Dos", "productor_nombre": "Ana", "productor_email": "ana@andina.pe", "solicitud_id": lista[0]["id"]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("«Avícola Andina» (suspendido)", r.json()["detail"])
        db = self.Session()
        self.assertEqual(db.query(Organizacion).count(), 2, "no se creó un cliente a medias")
        db.close()

    def test_personal_con_correo_repetido_sin_revelar_otros_clientes(self):
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        productor = {"Authorization": f"Bearer {token}"}
        alta = lambda email, h: self.client.post("/api/usuarios", headers=h, json={"nombre": "Pedro Quispe", "email": email, "rol": "OPERARIO"})  # noqa: E731
        self.assertEqual(alta("pedro@sur.pe", productor).status_code, 200)

        propio = alta("pedro@sur.pe", productor)
        self.assertEqual(propio.status_code, 400)
        self.assertIn("ya tiene una cuenta en tu equipo", propio.json()["detail"])

        ajeno = alta("ana@andina.pe", productor)
        self.assertEqual(ajeno.status_code, 400)
        self.assertIn("ya está registrado en AviSmart", ajeno.json()["detail"])
        self.assertNotIn("Andina", ajeno.json()["detail"], "el productor no ve el nombre de otro cliente")

        sur = self.ids["Granja Sur"]
        plataforma = self.client.post(f"/api/plataforma/organizaciones/{sur}/usuarios", headers=self.h,
                                      json={"nombre": "Ana Ruiz", "email": "ana@andina.pe", "rol": "VETERINARIO"})
        self.assertEqual(plataforma.status_code, 400)
        self.assertIn("«Avícola Andina»", plataforma.json()["detail"], "la plataforma sí sabe de quién es")

    def test_origen_cuando_escribio_otra_persona(self):
        db = self.Session()
        for nombre, correo in (("Juan Empleado", "juan@norte.pe"), ("Rosa Dueña", "rosa@centro.pe")):
            db.add(SolicitudContacto(nombre=nombre, email=correo, empresa="", pais="Perú", motivo="COMERCIAL",
                                     mensaje="Queremos usar AviSmart", estado="CONTACTADA", creada_en=datetime.now()))
        db.commit()
        ids = {s.email: s.id for s in db.query(SolicitudContacto)}
        db.close()
        crear = lambda nombre, email, solicitud: self.client.post("/api/plataforma/organizaciones", headers=self.h, json={  # noqa: E731
            "nombre": nombre, "productor_nombre": "Productor", "productor_email": email, "solicitud_id": solicitud}).json()["organizacion"]

        norte = crear("Granja Norte", "pedro@norte.pe", ids["juan@norte.pe"])
        self.assertEqual(norte["origen"]["nombre"], "Juan Empleado", "escribió el empleado, la cuenta es del jefe")
        self.assertEqual(norte["solicitud_id"], ids["juan@norte.pe"], "la solicitud queda enlazada igual")
        centro = crear("Granja Centro", "rosa@centro.pe", ids["rosa@centro.pe"])
        self.assertIsNone(centro["origen"], "si escribió el propio productor no hay nada que aclarar")

    def test_un_solo_productor_y_correo_sin_enie(self):
        sur = self.ids["Granja Sur"]
        alta = lambda rol, email: self.client.post(f"/api/plataforma/organizaciones/{sur}/usuarios", headers=self.h,  # noqa: E731
                                                   json={"nombre": "Juan Pérez Muñoz", "email": email, "rol": rol})
        self.assertEqual(alta("PRODUCTOR", "otro@sur.pe").status_code, 400, "el productor principal es único")
        malo = alta("OPERARIO", "perezMuñ@gmail.com")
        self.assertEqual(malo.status_code, 400)
        self.assertIn("ñ", malo.json()["detail"])
        self.assertEqual(alta("OPERARIO", "perezmunoz@gmail.com").status_code, 200)

    def test_modo_soporte_opera_como_productor_del_cliente(self):
        sur = self.ids["Granja Sur"]
        r = self.client.post(f"/api/plataforma/organizaciones/{sur}/soporte", headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        soporte = {"Authorization": f"Bearer {r.json()['token']}"}

        yo = self.client.get("/api/me", headers=soporte).json()
        self.assertTrue(yo["soporte"])
        self.assertEqual(yo["rol"], "PRODUCTOR")
        self.assertEqual(yo["organizacion"]["id"], sur)

        granja = self.client.post("/api/granjas", headers=soporte, json={"nombre": "Granja nueva del sur", "ubicacion": "Ayaviri"})
        self.assertEqual(granja.status_code, 201, granja.text)
        db = self.Session()
        self.assertEqual(db.query(Granja).filter_by(nombre="Granja nueva del sur").one().organizacion_id, sur, "queda en el cliente correcto")
        self.assertEqual(db.query(Usuario).filter_by(rol="PRODUCTOR", organizacion_id=sur).count(), 1, "no crea cuentas nuevas")
        db.close()
        granjas = self.client.get("/api/granjas", headers=soporte).json()
        self.assertTrue(all("Andina" not in g["nombre"] for g in granjas), "solo ve los datos de ese cliente")

        self.assertEqual(self.client.get("/api/plataforma/organizaciones", headers=soporte).status_code, 403, "en soporte no es plataforma")
        cambio = self.client.post("/api/auth/cambiar-clave", headers=soporte, json={"clave_actual": CLAVE, "clave_nueva": "OtraClave#1234"})
        self.assertEqual(cambio.status_code, 403)
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        self.assertEqual(self.client.post(f"/api/plataforma/organizaciones/{sur}/soporte", headers={"Authorization": f"Bearer {token}"}).status_code, 403,
                         "un productor no puede abrir el modo soporte")

        accesos = self.client.get(f"/api/plataforma/organizaciones/{sur}/accesos", headers=self.h).json()
        entradas = [a for a in accesos if a["evento"] == "Entrada en modo soporte"]
        self.assertEqual(len(entradas), 1, "RN-21: la entrada en modo soporte queda registrada")
        self.assertIn("(AviSmart)", entradas[0]["usuario"])
        otro = next(i for nombre, i in self.ids.items() if i != sur)
        self.assertFalse(any(a["evento"] == "Entrada en modo soporte" for a in self.client.get(f"/api/plataforma/organizaciones/{otro}/accesos", headers=self.h).json()),
                         "no aparece en otro cliente")

    def test_ubicacion_de_la_granja_con_ubigeo_y_mapa(self):
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        prod = {"Authorization": f"Bearer {token}"}
        nueva = lambda **datos: self.client.post("/api/granjas", headers=prod, json={"nombre": "Granja San Fernando", **datos})  # noqa: E731

        ok = nueva(departamento="Puno", provincia="San Román", distrito="Juliaca", latitud=-15.4839, longitud=-70.1333)
        self.assertEqual(ok.status_code, 201, ok.text)
        self.assertEqual(ok.json()["ubicacion"], "Juliaca, San Román, Puno", "la ubicación legible se arma sola")
        self.assertEqual(ok.json()["latitud"], -15.4839)
        self.assertEqual(nueva(departamento="Puno", provincia="Puno", distrito="Puno").json()["ubicacion"], "Puno",
                         "no repite el nombre cuando distrito, provincia y departamento se llaman igual")

        self.assertIn("departamento, provincia y distrito", nueva(departamento="Puno", provincia="", distrito="").json()["detail"])
        self.assertIn("dentro del Perú", nueva(departamento="Puno", provincia="Puno", distrito="Puno", latitud=40.4, longitud=-3.7).json()["detail"])
        self.assertIn("incompleto", nueva(departamento="Puno", provincia="Puno", distrito="Puno", latitud=-15.8).json()["detail"])
        self.assertEqual(nueva(ubicacion="Km 5 carretera a Lampa").status_code, 201, "las granjas antiguas siguen con texto libre")
        self.assertEqual(nueva().status_code, 400)

    def test_galpones_numerados_hasta_diez(self):
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        prod = {"Authorization": f"Bearer {token}"}
        granja = self.client.post("/api/granjas", headers=prod, json={"nombre": "Granja nueva", "ubicacion": "Lampa"}).json()["id"]
        alta = lambda: self.client.post(f"/api/granjas/{granja}/galpones", headers=prod, json={"nombre": "Lo que sea", "capacidad": 3000})  # noqa: E731
        nombres = [alta().json()["nombre"] for _ in range(10)]
        self.assertEqual(nombres[0], "Galpón 01", "el nombre escrito se ignora: se numera solo")
        self.assertEqual(nombres[-1], "Galpón 10")
        undecimo = alta()
        self.assertEqual(undecimo.status_code, 400)
        self.assertIn("hasta 10 galpones", undecimo.json()["detail"])
        galpon = self.client.get("/api/granjas", headers=prod).json()
        g01 = next(g for x in galpon if x["id"] == granja for g in x["galpones"] if g["nombre"] == "Galpón 01")
        editado = self.client.put(f"/api/galpones/{g01['id']}", headers=prod, json={"nombre": "Otro nombre", "capacidad": 4500}).json()
        self.assertEqual((editado["nombre"], editado["capacidad"]), ("Galpón 01", 4500), "al editar solo cambia la capacidad")

    def test_vacunas_de_incubadora_al_abrir_el_lote(self):
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        prod = {"Authorization": f"Bearer {token}"}
        granja = self.client.post("/api/granjas", headers=prod, json={"nombre": "Granja dos", "ubicacion": "Lampa"}).json()["id"]
        galpon = self.client.post(f"/api/granjas/{granja}/galpones", headers=prod, json={"capacidad": 5000}).json()["id"]
        lote = lambda vacunas: self.client.post("/api/lotes", headers=prod, json={  # noqa: E731
            "galpon_id": galpon, "linea": "Hubbard", "fecha_ingreso": date.today().isoformat(), "proveedor": "Avinka",
            "cantidad_recibida": 3000, "descarte_llegada": 10, "peso_llegada_g": 41, "precio_pollito": 2.2, "vacunas_incubadora": vacunas,
            "adjuntos": [guia(self.client, prod)]})

        self.assertEqual(lote(["Viruela aviar"]).status_code, 400, "solo vacunas de la lista de la incubadora")
        r = lote(["Marek (HVT)", "Newcastle + Bronquitis (B1 + H120)"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["linea"], "Hubbard")
        sanidad = self.client.get(f"/api/lotes/{r.json()['id']}/sanidad", headers=prod).json()
        vacunas = {v["nombre"]: v for v in sanidad["vacunas"]}
        self.assertEqual(set(vacunas), {"Marek (HVT)", "Newcastle + Bronquitis (B1 + H120)"})
        marek = vacunas["Marek (HVT)"]
        self.assertEqual(marek["estado"], "APLICADA", "queda por revisar del veterinario")
        self.assertEqual(marek["fecha_aplicacion"], date.today().isoformat())
        self.assertIn("incubadora (Avinka)", marek["nota_aplicacion"])

    def test_celular_opcional_de_peru(self):
        from fastapi import HTTPException

        from app.main import _telefono_peru

        self.assertIsNone(_telefono_peru(""))
        self.assertEqual(_telefono_peru("987 654 321"), "987654321")
        self.assertEqual(_telefono_peru("+51 987-654-321"), "987654321")
        for malo in ("12345", "887654321", "9876543210"):
            with self.assertRaises(HTTPException):
                _telefono_peru(malo)

    def test_solo_la_plataforma_puede_eliminar(self):
        self.suspender()
        token = self.client.post("/api/auth/login", json={"email": "luis@sur.pe", "password": CLAVE}).json()["token"]
        r = self.client.post(f"/api/plataforma/organizaciones/{self.andina}/eliminar", json={"confirmacion": "Avícola Andina"},
                             headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
