from flask import g, render_template


def registrar_inicio(app, servicios):
    @app.get('/')
    def inicio():
        resumen = {}
        usuario = g.usuario
        gestionar = usuario.tiene_permiso('PRESTAMOS_GESTIONAR')

        if gestionar or usuario.tiene_permiso('PRESTAMOS_PROPIOS_CONSULTAR'):
            dni = None if gestionar else usuario.dni
            resumen.update(servicios['prestamos'].consultar_resumen_prestamos(dni))

        if gestionar or usuario.tiene_permiso('RESERVAS_PROPIAS_GESTIONAR'):
            resumen['reservas_pendientes'] = servicios['reservas'].contar_reservas_pendientes(
                None if gestionar else usuario.dni
            )

        if usuario.tiene_permiso('CATALOGO_CONSULTAR'):
            resumen['bienes_disponibles'] = servicios['recursos'].contar_bienes_disponibles()

        solicitudes = (
            len(servicios['ampliaciones'].consultar_solicitudes_ampliacion('PENDIENTE'))
            if gestionar
            else 0
        )

        procesador = (
            servicios['procesador'].consultar_estado_procesador()
            if usuario.tiene_permiso('USUARIOS_GESTIONAR')
            else None
        )
        return render_template(
            'inicio.html',
            resumen=resumen,
            solicitudes_pendientes=solicitudes,
            procesador=procesador,
        )
