from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorPrestamo:
    def __init__(self, servicio, bienes):
        self.servicio, self.bienes = servicio, bienes
        self.blueprint = Blueprint('prestamos', __name__, url_prefix='/prestamos')
        self.blueprint.add_url_rule('/condiciones', 'condiciones', self.condiciones)
        for ruta, nombre, funcion, metodos in (
            ('', 'listar', self.listar, ['GET']),
            ('/nuevo', 'nuevo', self.nuevo, ['GET', 'POST']),
            ('/<int:identificador>', 'detalle', self.detalle, ['GET']),
            ('/<int:identificador>/devolver', 'devolver', self.devolver, ['POST']),
            (
                '/<int:identificador>/detalles/<int:detalle_id>/perdida',
                'perdida',
                self.perdida,
                ['POST'],
            ),
            ('/vencimientos', 'vencimientos', self.vencimientos, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def listar(self):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        filas = self.servicio.listar(request.args, None if gestionar else g.usuario.dni)
        return render_template(
            'vista_prestamo.html', modo='lista', prestamos=filas, gestionar=gestionar
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def condiciones(self):
        return jsonify(self.servicio.condiciones(request.args.get('dni_persona', '')))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def nuevo(self):
        if request.method == 'POST':
            datos = request.form.to_dict()
            datos.update(
                bienes=request.form.getlist('bienes'),
                participantes=[
                    d.strip() for d in request.form.get('participantes', '').split(',') if d.strip()
                ],
            )
            identificador = self.servicio.registrar(datos, g.usuario.id_usuario)
            flash('Préstamo entregado.')
            return redirect(url_for('prestamos.detalle', identificador=identificador))
        return render_template(
            'vista_prestamo.html',
            modo='formulario',
            bienes=self.bienes.listar({'estado': 'DISPONIBLE'}),
        )

    @requiere_permiso('PRESTAMOS_PROPIOS_CONSULTAR', 'PRESTAMOS_GESTIONAR')
    def detalle(self, identificador):
        gestionar = g.usuario.permite('PRESTAMOS_GESTIONAR')
        prestamo = self.servicio.consultar(identificador, g.usuario.dni, gestionar)
        return render_template(
            'vista_prestamo.html', modo='detalle', prestamo=prestamo, gestionar=gestionar
        )

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def devolver(self, identificador):
        datos = dict(request.form, detalles=request.form.getlist('detalles'))
        self.servicio.devolver(identificador, datos, g.usuario.id_usuario)
        flash('Devolución registrada.')
        return redirect(url_for('prestamos.detalle', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def perdida(self, identificador, detalle_id):
        self.servicio.reportar_perdida(
            identificador, detalle_id, request.form.get('motivo'), g.usuario.id_usuario
        )
        flash('Pérdida registrada; el bien continúa pendiente de recuperación.')
        return redirect(url_for('prestamos.detalle', identificador=identificador))

    @requiere_permiso('PRESTAMOS_GESTIONAR')
    def vencimientos(self):
        self.servicio.actualizar_vencimientos(g.usuario.id_usuario)
        flash('Vencimientos registrados en el historial.')
        return redirect(url_for('prestamos.listar'))
