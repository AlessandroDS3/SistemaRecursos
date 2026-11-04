from mysql.connector import IntegrityError


def error_formulario(error, mensaje_duplicado):
    """Solo convierte errores esperados; los demás siguen al manejador general."""
    if isinstance(error, ValueError):
        return str(error)
    if isinstance(error, IntegrityError) and error.errno == 1062:
        return mensaje_duplicado
    raise error
