from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.persona import CAMPOS_TIPO, TIPOS_PERSONA
from presentacion.seguridad import requiere_permiso


class ControladorPersona:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('personas', __name__, url_prefix='/personas')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_personas', self.consultar_personas, ['GET']),
            ('/buscar', 'buscar_personas', self.buscar_personas, ['GET']),
            (
                '/nueva',
                'gestionar_formulario_persona',
                self.gestionar_formulario_persona,
                ['GET', 'POST'],
            ),
            ('/<documento>', 'consultar_persona', self.consultar_persona, ['GET']),
            (
                '/<documento>/editar',
                'gestionar_formulario_persona',
                self.gestionar_formulario_persona,
                ['GET', 'POST'],
            ),
            ('/<documento>/desactivar', 'desactivar_persona', self.desactivar_persona, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('PERSONAS_CONSULTAR')
    def consultar_personas(self):
        resultado = self.servicio.consultar_personas(request.args)
        return render_template('vista_persona.html', modo='lista', resultado=resultado)

    @requiere_permiso('PERSONAS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def buscar_personas(self):
        return jsonify(self.servicio.buscar_personas(request.args.get('q', '')))

    @requiere_permiso('PERSONAS_CONSULTAR')
    def consultar_persona(self, documento):
        persona, _ = self.servicio.consultar_persona(documento)
        return render_template('vista_persona.html', modo='detalle', persona=persona)

    @requiere_permiso('PERSONAS_GESTIONAR')
    def gestionar_formulario_persona(self, documento=None):
        persona, version = self.servicio.consultar_persona(documento) if documento else ({}, '')
        if request.method == 'POST':
            nuevo = self.servicio.guardar_persona(
                request.form.to_dict(), g.usuario.id_usuario, documento
            )
            flash('Ficha de persona guardada.')
            return redirect(url_for('personas.consultar_persona', documento=nuevo))
        return render_template(
            'vista_persona.html',
            modo='formulario',
            persona=persona,
            version=version,
            tipos=TIPOS_PERSONA,
            campos_tipo=CAMPOS_TIPO,
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    def desactivar_persona(self, documento):
        self.servicio.desactivar_persona(documento, g.usuario.id_usuario)
        flash('Persona desactivada.')
        return redirect(url_for('personas.consultar_persona', documento=documento))
