from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_control.politica_prestamo import DIAS_LABORABLES, NOMBRES_DIAS, dias_habilitados
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario_tras_error

RUTA_POLITICAS = 'politicas.consultar_politicas_prestamo'


class ControladorPoliticaPrestamo:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('politicas', __name__, url_prefix='/politicas')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_politicas_prestamo', self.consultar_politicas_prestamo, ['GET']),
            (
                '/nueva',
                'registrar_politica_prestamo',
                self.registrar_politica_prestamo,
                ['GET', 'POST'],
            ),
            (
                '/<int:identificador>/editar',
                'editar_politica_prestamo',
                self.editar_politica_prestamo,
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
                'guardar_horario_y_plazos_de_reserva',
                self.guardar_horario_y_plazos_de_reserva,
                ['POST'],
            ),
            ('/limite', 'guardar_limite_articulos', self.guardar_limite_articulos, ['POST']),
            ('/limites', 'guardar_limites_articulos', self.guardar_limites_articulos, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('POLITICAS_GESTIONAR')
    def consultar_politicas_prestamo(self):
        politicas = self.servicio.consultar_politicas_prestamo()
        matriz = {(p['id_categoria'], p['tipo_persona']): p for p in politicas}
        configuracion = self.servicio.consultar_horario_y_plazos_de_reserva()
        dias = (
            request.form.getlist('dias_atencion')
            if request.endpoint == 'politicas.guardar_horario_y_plazos_de_reserva'
            else tuple(map(str, dias_habilitados(configuracion.get('dias_atencion', DIAS_LABORABLES))))
        )
        return render_template(
            'control/vista_politica_prestamo.html',
            modo='lista',
            politicas=politicas,
            matriz=matriz,
            categorias=self.recursos.consultar_categorias(),
            configuracion=configuracion,
            dias_elegidos=dias,
            dias_semana=tuple(enumerate(NOMBRES_DIAS)),
            limites=self.servicio.consultar_limites_articulos(),
            tipos=TIPOS_PERSONA,
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self._mostrar_formulario_politica())
    def registrar_politica_prestamo(self):
        if request.method == 'POST':
            self.servicio.registrar_politica_prestamo(
                request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Política registrada.')
            return redirect(url_for(RUTA_POLITICAS))
        return self._mostrar_formulario_politica()

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self._mostrar_formulario_politica(identificador))
    def editar_politica_prestamo(self, identificador):
        if request.method == 'POST':
            self.servicio.actualizar_politica_prestamo(
                identificador, request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Política actualizada.')
            return redirect(url_for(RUTA_POLITICAS))
        return self._mostrar_formulario_politica(identificador)

    def _mostrar_formulario_politica(self, identificador=None):
        politica, version = (
            self.servicio.consultar_politica_prestamo(identificador)
            if identificador is not None
            else ({}, '')
        )
        return render_template(
            'control/vista_politica_prestamo.html',
            modo='formulario',
            politica=politica,
            categoria_seleccionada=request.args.get('id_categoria', ''),
            version=version,
            tipos=TIPOS_PERSONA,
            categorias=self.recursos.consultar_categorias(),
        )

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self.consultar_politicas_prestamo())
    def guardar_horario_y_plazos_de_reserva(self):
        datos = dict(request.form, dias_atencion=request.form.getlist('dias_atencion'))
        self.servicio.guardar_horario_y_plazos_de_reserva(datos, g.usuario.id_usuario)
        flash('Horario y plazos de reserva guardados.')
        return redirect(url_for(RUTA_POLITICAS))

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self.consultar_politicas_prestamo())
    def guardar_limite_articulos(self):
        self.servicio.guardar_limite_articulos(
            request.form.get('tipo_persona'),
            request.form.get('maximo_articulos'),
            g.usuario.id_usuario,
        )
        flash('Límite actualizado.')
        return redirect(url_for(RUTA_POLITICAS))

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self.consultar_politicas_prestamo())
    def guardar_limites_articulos(self):
        self.servicio.guardar_limites_articulos(
            {tipo: request.form.get('maximo_' + tipo) for tipo in TIPOS_PERSONA},
            g.usuario.id_usuario,
        )
        flash('Límites actualizados.')
        return redirect(url_for(RUTA_POLITICAS))

    @requiere_permiso('POLITICAS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self._mostrar_formulario_politica(identificador))
    def eliminar_politica_prestamo(self, identificador):
        self.servicio.eliminar_politica_prestamo(identificador, g.usuario.id_usuario)
        flash('Política eliminada.')
        return redirect(url_for(RUTA_POLITICAS))
