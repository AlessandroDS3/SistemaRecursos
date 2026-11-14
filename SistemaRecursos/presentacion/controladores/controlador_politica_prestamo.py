from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
from presentacion.seguridad import requiere_permiso


class ControladorPoliticaPrestamo:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('politicas', __name__, url_prefix='/politicas')
        for ruta, nombre, funcion, metodos in (
            ('', 'listar', self.listar, ['GET']),
            ('/nueva', 'nueva', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>/editar', 'editar', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>/eliminar', 'eliminar', self.eliminar, ['POST']),
            ('/configuracion', 'configuracion', self.configuracion, ['POST']),
            ('/limite', 'limite', self.limite, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('POLITICAS_GESTIONAR')
    def listar(self):
        return render_template(
            'vista_politica_prestamo.html',
            modo='lista',
            politicas=self.servicio.listar(),
            configuracion=self.servicio.configuracion(),
            limites=self.servicio.limites(),
            tipos=TIPOS_PERSONA,
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    def formulario(self, identificador=None):
        politica, version = self.servicio.consultar(identificador) if identificador else ({}, '')
        if request.method == 'POST':
            self.servicio.guardar(request.form.to_dict(), g.usuario.id_usuario, identificador)
            flash('Política guardada. Los préstamos anteriores conservan sus condiciones.')
            return redirect(url_for('politicas.listar'))
        return render_template(
            'vista_politica_prestamo.html',
            modo='formulario',
            politica=politica,
            version=version,
            tipos=TIPOS_PERSONA,
            categorias=self.recursos.categorias(),
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    def configuracion(self):
        self.servicio.guardar_configuracion(request.form.to_dict(), g.usuario.id_usuario)
        flash('Horario y plazos de reserva guardados.')
        return redirect(url_for('politicas.listar'))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def limite(self):
        self.servicio.guardar_limite(
            request.form.get('tipo_persona'),
            request.form.get('maximo_articulos'),
            g.usuario.id_usuario,
        )
        flash('Límite guardado.')
        return redirect(url_for('politicas.listar'))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def eliminar(self, identificador):
        self.servicio.eliminar(identificador, g.usuario.id_usuario)
        flash('Política sin préstamos asociados eliminada.')
        return redirect(url_for('politicas.listar'))
