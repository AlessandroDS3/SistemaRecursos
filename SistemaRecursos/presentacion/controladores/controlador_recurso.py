from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN
from presentacion.seguridad import requiere_permiso


class ControladorRecurso:
    def __init__(self, servicio, bienes):
        self.servicio, self.bienes = servicio, bienes
        self.blueprint = Blueprint('recursos', __name__, url_prefix='/recursos')
        for ruta, nombre, funcion, metodos in (
            ('', 'consultar_recursos', self.consultar_recursos, ['GET']),
            (
                '/administracion',
                'consultar_administracion_recursos',
                self.consultar_administracion_recursos,
                ['GET'],
            ),
            (
                '/nuevo',
                'gestionar_formulario_recurso',
                self.gestionar_formulario_recurso,
                ['GET', 'POST'],
            ),
            ('/<int:identificador>', 'consultar_recurso', self.consultar_recurso, ['GET']),
            (
                '/<int:identificador>/editar',
                'gestionar_formulario_recurso',
                self.gestionar_formulario_recurso,
                ['GET', 'POST'],
            ),
            ('/<int:identificador>/eliminar', 'eliminar_recurso', self.eliminar_recurso, ['POST']),
            ('/categorias', 'gestionar_categorias', self.gestionar_categorias, ['GET', 'POST']),
            (
                '/categorias/<int:identificador>/eliminar',
                'eliminar_categoria',
                self.eliminar_categoria,
                ['POST'],
            ),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('CATALOGO_CONSULTAR', 'RECURSOS_GESTIONAR')
    def consultar_recursos(self):
        return render_template(
            'vista_recurso.html',
            modo='lista',
            recursos=self.servicio.consultar_recursos(request.args),
            categorias=self.servicio.consultar_categorias(),
        )

    @requiere_permiso('CATALOGO_CONSULTAR', 'RECURSOS_GESTIONAR')
    def consultar_recurso(self, identificador):
        return render_template(
            'vista_recurso.html',
            modo='detalle',
            recurso=self.servicio.consultar_recurso(identificador),
            bienes=self.bienes.consultar_bienes_materiales({'id_recurso': identificador}),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def consultar_administracion_recursos(self):
        resultado = self.servicio.consultar_administracion_recursos(request.args)
        return render_template(
            'vista_administracion_recursos.html',
            **resultado,
            estados=ESTADOS_BIEN,
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def gestionar_formulario_recurso(self, identificador=None):
        if request.method == 'POST':
            id_recurso_guardado = self.servicio.guardar_recurso(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Recurso guardado.')
            if request.form.get('volver') == 'administracion':
                return redirect(url_for('recursos.consultar_administracion_recursos'))
            return redirect(
                url_for('recursos.consultar_recurso', identificador=id_recurso_guardado)
            )
        recurso = (
            self.servicio.consultar_recurso(identificador) if identificador is not None else {}
        )
        return render_template(
            'vista_recurso.html',
            modo='formulario',
            recurso=recurso,
            categorias=self.servicio.consultar_categorias(),
            volver='administracion' if request.args.get('volver') == 'administracion' else '',
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_recurso(self, identificador):
        self.servicio.eliminar_recurso(identificador, g.usuario.id_usuario)
        flash('Recurso eliminado.')
        if request.form.get('volver') == 'administracion':
            return redirect(url_for('recursos.consultar_administracion_recursos'))
        return redirect(url_for('recursos.consultar_recursos'))

    @requiere_permiso('RECURSOS_GESTIONAR')
    def gestionar_categorias(self):
        if request.method == 'POST':
            self.servicio.guardar_categoria(
                request.form.to_dict(),
                g.usuario.id_usuario,
                request.form.get('id_categoria') or None,
            )
            flash('Categoría guardada.')
            if request.form.get('volver') == 'administracion':
                return redirect(
                    url_for(
                        'recursos.consultar_administracion_recursos',
                        vista='categorias',
                        _anchor='categorias',
                    )
                )
            return redirect(url_for('recursos.gestionar_categorias'))
        return render_template(
            'vista_recurso.html', modo='categorias', categorias=self.servicio.consultar_categorias()
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_categoria(self, identificador):
        self.servicio.eliminar_categoria(identificador, g.usuario.id_usuario)
        if request.form.get('volver') == 'administracion':
            return redirect(
                url_for(
                    'recursos.consultar_administracion_recursos',
                    vista='categorias',
                    _anchor='categorias',
                )
            )
        return redirect(url_for('recursos.gestionar_categorias'))
