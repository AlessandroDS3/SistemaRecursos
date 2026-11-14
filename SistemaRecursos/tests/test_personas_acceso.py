"""Pruebas con MySQL 8. Definir TEST_MYSQL_PORT para usar una instancia de pruebas."""
import os
import re
import unittest
from unittest.mock import patch

import mysql.connector
from dominio.personas import FabricaPersona
from dominio.validaciones import version_persona, version_matriz
from dominio.personas import ValidacionPersonaError
from repositorio.repositorio_persona_sql import RepositorioPersonaSQL
from repositorio.repositorio_rol_sql import RepositorioRolSQL
from servicios.servicio_rol import ServicioAplicacionRol


@unittest.skipUnless(os.environ.get("TEST_MYSQL_PORT"), "Configura la instancia MySQL de pruebas.")
class PersonasAccesoTest(unittest.TestCase):
    def setUp(self):
        from soporte_mysql import preparar_base_integracion
        preparar_base_integracion(self, catalogo=False)

    def login(self, user="admin", password="AdminPrueba2026!"):
        client = self.app.test_client()
        client.get("/login")
        with client.session_transaction() as s:
            token = s["csrf_token"]
        response = client.post("/login", data=dict(usuario=user, clave=password, csrf_token=token))
        self.assertEqual(response.status_code, 302)
        return client

    def post(self, client, path, data=None):
        client.get("/")
        with client.session_transaction() as s:
            token = s["csrf_token"]
        return client.post(path, data=dict(data or {}, csrf_token=token))

    def test_logout_independiente(self):
        uno, dos = self.login(), self.login()
        self.assertEqual(self.post(uno, "/logout").status_code, 302)
        self.assertEqual(uno.get("/personas").status_code, 302)
        self.assertEqual(dos.get("/personas").status_code, 200)

    def test_login_y_sesion_no_construyen_la_ficha_de_persona(self):
        with patch.object(FabricaPersona, 'construir', side_effect=AssertionError('El login no carga fichas')):
            for usuario, clave in (('admin', 'AdminPrueba2026!'),
                                   ('encargado1', 'EncargadoPrueba2026!'),
                                   ('usuario1', 'UsuarioPrueba2026!')):
                with self.subTest(usuario=usuario):
                    cliente = self.login(usuario, clave)
                    self.assertEqual(cliente.get('/').status_code, 200)
            cuenta = self.app.extensions['acceso'].autenticar('usuario1', 'UsuarioPrueba2026!')
            self.assertEqual(cuenta.persona.dni, '02167885')
            self.assertFalse(hasattr(cuenta.persona, 'cui'))
            self.assertFalse(hasattr(cuenta.persona, 'tipo'))

    def test_correo_de_ficha_no_interviene_en_la_autenticacion(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET correo='correo-incompleto' WHERE dni='02167885'")
        cuenta = self.app.extensions['acceso'].autenticar('usuario1', 'UsuarioPrueba2026!')
        self.assertIsNotNone(cuenta)
        with self.assertRaises(ValidacionPersonaError):
            RepositorioPersonaSQL(self.db).consultar_persona('02167885')

    def test_reserva_consulta_el_tipo_de_persona_solo_al_abrir_su_formulario(self):
        from soporte_mysql import preparar_catalogo
        preparar_catalogo(self)
        self.cn.commit()
        cliente = self.login('usuario1', 'UsuarioPrueba2026!')
        with patch.object(FabricaPersona, 'construir', wraps=FabricaPersona.construir) as construir:
            pagina = cliente.get('/reservas/nueva?recurso=1&tipo=RESERVA')
        self.assertEqual(pagina.status_code, 200)
        self.assertIn(b'data-tipo-persona="ESTUDIANTE"', pagina.data)
        self.assertEqual(construir.call_count, 1)

    def test_gestor_de_cuentas_sin_consulta_ni_acceso_a_admin(self):
        # Este rol de prueba puede administrar cuentas, pero no consultar fichas.
        with self.db.sesion(escritura=True) as c:
            c.execute("DELETE FROM rol_permiso WHERE rol='ENCARGADO_PRESTAMOS' AND permiso='PERSONAS_CONSULTAR'")
            c.execute("INSERT INTO rol_permiso VALUES ('ENCARGADO_PRESTAMOS','USUARIOS_GESTIONAR')")
        try:
            client = self.login("encargado1", "EncargadoPrueba2026!")
            self.assertEqual(client.get("/personas/98000001").status_code, 403)
            error = self.post(client, "/personas/98000001/cuenta", {"nombre_usuario": ""})
            self.assertEqual(error.status_code, 400)
            self.assertNotIn(b"admin@ejemplo.gmail", error.data)
            self.assertIn(b"Crear cuenta de acceso", error.data)
            editar = self.post(client, "/personas/98000001/cuenta/editar",
                               {"nombre_usuario": "admin", "clave": "otra-clave-test"})
            self.assertEqual(editar.status_code, 403)
            self.login()
        finally:
            with self.db.sesion(escritura=True) as c:
                c.execute("DELETE FROM rol_permiso WHERE rol='ENCARGADO_PRESTAMOS' AND permiso='USUARIOS_GESTIONAR'")
                c.execute("INSERT INTO rol_permiso VALUES ('ENCARGADO_PRESTAMOS','PERSONAS_CONSULTAR')")

    def test_base_sin_tablas_auxiliares_de_acceso(self):
        with self.db.sesion() as c:
            c.execute("SHOW TABLES")
            tablas = {next(iter(fila.values())) for fila in c.fetchall()}
        self.assertNotIn("sesion_acceso", tablas)
        self.assertNotIn("intento_acceso", tablas)
        self.assertNotIn("rol", tablas)
        self.assertNotIn("permiso", tablas)
        with self.db.sesion() as c:
            c.execute("SHOW COLUMNS FROM usuario_sistema")
            columnas = {fila["Field"] for fila in c.fetchall()}
        self.assertIn("rol", columnas)
        self.assertNotIn("activo", columnas)
        self.assertNotIn("id_rol_ref", columnas)

    def test_roles_fijos_asignacion_y_ultimo_administrador(self):
        cuentas = self.app.extensions["cuentas"]
        repo = RepositorioRolSQL(self.db)
        servicio = ServicioAplicacionRol(repo, cuentas.repositorio)
        self.assertEqual({rol.nombre.value for rol in servicio.consultar_roles()},
                         {"USUARIO", "ENCARGADO_PRESTAMOS", "ADMINISTRADOR"})
        with self.assertRaises(ValueError):
            servicio.actualizar_rol_cuenta("98000001", "USUARIO", 1)
        with self.assertRaises(ValueError):
            servicio.actualizar_rol_cuenta("02167885", "ROL_INEXISTENTE", 1)
        try:
            cuenta = servicio.actualizar_rol_cuenta("02167885", "ENCARGADO_PRESTAMOS", 1)
            self.assertEqual(cuenta.rol.nombre.value, "ENCARGADO_PRESTAMOS")
            client = self.login()
            pagina = client.get("/roles?q=02167885")
            self.assertEqual(pagina.status_code, 200)
            self.assertIn(b'name="nombre_rol"', pagina.data)
            self.assertIn(b'value="ENCARGADO_PRESTAMOS"', pagina.data)
        finally:
            servicio.actualizar_rol_cuenta("02167885", "USUARIO", 1)
        roles, permisos = servicio.consultar_roles(), servicio.consultar_permisos()
        with self.assertRaises(LookupError):
            servicio._construir_matriz({"permisos_USUARIO": ["PERMISO_INEXISTENTE"]}, roles, permisos)
        with self.assertRaises(ValueError):
            repo.actualizar_matriz_permisos({"USUARIO": [], "ENCARGADO_PRESTAMOS": [], "ADMINISTRADOR": []},
                                           version=version_matriz(roles, permisos))

    def test_cuenta_bloqueada_no_accede(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE usuario_sistema SET estado_cuenta='BLOQUEADA' WHERE nombre_usuario='usuario1'")
        try:
            self.assertIsNone(self.app.extensions["acceso"].autenticar("usuario1", "UsuarioPrueba2026!"))
        finally:
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE usuario_sistema SET estado_cuenta='ACTIVA' WHERE nombre_usuario='usuario1'")

    def test_correo_unico_en_registro_edicion_y_base(self):
        repo = RepositorioPersonaSQL(self.db)
        datos = dict(tipo="ESTUDIANTE", dni="71111111", cui="72222222",
                     nombres="Correo", apellidos="Prueba", correo="correo-unico@example.com",
                     estado_matricula="VIGENTE")
        persona = repo.registrar_persona(FabricaPersona.construir(datos))
        admin = repo.consultar_persona("98000001")
        with self.assertRaises(ValidacionPersonaError) as error:
            repo.registrar_persona(FabricaPersona.construir(dict(
                datos, dni="71111112", cui="72222223", correo=admin.correo)))
        self.assertIn("correo", error.exception.errores)
        # Conservar el mismo correo al editar la propia ficha es valido.
        repo.actualizar_persona(persona, persona.dni, 1, version=version_persona(persona))
        version = version_persona(persona)
        persona.correo = admin.correo
        with self.assertRaises(ValidacionPersonaError):
            repo.actualizar_persona(persona, persona.dni, 1, version=version)
        self.assertEqual(repo.consultar_persona(persona.dni).correo, datos["correo"])
        with self.assertRaises(mysql.connector.IntegrityError):
            with self.db.sesion(escritura=True) as c:
                c.execute("INSERT INTO persona (dni,nombres,apellidos,correo) VALUES (%s,%s,%s,%s)",
                          ("71111113", "Otra", "Persona", admin.correo))

    def test_estudiante_valores_predeterminados_y_ciclo(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("INSERT INTO persona (dni,nombres,apellidos,correo) VALUES (%s,%s,%s,%s)",
                      ("73333333", "Matricula", "Prueba", "matricula-default@example.com"))
            c.execute("INSERT INTO estudiante (dni,cui) VALUES (%s,%s)", ("73333333", "74444444"))
        persona = RepositorioPersonaSQL(self.db).consultar_persona("73333333")
        self.assertEqual(persona.estado_matricula, "VIGENTE")
        self.assertIsNone(persona.ciclo)
        self.assertTrue(persona.matricula_vigente())
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE estudiante SET ciclo=0 WHERE dni=%s", (persona.dni,))
        with self.assertRaises(mysql.connector.Error):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE estudiante SET estado_matricula='INVALIDA' WHERE dni=%s", (persona.dni,))

    def test_intentos_fallidos_no_bloquean_y_cuenta_inactiva_cierra_sesion(self):
        acceso = self.app.extensions["acceso"]
        for _ in range(10):
            self.assertIsNone(acceso.autenticar("usuario1", "incorrecta"))
        client = self.login("usuario1", "UsuarioPrueba2026!")
        self.app.extensions['cuentas'].cambiar_estado_cuenta("02167885", False, 1)
        try:
            self.assertEqual(client.get("/").status_code, 302)
        finally:
            self.app.extensions['cuentas'].cambiar_estado_cuenta("02167885", True, 1)
        self.login("usuario1", "UsuarioPrueba2026!")

    def test_cambiar_contrasena_descarta_la_sesion_anterior(self):
        cuentas = self.app.extensions["cuentas"]
        client = self.login("usuario1", "UsuarioPrueba2026!")
        try:
            cuentas.actualizar_cuenta("02167885", {
                "nombre_usuario": "usuario1", "clave": "ClaveNuevaPrueba2026!",
            }, 1)
            self.assertEqual(client.get("/").status_code, 302)
            self.login("usuario1", "ClaveNuevaPrueba2026!")
        finally:
            cuentas.actualizar_cuenta("02167885", {
                "nombre_usuario": "usuario1", "clave": "UsuarioPrueba2026!",
            }, 1)

    def test_directorio_y_campos_opcionales(self):
        repo = RepositorioPersonaSQL(self.db)
        for i in range(30):
            repo.registrar_persona(FabricaPersona.construir(dict(
                tipo="ESTUDIANTE", dni=str(70000000+i), cui=str(71000000+i),
                nombres="Prueba", apellidos="Directorio", correo=f"prueba{i}@example.com",
                estado_matricula="VIGENTE",
            )))
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET telefono=NULL WHERE dni='98000001'")
        client = self.login()
        self.assertEqual(repo.consultar_persona("98000001").telefono, "")
        self.assertIn(b"Siguiente", client.get("/personas").data)
        self.assertIn(b"Anterior", client.get("/personas?pagina=2").data)
        self.assertIn(b"dos caracteres", client.get("/personas?q=a").data)
        self.assertEqual(client.get("/roles").status_code, 200)
        primera, segunda = [repo.consultar_personas({"pagina": n})["personas"] for n in (1, 2)]
        self.assertEqual(len(primera), 25)
        self.assertTrue(segunda)
        self.assertTrue({p.dni for p in primera}.isdisjoint(p.dni for p in segunda))

    def test_edicion_antigua_no_reactiva_persona(self):
        client = self.login()
        dni = "99000012"
        path = f"/personas/{dni}/editar"
        version = re.search(rb'name="version" value="([^"]+)"', client.get(path).data)[1].decode()
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (dni,))
        repo = RepositorioPersonaSQL(self.db)
        datos = dict(vars(repo.consultar_persona(dni)), tipo="ESTUDIANTE", version=version,
                     estado="ACTIVA", telefono="123", ciclo="5")
        self.assertEqual(self.post(client, path, datos).status_code, 409)
        actual = repo.consultar_persona(dni)
        self.assertFalse(actual.esta_activa())
        datos["version"] = version_persona(actual)
        self.assertEqual(self.post(client, path, datos).status_code, 302)

    def test_matriz_antigua_no_restaura_permiso(self):
        client = self.login()
        html = client.get("/roles").data
        version = re.search(rb'name="version" value="([^"]+)"', html)[1].decode()
        with self.db.sesion() as c:
            c.execute("SELECT rol,permiso FROM rol_permiso")
            datos = {}
            for fila in c.fetchall():
                datos.setdefault("permisos_" + fila["rol"], []).append(fila["permiso"])
        original = dict(datos, version=version)
        cambio = dict(original, permisos_USUARIO=[p for p in datos["permisos_USUARIO"] if p != "CATALOGO_CONSULTAR"])
        self.assertEqual(self.post(client, "/roles/permisos", cambio).status_code, 302)
        self.assertEqual(self.post(client, "/roles/permisos", original).status_code, 409)
        with self.db.sesion() as c:
            c.execute("SELECT 1 FROM rol_permiso WHERE rol='USUARIO' AND permiso='CATALOGO_CONSULTAR'")
            self.assertIsNone(c.fetchone())

    def test_alta_revalida_persona_y_exige_rol_usuario(self):
        cuentas = self.app.extensions["cuentas"]
        repo = cuentas.repositorio
        real = repo.registrar_cuenta
        def desactivar_y_guardar(usuario):
            with self.db.sesion(escritura=True) as c:
                c.execute("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (usuario.persona.dni,))
            return real(usuario)
        with patch.object(repo, "registrar_cuenta", desactivar_y_guardar):
            with self.assertRaisesRegex(ValueError, "persona debe estar activa"):
                cuentas.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        self.assertIsNone(repo.consultar_cuenta_persona("99000011"))
        with self.db.sesion(escritura=True) as c:
            c.execute("UPDATE persona SET estado='ACTIVA' WHERE dni='99000011'")
        def cambiar_rol_y_guardar(usuario):
            from dominio.cuentas import NombreRol
            usuario.rol.nombre = NombreRol.ADMINISTRADOR
            return real(usuario)
        with patch.object(repo, "registrar_cuenta", cambiar_rol_y_guardar):
            with self.assertRaisesRegex(ValueError, "rol Usuario"):
                cuentas.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        cuenta = cuentas.registrar_cuenta("99000011", "alta-prueba", "ClaveTemporal123")
        self.assertIsNotNone(cuenta.id_usuario)
