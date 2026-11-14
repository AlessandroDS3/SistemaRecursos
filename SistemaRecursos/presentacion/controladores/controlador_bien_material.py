from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN, ESTADOS_MANUALES
from presentacion.seguridad import requiere_permiso


class ControladorBienMaterial:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('bienes', __name__, url_prefix='/bienes')
        for ruta, nombre, funcion, metodos in (
            ('', 'listar', self.listar, ['GET']),
            ('/nuevo', 'nuevo', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>', 'detalle', self.detalle, ['GET']),
            ('/<int:identificador>/editar', 'editar', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>/estado', 'estado', self.estado, ['POST']),
            ('/<int:identificador>/eliminar', 'eliminar', self.eliminar, ['POST']),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('RECURSOS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def listar(self):
        return render_template(
            'vista_bien_material.html',
            modo='lista',
            bienes=self.servicio.listar(request.args),
            estados=ESTADOS_BIEN,
        )

    @requiere_permiso('RECURSOS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def detalle(self, identificador):
        return render_template(
            'vista_bien_material.html',
            modo='detalle',
            bien=self.servicio.consultar(identificador),
            historial=self.servicio.historial(identificador),
            estados=ESTADOS_MANUALES,
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def formulario(self, identificador=None):
        bien = (
            self.servicio.consultar(identificador)
            if identificador
            else {'id_recurso': request.args.get('id_recurso')}
        )
        if request.method == 'POST':
            nuevo = self.servicio.guardar(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Bien guardado.')
            return redirect(url_for('bienes.detalle', identificador=nuevo))
        return render_template(
            'vista_bien_material.html',
            modo='formulario',
            bien=bien,
            recursos=self.recursos.listar({}),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def estado(self, identificador):
        self.servicio.cambiar_estado(identificador, request.form.to_dict(), g.usuario.id_usuario)
        flash('Estado actualizado.')
        return redirect(url_for('bienes.detalle', identificador=identificador))

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar(self, identificador):
        self.servicio.eliminar(identificador, g.usuario.id_usuario)
        return redirect(url_for('bienes.listar'))
