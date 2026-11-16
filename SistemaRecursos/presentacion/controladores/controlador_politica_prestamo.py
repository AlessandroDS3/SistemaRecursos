from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
from presentacion.seguridad import requiere_permiso

RUTA_POLITICAS = 'politicas.consultar_politicas_prestamo'


class ControladorPoliticaPrestamo:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('politicas', __name__, url_prefix='/politicas')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_politicas_prestamo', self.consultar_politicas_prestamo, ['GET']),
            (
                '/nueva',
                'gestionar_formulario_politica_prestamo',
                self.gestionar_formulario_politica_prestamo,
                ['GET', 'POST'],
            ),
            (
                '/<int:identificador>/editar',
                'gestionar_formulario_politica_prestamo',
                self.gestionar_formulario_politica_prestamo,
                ['GET', 'POST'],
            ),
            (
                '/<int:identificador>/eliminar',
                'eliminar_politica_prestamo',
                self.eliminar_politica_prestamo,
                ['POST'],
            ),
            (
                '/configuracion',
                'guardar_configuracion_general',
                self.guardar_configuracion_general,
                ['POST'],
            ),
            ('/limite', 'guardar_limite_articulos', self.guardar_limite_articulos, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('POLITICAS_GESTIONAR')
    def consultar_politicas_prestamo(self):
        politicas = self.servicio.consultar_politicas_prestamo()
        matriz = {(p['id_categoria'], p['tipo_persona']): p for p in politicas}
        return render_template(
            'vista_politica_prestamo.html',
            modo='lista',
            politicas=politicas,
            matriz=matriz,
            categorias=self.recursos.consultar_categorias(),
            configuracion=self.servicio.consultar_configuracion_general(),
            limites=self.servicio.consultar_limites_articulos(),
            tipos=TIPOS_PERSONA,
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    def gestionar_formulario_politica_prestamo(self, identificador=None):
        if request.method == 'POST':
            self.servicio.guardar_politica_prestamo(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Política guardada. Los préstamos anteriores conservan sus condiciones.')
            return redirect(url_for(RUTA_POLITICAS))
        politica, version = (
            self.servicio.consultar_politica_prestamo(identificador)
            if identificador is not None
            else ({}, '')
        )
        return render_template(
            'vista_politica_prestamo.html',
            modo='formulario',
            politica=politica,
            version=version,
            tipos=TIPOS_PERSONA,
            categorias=self.recursos.consultar_categorias(),
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    def guardar_configuracion_general(self):
        self.servicio.guardar_configuracion_general(request.form.to_dict(), g.usuario.id_usuario)
        flash('Horario y plazos de reserva guardados.')
        return redirect(url_for(RUTA_POLITICAS))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def guardar_limite_articulos(self):
        self.servicio.guardar_limite_articulos(
            request.form.get('tipo_persona'),
            request.form.get('maximo_articulos'),
            g.usuario.id_usuario,
        )
        flash('Límite guardado.')
        return redirect(url_for(RUTA_POLITICAS))

    @requiere_permiso('POLITICAS_GESTIONAR')
    def eliminar_politica_prestamo(self, identificador):
        self.servicio.eliminar_politica_prestamo(identificador, g.usuario.id_usuario)
        flash('Política sin préstamos asociados eliminada.')
        return redirect(url_for(RUTA_POLITICAS))
