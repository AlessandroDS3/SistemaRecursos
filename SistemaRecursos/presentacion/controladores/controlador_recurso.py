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
        recursos = self.servicio.consultar_recursos(
            {'id_categoria': request.args.get('id_categoria')}
        )
        bienes = self.bienes.consultar_bienes_materiales(request.args)
        por_recurso = {}
        for bien in bienes:
            por_recurso.setdefault(bien['id_recurso'], []).append(bien)
        coincidentes = {r['id_recurso'] for r in self.servicio.consultar_recursos(request.args)}
        grupos = [
            dict(recurso=r, bienes=por_recurso.get(r['id_recurso'], []))
            for r in recursos
            if (not request.args.get('q') and not request.args.get('estado'))
            or r['id_recurso'] in por_recurso
            or (not request.args.get('estado') and r['id_recurso'] in coincidentes)
        ]
        visibles = [b for grupo in grupos for b in grupo['bienes']]
        return render_template(
            'vista_administracion_recursos.html',
            grupos=grupos,
            categorias=self.servicio.consultar_categorias(),
            estados=ESTADOS_BIEN,
            resumen={
                'recursos': len(grupos),
                'bienes': len(visibles),
                'disponibles': sum(b['estado'] == 'DISPONIBLE' for b in visibles),
            },
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def gestionar_formulario_recurso(self, identificador=None):
        recurso = self.servicio.consultar_recurso(identificador) if identificador else {}
        if request.method == 'POST':
            nuevo = self.servicio.guardar_recurso(
                request.form.to_dict(), g.usuario.id_usuario, identificador
            )
            flash('Recurso guardado.')
            if request.form.get('volver') == 'administracion':
                return redirect(url_for('recursos.consultar_administracion_recursos'))
            return redirect(url_for('recursos.consultar_recurso', identificador=nuevo))
        return render_template(
            'vista_recurso.html',
            modo='formulario',
            recurso=recurso,
            categorias=self.servicio.consultar_categorias(),
        )

    @requiere_permiso('RECURSOS_GESTIONAR')
    def eliminar_recurso(self, identificador):
        self.servicio.eliminar_recurso(identificador, g.usuario.id_usuario)
        flash('Recurso eliminado.')
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
                    url_for('recursos.consultar_administracion_recursos', _anchor='categorias')
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
                url_for('recursos.consultar_administracion_recursos', _anchor='categorias')
            )
        return redirect(url_for('recursos.gestionar_categorias'))
