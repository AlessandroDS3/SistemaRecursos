from flask import render_template
from mysql.connector import Error as ErrorMySQL
from werkzeug.exceptions import HTTPException

from dominio.compartido.validacion import Conflicto, NoEncontrado


def registrar_manejadores_de_errores_http(app):
    def renderizar_pagina_de_error(mensaje, codigo):
        return render_template('error.html', mensaje=mensaje, codigo=codigo), codigo

    @app.errorhandler(Conflicto)
    def responder_conflicto(error):
        return renderizar_pagina_de_error(str(error), 409)

    @app.errorhandler(ValueError)
    def responder_error_de_validacion(error):
        return renderizar_pagina_de_error(str(error), 400)

    @app.errorhandler(NoEncontrado)
    def responder_registro_no_encontrado(error):
        return renderizar_pagina_de_error(str(error), 404)

    @app.errorhandler(PermissionError)
    def responder_acceso_denegado(error):
        return renderizar_pagina_de_error(str(error), 403)

    @app.errorhandler(HTTPException)
    def responder_excepcion_http(error):
        mensajes = {
            400: 'Revisa los datos e inténtalo de nuevo.',
            403: 'Tu cuenta no tiene permiso para esta operación.',
            404: 'No se encontró la página solicitada.',
            405: 'Esta acción no está disponible desde esta página.',
            413: 'La información enviada es demasiado grande.',
            500: 'No se pudo completar la operación. Inténtalo de nuevo.',
        }
        mensaje = error.description
        if mensaje == type(error).description:
            mensaje = mensajes.get(error.code, 'No se pudo completar la operación.')
        return renderizar_pagina_de_error(mensaje, error.code)

    @app.errorhandler(ErrorMySQL)
    def responder_error_de_base_de_datos(error):
        app.logger.exception('Falló la base de datos.')
        return renderizar_pagina_de_error(
            'El sistema no está disponible. Inténtalo de nuevo en un momento.', 503
        )
