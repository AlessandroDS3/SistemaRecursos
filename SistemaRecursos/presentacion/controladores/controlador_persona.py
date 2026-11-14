from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.persona import CAMPOS_TIPO, TIPOS_PERSONA
from presentacion.seguridad import requiere_permiso


class ControladorPersona:
    def __init__(self, servicio):
        self.servicio = servicio
        self.blueprint = Blueprint('personas', __name__, url_prefix='/personas')
        for ruta, nombre, funcion, metodos in (
            ('', 'listar', self.listar, ['GET']),
            ('/buscar', 'buscar', self.buscar, ['GET']),
            ('/nueva', 'nueva', self.formulario, ['GET', 'POST']),
            ('/<documento>', 'detalle', self.detalle, ['GET']),
            ('/<documento>/editar', 'editar', self.formulario, ['GET', 'POST']),
            ('/<documento>/desactivar', 'desactivar', self.desactivar, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('PERSONAS_CONSULTAR')
    def listar(self):
        resultado = self.servicio.listar(request.args)
        return render_template('vista_persona.html', modo='lista', resultado=resultado)

    @requiere_permiso('PERSONAS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def buscar(self):
        return jsonify(self.servicio.buscar(request.args.get('q', '')))

    @requiere_permiso('PERSONAS_CONSULTAR')
    def detalle(self, documento):
        persona, _ = self.servicio.consultar(documento)
        return render_template('vista_persona.html', modo='detalle', persona=persona)

    @requiere_permiso('PERSONAS_GESTIONAR')
    def formulario(self, documento=None):
        persona, version = self.servicio.consultar(documento) if documento else ({}, '')
        if request.method == 'POST':
            nuevo = self.servicio.guardar(request.form.to_dict(), g.usuario.id_usuario, documento)
            flash('Ficha de persona guardada.')
            return redirect(url_for('personas.detalle', documento=nuevo))
        return render_template(
            'vista_persona.html',
            modo='formulario',
            persona=persona,
            version=version,
            tipos=TIPOS_PERSONA,
            campos_tipo=CAMPOS_TIPO,
        )

    @requiere_permiso('PERSONAS_GESTIONAR')
    def desactivar(self, documento):
        self.servicio.desactivar(documento, g.usuario.id_usuario)
        flash('Persona desactivada.')
        return redirect(url_for('personas.detalle', documento=documento))
