from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario_tras_error
from presentacion.navegacion import obtener_url_del_detalle_de_prestamo, obtener_url_de_regreso_a_prestamos
from dominio.gestion_prestamos.prestamo import FILTROS_ESTADO_PRESTAMO


def _preparar_bien_para_formulario_prestamo(bien):
    return dict(
        id_bien=bien['id_bien'],
        id_recurso=bien['id_recurso'],
        id_categoria=bien['id_categoria'],
        codigo_inventario=bien['codigo_inventario'],
        recurso_nombre=bien['recurso'],
        ubicacion=bien['ubicacion'],
        estado=bien['estado'],
    )


class ControladorPrestamo:
    def __init__(self, servicio, bienes, recursos, politicas, ampliaciones=None):
        self.servicio, self.bienes, self.recursos, self.politicas = (
            servicio,
            bienes,
            recursos,
            politicas,
        )
        self.ampliaciones = ampliaciones
        self.blueprint = Blueprint('prestamos', __name__, url_prefix='/prestamos')
        self.blueprint.add_url_rule(
            '/condiciones', 'consultar_condiciones_prestamo', self.consultar_condiciones_prestamo
        )
        self.blueprint.add_url_rule(
            '/bienes', 'consultar_bienes_disponibles', self.consultar_bienes_disponibles
        )
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_prestamos', self.consultar_prestamos, ['GET']),
            ('/nuevo', 'registrar_prestamo', self.registrar_prestamo, ['GET', 'POST']),
            ('/autorizaciones', 'autorizar_operacion_propia', self.autorizar_operacion_propia, ['POST']),
            ('/<int:identificador>/detalles/<int:detalle_id>/discrepancia',
             'registrar_discrepancia_devolucion', self.registrar_discrepancia_devolucion, ['POST']),
            ('/<int:identificador>/detalles/<int:detalle_id>/rectificar',
             'rectificar_devolucion', self.rectificar_devolucion, ['POST']),
            ('/<int:identificador>', 'consultar_prestamo', self.consultar_prestamo, ['GET']),
            (
                '/<int:identificador>/devolver',
                'registrar_devolucion',
                self.registrar_devolucion,
                ['POST'],
            ),
            (
                '/<int:identificador>/detalles/<int:detalle_id>/perdida',
                'registrar_perdida_bien_material',
                self.registrar_perdida_bien_material,
                ['POST'],
            ),
            (
                '/vencimientos',
                'actualizar_estados_prestamos_vencidos',
                self.actualizar_estados_prestamos_vencidos,
                ['POST'],
            ),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def consultar_prestamos(self):
        gestionar = g.usuario.tiene_permiso('PRESTAMOS_GESTIONAR')
        filas = self.servicio.consultar_prestamos(
            request.args, None if gestionar else g.usuario.dni
        )
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='lista',
            prestamos=filas,
            gestionar=gestionar,
            estados=FILTROS_ESTADO_PRESTAMO,
            volver=url_for(
                'prestamos.consultar_prestamos',
                **{k: request.args[k] for k in ('q', 'estado', 'pagina') if k in request.args},
            ),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_condiciones_prestamo(self):
        return jsonify(
            self.servicio.consultar_condiciones_prestamo(request.args.get('dni_persona', ''))
        )

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self.consultar_prestamos())
    def autorizar_operacion_propia(self):
        identificador = self.servicio.autorizar_operacion_propia(request.form, g.usuario.id_usuario)
        flash(f'Autorización #{identificador}. Es válida para un uso durante 24 horas.')
        return redirect(url_for('prestamos.consultar_prestamos'))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_bienes_disponibles(self):
        filtros = dict(request.args, estado='DISPONIBLE')
        return jsonify(
            resultados=[
                _preparar_bien_para_formulario_prestamo(b) for b in self.bienes.consultar_bienes_materiales(filtros)
            ]
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self: self._mostrar_formulario_prestamo())
    def registrar_prestamo(self):
        if request.method == 'POST':
            datos = request.form.to_dict()
            datos.update(
                bienes=request.form.getlist('bienes'),
                participantes=[
                    d.strip()
                    for entrada in request.form.getlist('participantes')
                    for d in entrada.split(',')
                    if d.strip()
                ],
            )
            identificador = self.servicio.registrar_prestamo(datos, g.usuario.id_usuario)
            flash('Préstamo registrado.')
            return redirect(obtener_url_del_detalle_de_prestamo(identificador))
        return self._mostrar_formulario_prestamo()

    def _mostrar_formulario_prestamo(self):
        bien = (
            (
                self.bienes.consultar_bien_disponible_para_prestamo(request.args['id_bien'])
                if request.method == 'GET'
                else self.bienes.consultar_bien_material(request.args['id_bien'])
            )
            if request.args.get('id_bien')
            else None
        )
        id_recurso = bien['id_recurso'] if bien else request.args.get('id_recurso')
        recurso = self.recursos.consultar_recurso(id_recurso) if id_recurso else None
        filtros = {'estado': 'DISPONIBLE'}
        if recurso:
            filtros['id_recurso'] = recurso['id_recurso']
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='formulario',
            bienes=[_preparar_bien_para_formulario_prestamo(b) for b in self.bienes.consultar_bienes_materiales(filtros)],
            bien_seleccionado=bien['id_bien'] if bien else None,
            bien_inicial=_preparar_bien_para_formulario_prestamo(bien) if bien else None,
            bienes_recuperados=(
                [
                    _preparar_bien_para_formulario_prestamo(b)
                    for b in self.bienes.consultar_bienes_materiales({})
                    if str(b['id_bien']) in request.form.getlist('bienes')
                ]
                if request.method == 'POST'
                else []
            ),
            politicas=self.politicas.consultar_politicas_prestamo(),
            horario=self.politicas.consultar_horario_y_plazos_de_reserva(),
            recurso_contexto=recurso,
            cancelar_url=(
                url_for('recursos.consultar_recurso', identificador=recurso['id_recurso'])
                if recurso
                else obtener_url_de_regreso_a_prestamos()
            ),
            volver=obtener_url_de_regreso_a_prestamos(),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def consultar_prestamo(self, identificador):
        gestionar = g.usuario.tiene_permiso('PRESTAMOS_GESTIONAR')
        prestamo = self.servicio.consultar_prestamo(identificador, g.usuario.dni, gestionar)
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='detalle',
            prestamo=prestamo,
            solicitudes=(
                self.ampliaciones.consultar_solicitudes_de_ampliacion_del_prestamo(identificador)
                if self.ampliaciones
                else []
            ),
            gestionar=gestionar,
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
            volver=obtener_url_de_regreso_a_prestamos(),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador: self.consultar_prestamo(identificador))
    def registrar_devolucion(self, identificador):
        datos = dict(request.form, detalles=request.form.getlist('detalles'))
        self.servicio.registrar_devolucion(identificador, datos, g.usuario.id_usuario)
        flash('Devolución registrada.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador, detalle_id: self.consultar_prestamo(identificador))
    def registrar_discrepancia_devolucion(self, identificador, detalle_id):
        self.servicio.registrar_discrepancia_devolucion(
            identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario,
        )
        flash('Discrepancia anotada. El bien sigue pendiente de devolución.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador) + '#devolucion')

    @requiere_permiso('USUARIOS_GESTIONAR')
    @recuperar_formulario_tras_error(lambda self, identificador, detalle_id: self.consultar_prestamo(identificador))
    def rectificar_devolucion(self, identificador, detalle_id):
        self.servicio.rectificar_devolucion(identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario)
        flash('Devolución rectificada. El bien vuelve a quedar pendiente y se conserva el registro anterior.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador) + '#devolucion')

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario_tras_error(
        lambda self, identificador, detalle_id: self.consultar_prestamo(identificador)
    )
    def registrar_perdida_bien_material(self, identificador, detalle_id):
        self.servicio.registrar_perdida_bien_material(
            identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario,
            gravedad=request.form.get('gravedad', 'GRAVE'),
        )
        flash('Pérdida registrada. El bien queda pendiente de recuperación o reposición.')
        return redirect(obtener_url_del_detalle_de_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def actualizar_estados_prestamos_vencidos(self):
        self.servicio.actualizar_estados_prestamos_vencidos(g.usuario.id_usuario)
        flash('Vencimientos registrados.')
        return redirect(obtener_url_de_regreso_a_prestamos())
