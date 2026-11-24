from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN, ESTADOS_MANUALES
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario


class ControladorBienMaterial:
    def __init__(self, servicio, recursos):
        self.servicio, self.recursos = servicio, recursos
        self.blueprint = Blueprint('bienes', __name__, url_prefix='/bienes')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_bienes_materiales', self.consultar_bienes_materiales, ['GET']),
            (
                '/nuevo',
                'registrar_bien_material',
                self.registrar_bien_material,
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
                'editar_bien_material',
                self.editar_bien_material,
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
            'recursos/vista_bien_material.html',
            modo='lista',
            bienes=self.servicio.consultar_bienes_materiales(request.args),
            estados=ESTADOS_BIEN,
        )

    @requiere_permiso('RECURSOS_GESTIONAR', 'PRESTAMOS_GESTIONAR')
    def consultar_bien_material(self, identificador):
        return render_template(
            'recursos/vista_bien_material.html',
            modo='detalle',
            **self.servicio.consultar_detalle_bien_material(identificador),
            continuar_registro=session.pop('bien_recien_registrado', None) == identificador,
            estados=ESTADOS_MANUALES,
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(lambda self: self._mostrar_formulario_bien_material())
    def registrar_bien_material(self):
        if request.method == 'POST':
            id_bien_guardado = self.servicio.registrar_bien_material(
                request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Bien guardado.')
            session['bien_recien_registrado'] = id_bien_guardado
            return redirect(
                url_for('bienes.consultar_bien_material', identificador=id_bien_guardado)
            )
        return self._mostrar_formulario_bien_material()

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(
        lambda self, identificador: self._mostrar_formulario_bien_material(identificador)
    )
    def editar_bien_material(self, identificador):
        if request.method == 'POST':
            id_bien_guardado = self.servicio.actualizar_bien_material(
                identificador, request.form.to_dict(), g.usuario.id_usuario
            )
            flash('Bien guardado.')
            return redirect(
                url_for('bienes.consultar_bien_material', identificador=id_bien_guardado)
            )
        return self._mostrar_formulario_bien_material(identificador)

    def _mostrar_formulario_bien_material(self, identificador=None):
        bien = self.servicio.consultar_bien_material(identificador) if identificador else {}
        if identificador is None and request.values.get('id_recurso'):
            if request.method == 'GET':
                bien['id_recurso'] = self.recursos.consultar_recurso(request.values['id_recurso'])[
                    'id_recurso'
                ]
            else:
                bien['id_recurso'] = request.form.get('id_recurso')
        return render_template(
            'recursos/vista_bien_material.html',
            modo='formulario',
            bien=bien,
            recursos=self.recursos.consultar_recursos({}) if identificador is None else [],
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(lambda self, identificador: self.consultar_bien_material(identificador))
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
