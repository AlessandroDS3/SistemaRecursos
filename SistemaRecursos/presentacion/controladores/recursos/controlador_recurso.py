from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN
from presentacion.seguridad import requiere_permiso
from presentacion.formularios import recuperar_formulario


class ControladorRecurso:
    def __init__(self, servicio, bienes, politicas):
        self.servicio, self.bienes, self.politicas = servicio, bienes, politicas
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
                'registrar_recurso',
                self.registrar_recurso,
                ['GET', 'POST'],
            ),
            ('/<int:identificador>', 'consultar_recurso', self.consultar_recurso, ['GET']),
            (
                '/<int:identificador>/editar',
                'editar_recurso',
                self.editar_recurso,
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
            'recursos/vista_recurso.html',
            modo='lista',
            recursos=self.servicio.consultar_recursos(request.args),
            categorias=self.servicio.consultar_categorias(),
        )

    @requiere_permiso('CATALOGO_CONSULTAR', 'RECURSOS_GESTIONAR')
    def consultar_recurso(self, identificador):
        recurso = self.servicio.consultar_recurso(identificador)
        bienes = self.bienes.consultar_bienes_materiales({'id_recurso': identificador})
        return render_template(
            'recursos/vista_recurso.html',
            modo='detalle',
            recurso=recurso,
            continuar_registro=session.pop('recurso_recien_registrado', None) == identificador,
            categoria=self.servicio.consultar_categoria(recurso['id_categoria']),
            bienes=bienes,
            disponibles=sum(b['estado'] == 'DISPONIBLE' for b in bienes),
            politicas=[
                p
                for p in self.politicas.consultar_politicas_prestamo()
                if p['id_categoria'] == recurso['id_categoria']
            ],
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def consultar_administracion_recursos(self):
        resultado = self.servicio.consultar_administracion_recursos(request.args)
        recien_registrado = session.pop('recurso_recien_registrado', None)
        return render_template(
            'recursos/vista_administracion_recursos.html',
            **resultado,
            estados=ESTADOS_BIEN,
            recurso_continuacion=(
                self.servicio.consultar_recurso(recien_registrado) if recien_registrado else None
            ),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(lambda self: self._mostrar_formulario_recurso())
    def registrar_recurso(self):
        if request.method == 'POST':
            id_recurso_guardado = self.servicio.registrar_recurso(
                request.form.to_dict(), g.usuario.id_usuario
            )
            session['recurso_recien_registrado'] = id_recurso_guardado
            return self._redirigir_recurso_guardado(id_recurso_guardado)
        return self._mostrar_formulario_recurso()

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(
        lambda self, identificador: self._mostrar_formulario_recurso(identificador)
    )
    def editar_recurso(self, identificador):
        if request.method == 'POST':
            id_recurso_guardado = self.servicio.actualizar_recurso(
                identificador, request.form.to_dict(), g.usuario.id_usuario
            )
            return self._redirigir_recurso_guardado(id_recurso_guardado)
        return self._mostrar_formulario_recurso(identificador)

    def _redirigir_recurso_guardado(self, identificador):
        flash('Recurso guardado.')
        if request.form.get('volver') == 'administracion':
            return redirect(url_for('recursos.consultar_administracion_recursos'))
        return redirect(url_for('recursos.consultar_recurso', identificador=identificador))

    def _mostrar_formulario_recurso(self, identificador=None):
        recurso = (
            self.servicio.consultar_recurso(identificador) if identificador is not None else {}
        )
        return render_template(
            'recursos/vista_recurso.html',
            modo='formulario',
            recurso=recurso,
            categorias=self.servicio.consultar_categorias(),
            volver=(
                request.values.get('volver')
                if request.values.get('volver') in ('administracion', 'catalogo')
                else ''
            ),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_recurso(self, identificador):
        self.servicio.eliminar_recurso(identificador, g.usuario.id_usuario)
        flash('Recurso eliminado.')
        if request.form.get('volver') == 'administracion':
            return redirect(url_for('recursos.consultar_administracion_recursos'))
        return redirect(url_for('recursos.consultar_recursos'))

    @requiere_permiso('RECURSOS_GESTIONAR')
    @recuperar_formulario(lambda self: self._mostrar_categorias())
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
        return self._mostrar_categorias()

    def _mostrar_categorias(self):
        if request.form.get('volver') == 'administracion':
            return render_template(
                'recursos/vista_administracion_recursos.html',
                **self.servicio.consultar_administracion_recursos({}),
                estados=ESTADOS_BIEN,
                vista_categorias_forzada=True,
            )
        return render_template(
            'recursos/vista_recurso.html', modo='categorias', categorias=self.servicio.consultar_categorias()
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
