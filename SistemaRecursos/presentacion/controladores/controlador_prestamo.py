from datetime import datetime, timezone
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorPrestamo:
    def __init__(self, servicio, bienes):
        self.servicio, self.bienes = servicio, bienes
        self.blueprint = Blueprint('prestamos', __name__, url_prefix='/prestamos')
        self.blueprint.add_url_rule(
            '/condiciones', 'consultar_condiciones_prestamo', self.consultar_condiciones_prestamo
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
                'registrar_vencimientos_prestamos',
                self.registrar_vencimientos_prestamos,
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
            'vista_prestamo.html', modo='lista', prestamos=filas, gestionar=gestionar
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def consultar_condiciones_prestamo(self):
        return jsonify(
            self.servicio.consultar_condiciones_prestamo(request.args.get('dni_persona', ''))
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_prestamo(self):
        if request.method == 'POST':
            datos = request.form.to_dict()
            datos.update(
                bienes=request.form.getlist('bienes'),
                participantes=[
                    d.strip() for d in request.form.get('participantes', '').split(',') if d.strip()
                ],
            )
            identificador = self.servicio.registrar_prestamo(datos, g.usuario.id_usuario)
            flash('Préstamo entregado.')
            return redirect(url_for('prestamos.consultar_prestamo', identificador=identificador))
        return render_template(
            'vista_prestamo.html',
            modo='formulario',
            bienes=self.bienes.consultar_bienes_materiales({'estado': 'DISPONIBLE'}),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def consultar_prestamo(self, identificador):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        prestamo = self.servicio.consultar_prestamo(identificador, g.usuario.dni, gestionar)
        return render_template(
            'vista_prestamo.html',
            modo='detalle',
            prestamo=prestamo,
            gestionar=gestionar,
            ahora=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_devolucion(self, identificador):
        datos = dict(request.form, detalles=request.form.getlist('detalles'))
        self.servicio.registrar_devolucion(identificador, datos, g.usuario.id_usuario)
        flash('Devolución registrada.')
        return redirect(url_for('prestamos.consultar_prestamo', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_perdida_bien_material(self, identificador, detalle_id):
        self.servicio.registrar_perdida_bien_material(
            identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario
        )
        flash('Pérdida registrada; el bien continúa pendiente de recuperación.')
        return redirect(url_for('prestamos.consultar_prestamo', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def registrar_vencimientos_prestamos(self):
        self.servicio.registrar_vencimientos_prestamos(g.usuario.id_usuario)
        flash('Vencimientos registrados en el historial.')
        return redirect(url_for('prestamos.consultar_prestamos'))
