from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.persona import (
    CAMPOS_TIPO,
    ESTADOS_MATRICULA,
    ESTADOS_PERSONA,
    LONGITUD_CODIGO_INSTITUCIONAL,
    TIPOS_PERSONA,
)
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario_tras_error

VISTA_PERSONA = 'personas_usuarios/vista_persona.html'


class ControladorPersona:
    def __init__(self, servicio, cuentas):
        self.servicio, self.cuentas = servicio, cuentas
        self.blueprint = Blueprint('personas', __name__, url_prefix='/personas')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_personas', self.consultar_personas, ['GET']),
            ('/buscar', 'buscar_personas', self.buscar_personas, ['GET']),
            (
                '/nueva',
                'registrar_persona',
                self.registrar_persona,
                ['GET', 'POST'],
            ),
            ('/<documento>', 'consultar_persona', self.consultar_persona, ['GET']),
            (
                '/<documento>/editar',
                'editar_persona',
                self.editar_persona,
                ['GET', 'POST'],
            ),
            ('/<documento>/desactivar', 'desactivar_persona', self.desactivar_persona, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('PERSONAS_CONSULTAR')
    def consultar_personas(self):
        resultado = self.servicio.consultar_personas(request.args)
        return render_template(
            VISTA_PERSONA,
            modo='lista',
            resultado=resultado,
            tipos=TIPOS_PERSONA,
            estados=ESTADOS_PERSONA,
        )

    @requiere_permiso('PERSONAS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def buscar_personas(self):
        return jsonify(self.servicio.buscar_personas(request.args.get('q', '')))

    @requiere_permiso('PERSONAS_CONSULTAR')
    def consultar_persona(self, documento):
        persona, _ = self.servicio.consultar_persona(documento)
        return render_template(
            VISTA_PERSONA,
            modo='detalle',
            persona=persona,
            cambios_tipo=(self.servicio.consultar_cambios_tipo_persona(documento)
                           if g.usuario.rol == 'ADMINISTRADOR' else []),
            tiene_cuenta=g.usuario.tiene_permiso('USUARIOS_GESTIONAR')
            and self.cuentas.tiene_cuenta(documento),
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self._mostrar_formulario_persona())
    def registrar_persona(self):
        if request.method == 'POST':
            dni_guardado = self.servicio.registrar_persona(
                request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Persona guardada.')
            return redirect(url_for('personas.consultar_persona', documento=dni_guardado))
        return self._mostrar_formulario_persona()

    @requiere_permiso('PERSONAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, documento: self._mostrar_formulario_persona(documento))
    def editar_persona(self, documento):
        if request.method == 'POST':
            dni_guardado = self.servicio.actualizar_persona(
                documento, request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Persona guardada.')
            return redirect(url_for('personas.consultar_persona', documento=dni_guardado))
        return self._mostrar_formulario_persona(documento)

    def _mostrar_formulario_persona(self, documento=None):
        persona, version_actual = (
            self.servicio.consultar_persona(documento) if documento else ({}, '')
        )
        return render_template(
            VISTA_PERSONA,
            modo='formulario',
            persona=persona,
            version=version_actual,
            tipos=TIPOS_PERSONA,
            campos_tipo=CAMPOS_TIPO,
            estados=ESTADOS_PERSONA,
            estados_matricula=ESTADOS_MATRICULA,
            longitud_codigo=LONGITUD_CODIGO_INSTITUCIONAL,
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    def desactivar_persona(self, documento):
        self.servicio.desactivar_persona(documento, g.usuario.id_usuario)
        flash('Persona desactivada.')
        return redirect(url_for('personas.consultar_persona', documento=documento))
