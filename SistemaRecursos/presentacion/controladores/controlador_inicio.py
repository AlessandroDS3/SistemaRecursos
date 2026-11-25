from flask import g, render_template


def registrar_inicio(app, servicios):
    @app.get('/')
    def inicio():
        resumen = {}
        usuario = g.usuario
        gestionar = usuario.permite('PRESTAMOS_GESTIONAR')

        if gestionar or usuario.permite('PRESTAMOS_PROPIOS_CONSULTAR'):
            dni = None if gestionar else usuario.dni
            resumen.update(servicios['prestamos'].consultar_resumen_prestamos(dni))

        if usuario.permite('CATALOGO_CONSULTAR'):
            resumen['bienes_disponibles'] = servicios['recursos'].consultar_disponibilidad()

        solicitudes = (
            len(servicios['ampliaciones'].consultar_solicitudes_ampliacion('PENDIENTE'))
            if gestionar
            else 0
        )

        procesador = (
            servicios['procesador'].consultar_estado_procesador()
            if usuario.permite('USUARIOS_GESTIONAR')
            else None
        )
        return render_template(
            'inicio.html',
            resumen=resumen,
            solicitudes_pendientes=solicitudes,
            procesador=procesador,
        )
