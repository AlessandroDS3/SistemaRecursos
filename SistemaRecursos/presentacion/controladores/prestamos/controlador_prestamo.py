from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario
from presentacion.navegacion import detalle_prestamo, regreso_prestamos
from dominio.gestion_prestamos.prestamo import FILTROS_ESTADO_PRESTAMO


def _bien_formulario(bien):
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
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
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

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_bienes_disponibles(self):
        filtros = dict(request.args, estado='DISPONIBLE')
        return jsonify(
            resultados=[
                _bien_formulario(b) for b in self.bienes.consultar_bienes_materiales(filtros)
            ]
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self: self._mostrar_formulario_prestamo())
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
            return redirect(detalle_prestamo(identificador))
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
            bienes=[_bien_formulario(b) for b in self.bienes.consultar_bienes_materiales(filtros)],
            bien_seleccionado=bien['id_bien'] if bien else None,
            bien_inicial=_bien_formulario(bien) if bien else None,
            bienes_recuperados=(
                [
                    _bien_formulario(b)
                    for b in self.bienes.consultar_bienes_materiales({})
                    if str(b['id_bien']) in request.form.getlist('bienes')
                ]
                if request.method == 'POST'
                else []
            ),
            politicas=self.politicas.consultar_politicas_prestamo(),
            horario=self.politicas.consultar_configuracion_general(),
            recurso_contexto=recurso,
            cancelar_url=(
                url_for('recursos.consultar_recurso', identificador=recurso['id_recurso'])
                if recurso
                else regreso_prestamos()
            ),
            volver=regreso_prestamos(),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def consultar_prestamo(self, identificador):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        prestamo = self.servicio.consultar_prestamo(identificador, g.usuario.dni, gestionar)
        return render_template(
            'prestamos/vista_prestamo.html',
            modo='detalle',
            prestamo=prestamo,
            solicitudes=(
                self.ampliaciones.consultar_solicitudes_prestamo(identificador)
                if self.ampliaciones
                else []
            ),
            gestionar=gestionar,
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
            volver=regreso_prestamos(),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_prestamo(identificador))
    def registrar_devolucion(self, identificador):
        datos = dict(request.form, detalles=request.form.getlist('detalles'))
        self.servicio.registrar_devolucion(identificador, datos, g.usuario.id_usuario)
        flash('Devolución registrada.')
        return redirect(detalle_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    @recuperar_formulario(
        lambda self, identificador, detalle_id: self.consultar_prestamo(identificador)
    )
    def registrar_perdida_bien_material(self, identificador, detalle_id):
        self.servicio.registrar_perdida_bien_material(
            identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario
        )
        flash('Pérdida registrada; el bien continúa pendiente de recuperación.')
        return redirect(detalle_prestamo(identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def actualizar_estados_prestamos_vencidos(self):
        self.servicio.actualizar_estados_prestamos_vencidos(g.usuario.id_usuario)
        flash('Vencimientos registrados.')
        return redirect(regreso_prestamos())
