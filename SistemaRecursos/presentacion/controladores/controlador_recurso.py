from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from presentacion.seguridad import requiere_permiso


class ControladorRecurso:
    def __init__(self, servicio, bienes):
        self.servicio, self.bienes = servicio, bienes
        self.blueprint = Blueprint('recursos', __name__, url_prefix='/recursos')
        for ruta, nombre, funcion, metodos in (
            ('', 'listar', self.listar, ['GET']),
            ('/nuevo', 'nuevo', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>', 'detalle', self.detalle, ['GET']),
            ('/<int:identificador>/editar', 'editar', self.formulario, ['GET', 'POST']),
            ('/<int:identificador>/eliminar', 'eliminar', self.eliminar, ['POST']),
            ('/categorias', 'categorias', self.categorias, ['GET', 'POST']),
            (
                '/categorias/<int:identificador>/eliminar',
                'eliminar_categoria',
                self.eliminar_categoria,
                ['POST'],
            ),
        ):
            self.blueprint.add_url_rule(ruta, nombre, funcion, methods=metodos)

    @requiere_permiso('CATALOGO_CONSULTAR', 'RECURSOS_GESTIONAR')
    def listar(self):
        return render_template(
            'vista_recurso.html',
            modo='lista',
            recursos=self.servicio.listar(request.args),
            categorias=self.servicio.categorias(),
        )

    @requiere_permiso('CATALOGO_CONSULTAR', 'RECURSOS_GESTIONAR')
    def detalle(self, identificador):
        return render_template(
            'vista_recurso.html',
            modo='detalle',
            recurso=self.servicio.consultar(identificador),
            bienes=self.bienes.listar({'id_recurso': identificador}),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def formulario(self, identificador=None):
        recurso = self.servicio.consultar(identificador) if identificador else {}
        if request.method == 'POST':
            nuevo = self.servicio.guardar(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Recurso guardado.')
            return redirect(url_for('recursos.detalle', identificador=nuevo))
        return render_template(
            'vista_recurso.html',
            modo='formulario',
            recurso=recurso,
            categorias=self.servicio.categorias(),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar(self, identificador):
        self.servicio.eliminar(identificador, g.usuario.id_usuario)
        flash('Recurso eliminado.')
        return redirect(url_for('recursos.listar'))

    @requiere_permiso('RECURSOS_GESTIONAR')
    def categorias(self):
        if request.method == 'POST':
            self.servicio.guardar_categoria(
                request.form.to_dict(),
                g.usuario.id_usuario,
                request.form.get('id_categoria') or None,
            )
            flash('Categoría guardada.')
            return redirect(url_for('recursos.categorias'))
        return render_template(
            'vista_recurso.html', modo='categorias', categorias=self.servicio.categorias()
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_categoria(self, identificador):
        self.servicio.eliminar_categoria(identificador, g.usuario.id_usuario)
        return redirect(url_for('recursos.categorias'))
