from __future__ import annotations
from servicios.servicio_persona import ServicioAplicacionPersona
from servicios.servicio_acceso import ServicioAplicacionAcceso
from mysql.connector import IntegrityError
from flask import Blueprint, request, redirect, url_for, g, session
from presentacion.formularios import error_formulario
from presentacion.seguridad import requiere_permiso, redirigir_segun_permiso
from presentacion.vistas.vista_persona import VistaPersona
from dominio.gestion_personas_usuarios.validacion_persona import ValidacionPersonaError

MSG_PERSONA_DUPLICADA = "Ya existe una persona con esos datos únicos."


class ControladorPersona:
    def __init__(self, servicio: ServicioAplicacionPersona, acceso: ServicioAplicacionAcceso):
        self.servicio: ServicioAplicacionPersona = servicio
        self.acceso: ServicioAplicacionAcceso = acceso
        self.vista = VistaPersona()
        self.blueprint = Blueprint("personas", __name__, url_prefix="/personas")
        agregar = self.blueprint.add_url_rule
        agregar("", "consultar_personas", self.consultar_personas, methods=["GET"])
        agregar('/nueva', "mostrar_formulario_persona", self.mostrar_formulario_persona, methods=["GET"])
        agregar('/nueva', 'registrar_persona', self.registrar_persona, methods=["POST"])
        agregar("/<string:dni>", "consultar_persona", self.consultar_persona, methods=["GET"])
        agregar('/<string:dni>/editar', "mostrar_edicion_persona", self.mostrar_edicion_persona, methods=["GET"])
        agregar('/<string:dni>/editar', 'actualizar_persona', self.actualizar_persona, methods=["POST"])
        agregar('/<string:dni>/desactivar', "mostrar_confirmacion_desactivacion_persona", self.mostrar_confirmacion_desactivacion_persona, methods=["GET"])
        agregar('/<string:dni>/desactivar', 'desactivar_persona', self.desactivar_persona, methods=["POST"])
        agregar("/<string:dni>/cuenta", "registrar_cuenta", self.registrar_cuenta, methods=["POST"])
        agregar('/<string:dni>/cuenta/editar', "mostrar_edicion_cuenta", self.mostrar_edicion_cuenta, methods=["GET"])
        agregar('/<string:dni>/cuenta/editar', 'actualizar_cuenta', self.actualizar_cuenta, methods=["POST"])
        agregar("/<string:dni>/cuenta/activar", "activar_cuenta", self.activar_cuenta, methods=["POST"])
        agregar("/<string:dni>/cuenta/desactivar", "desactivar_cuenta", self.desactivar_cuenta, methods=["POST"])

    @staticmethod
    def _ir_al_detalle(dni):
        return redirigir_segun_permiso(
            "personas.consultar_persona", "PERSONAS_CONSULTAR", dni=dni
        )

    @staticmethod
    def _errores_persona(error):
        if isinstance(error, ValidacionPersonaError):
            return error.errores
        if isinstance(error, IntegrityError) and error.errno == 1062:
            mensaje = str(error).lower()
            if "uq_estudiante_cui" in mensaje:
                return {"cui": "Este CUI ya está registrado."}
            if "uq_persona_dni" in mensaje:
                return {"dni": "Este DNI ya está registrado."}
        return {}

    @requiere_permiso("PERSONAS_CONSULTAR")
    def consultar_personas(self):
        con_cuentas = g.usuario.rol.tiene_permiso("USUARIOS_GESTIONAR")
        filtros = {
            "q": request.args.get("q", ""),
            "tipo": request.args.get("tipo", ""),
            "estado": request.args.get("estado", ""),
            "cuenta": request.args.get("cuenta", "") if con_cuentas else "",
        }
        resultado = self.servicio.consultar_personas(
            dict(filtros, pagina=request.args.get("pagina", "1")), incluir_cuenta=con_cuentas
        )
        personas = resultado["personas"]
        cuentas = {}
        if con_cuentas and personas:
            cuentas = self.acceso.consultar_resumen_cuentas(
                {p.dni for p in personas}
            )
        return self.vista.mostrar_consulta(
            personas,
            cuentas,
            filtros=filtros,
            resumen=resultado["resumen"], pagina=resultado["pagina"],
            paginas=resultado["paginas"], aviso=resultado["aviso"],
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    def mostrar_formulario_persona(self):
        return self.vista.mostrar_formulario()

    @requiere_permiso('PERSONAS_GESTIONAR')
    def registrar_persona(self):
        try:
            persona = self.servicio.registrar_persona(request.form)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, MSG_PERSONA_DUPLICADA)
            formulario = self.vista.mostrar_formulario(
                error=mensaje, errores=self._errores_persona(error)
            )
            return formulario
        self.vista.mostrar_mensaje("Persona registrada.")
        return self._ir_al_detalle(persona.dni)

    @requiere_permiso("PERSONAS_CONSULTAR")
    def consultar_persona(self, dni):
        return self._mostrar_detalle(dni)

    def _mostrar_detalle(self, dni, error=None):
        gestionar = g.usuario.rol.tiene_permiso("USUARIOS_GESTIONAR")
        return self.vista.mostrar_detalle(
            self.servicio.consultar_persona(dni),
            self.acceso.consultar_cuenta_persona(dni) if gestionar else None,
            error=error,
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    def mostrar_edicion_persona(self, dni):
        persona = self.servicio.consultar_persona(dni)
        return self.vista.mostrar_formulario(persona)

    @requiere_permiso('PERSONAS_GESTIONAR')
    def actualizar_persona(self, dni):
        persona = self.servicio.consultar_persona(dni)
        datos = dict(request.form)
        try:
            persona = self.servicio.actualizar_persona(datos, dni_actual=dni, id_usuario_actor=g.usuario.id_usuario)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, MSG_PERSONA_DUPLICADA)
            formulario = self.vista.mostrar_formulario(
                persona, error=mensaje, errores=self._errores_persona(error)
            )
            return formulario
        self.vista.mostrar_mensaje("Datos actualizados.")
        return self._ir_al_detalle(persona.dni)

    @requiere_permiso('PERSONAS_GESTIONAR')
    def mostrar_confirmacion_desactivacion_persona(self, dni):
        persona = self.servicio.consultar_persona(dni)
        return self.vista.mostrar_confirmacion_desactivacion(persona)

    @requiere_permiso('PERSONAS_GESTIONAR')
    def desactivar_persona(self, dni):
        self.servicio.desactivar_persona(dni, id_usuario_actor=g.usuario.id_usuario)
        self.vista.mostrar_mensaje("Persona desactivada. Sus cuentas ya no podrán ingresar.")
        return redirigir_segun_permiso("personas.consultar_personas", "PERSONAS_CONSULTAR")

    @requiere_permiso("USUARIOS_GESTIONAR")
    def registrar_cuenta(self, dni):
        try:
            self.acceso.registrar_cuenta(
                dni,
                request.form.get("nombre_usuario", ""),
                request.form.get("clave", ""),
            )
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(
                error, "La persona ya tiene cuenta o el usuario está en uso."
            )
            if g.usuario.rol.tiene_permiso("PERSONAS_CONSULTAR"):
                return self._mostrar_detalle(dni, error=mensaje), 400
            return self.vista.mostrar_alta_cuenta(dni, error=mensaje), 400
        self.vista.mostrar_mensaje("Cuenta de acceso creada.")
        return self._ir_al_detalle(dni)

    @requiere_permiso('USUARIOS_GESTIONAR')
    def mostrar_edicion_cuenta(self, dni):
        cuenta = self.acceso.consultar_cuenta(dni)
        return self.vista.mostrar_formulario_cuenta(
            cuenta.persona, cuenta
        )

    @requiere_permiso('USUARIOS_GESTIONAR')
    def actualizar_cuenta(self, dni):
        cuenta = self.acceso.consultar_cuenta(dni)
        propia = cuenta.id_usuario == g.usuario.id_usuario
        try:
            self.acceso.actualizar_cuenta(dni, request.form, g.usuario.id_usuario)
        except (ValueError, IntegrityError) as error:
            mensaje = error_formulario(error, "Ese nombre de usuario ya está en uso.")
            formulario = self.vista.mostrar_formulario_cuenta(
                cuenta.persona, cuenta, error=mensaje
            )
            return formulario
        if propia and request.form.get("clave", ""):
            session.clear()
            self.vista.mostrar_mensaje("Contraseña actualizada. Inicia sesión con tus nuevos datos.")
            return redirect(url_for("auth.login"))
        self.vista.mostrar_mensaje(
            "Cuenta actualizada."
        )
        if propia:
            return redirect(url_for("inicio"))
        return self._ir_al_detalle(dni)

    @requiere_permiso("USUARIOS_GESTIONAR")
    def activar_cuenta(self, dni):
        self.acceso.cambiar_estado_cuenta(dni, True, g.usuario.id_usuario)
        self.vista.mostrar_mensaje(
            "Cuenta activada. Ya puede iniciar sesión si su persona y rol están activos."
        )
        return self._ir_al_detalle(dni)

    @requiere_permiso("USUARIOS_GESTIONAR")
    def desactivar_cuenta(self, dni):
        self.acceso.cambiar_estado_cuenta(dni, False, g.usuario.id_usuario)
        self.vista.mostrar_mensaje(
            "Cuenta desactivada. No podrá iniciar sesión y perderá acceso en su siguiente petición."
        )
        return self._ir_al_detalle(dni)
