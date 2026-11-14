from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN, ESTADOS_MANUALES
from presentacion.seguridad import requiere_permiso


class ControladorBienMaterial:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('bienes', __name__, url_prefix='/bienes')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_bienes_materiales', self.consultar_bienes_materiales, ['GET']),
            (
                '/nuevo',
                'gestionar_formulario_bien_material',
                self.gestionar_formulario_bien_material,
                ['GET', 'POST'],
            ),
            (
                '/<int:identificador>',
                'consultar_bien_material',
                self.consultar_bien_material,
                ['GET'],
            ),
            (
                '/<int:identificador>/editar',
                'gestionar_formulario_bien_material',
                self.gestionar_formulario_bien_material,
                ['GET', 'POST'],
            ),
            (
                '/<int:identificador>/estado',
                'cambiar_estado_bien_material',
                self.cambiar_estado_bien_material,
                ['POST'],
            ),
            (
                '/<int:identificador>/eliminar',
                'eliminar_bien_material',
                self.eliminar_bien_material,
                ['POST'],
            ),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('RECURSOS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_bienes_materiales(self):
        return render_template(
            'vista_bien_material.html',
            modo='lista',
            bienes=self.servicio.consultar_bienes_materiales(request.args),
            estados=ESTADOS_BIEN,
        )

    @requiere_permiso('RECURSOS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_bien_material(self, identificador):
        return render_template(
            'vista_bien_material.html',
            modo='detalle',
            bien=self.servicio.consultar_bien_material(identificador),
            historial=self.servicio.consultar_historial_bien_material(identificador),
            estados=ESTADOS_MANUALES,
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def gestionar_formulario_bien_material(self, identificador=None):
        bien = (
            self.servicio.consultar_bien_material(identificador)
            if identificador
            else {'id_recurso': request.args.get('id_recurso')}
        )
        if request.method == 'POST':
            nuevo = self.servicio.guardar_bien_material(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Bien guardado.')
            return redirect(url_for('bienes.consultar_bien_material', identificador=nuevo))
        return render_template(
            'vista_bien_material.html',
            modo='formulario',
            bien=bien,
            recursos=self.recursos.consultar_recursos({}),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def cambiar_estado_bien_material(self, identificador):
        self.servicio.cambiar_estado_bien_material(
            identificador, request.form.to_dict(), g.usuario.id_usuario
        )
        flash('Estado actualizado.')
        return redirect(url_for('bienes.consultar_bien_material', identificador=identificador))

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_bien_material(self, identificador):
        self.servicio.eliminar_bien_material(identificador, g.usuario.id_usuario)
        return redirect(url_for('bienes.consultar_bienes_materiales'))
