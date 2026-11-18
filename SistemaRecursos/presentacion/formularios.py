"""Recuperación de formularios sin repetir escrituras ni guardar contraseñas."""

from functools import wraps
import re
import unicodedata

from flask import g, request

from dominio.compartido.validacion import Conflicto


def _normalizar(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto.lower()) if not unicodedata.combining(c)
    )


def recuperar_formulario(mostrar):
    def decorar(operacion):
        @wraps(operacion)
        def protegida(*args, **kwargs):
            try:
                return operacion(*args, **kwargs)
            except ValueError as error:
                if request.method != 'POST':
                    raise
                g.error_formulario = str(error)
                prefijo = {
                    'ampliaciones.ampliar_prestamo': 'ampliacion',
                    'prestamos.registrar_perdida_bien_material': 'perdida',
                }.get(request.endpoint)
                g.formulario_id = (
                    f'{prefijo}-{request.view_args["detalle_id"]}'
                    if prefijo
                    else request.form.get('_formulario', '')
                )
                g.valores_formulario = {
                    nombre: request.form.getlist(nombre)
                    for nombre in request.form
                    if not any(
                        s in nombre.lower()
                        for s in ('clave', 'password', 'contrasena', 'csrf', 'confirmacion')
                    )
                }
                g.errores_campos = _campos_del_error(str(error))
                return mostrar(*args, **kwargs), 409 if isinstance(error, Conflicto) else 400

        return protegida

    return decorar


def _campos_del_error(mensaje):
    aliases = {
        'codigo_inventario': 'codigo de inventario',
        'numero_serie': 'numero de serie',
        'fecha_adquisicion': 'fecha de adquisicion',
        'nombre_usuario': 'usuario',
        'dni': 'dni',
        'cui': 'cui',
        'nombres': 'nombres',
        'apellidos': 'apellidos',
        'correo': 'correo',
        'telefono': 'telefono',
        'ciclo': 'ciclo',
        'id_categoria': 'categoria',
        'id_recurso': 'recurso',
        'fecha_requerida': 'fecha',
        'plazo_maximo': 'plazo',
        'cantidad': 'tiempo adicional',
        'motivo': 'motivo',
        'justificacion': 'justificacion',
        'hora_apertura': 'apertura',
        'hora_cierre': 'cierre',
    }
    texto = _normalizar(mensaje)
    if (
        'dni' in texto
        and re.fullmatch(r'\d{8}', request.form.get('dni', ''))
        and 'cui' in request.form
    ):
        if not re.fullmatch(r'\d{8}', request.form['cui']):
            return {'cui': mensaje}
    for nombre in request.form:
        if nombre.startswith('observacion_') and 'observacion' in texto:
            if nombre.removeprefix('observacion_') in request.form.getlist('detalles'):
                return {nombre: mensaje}
    candidatos = [
        (nombre, aliases.get(nombre, nombre.replace('_', ' '))) for nombre in request.form
    ]
    for nombre, etiqueta in sorted(candidatos, key=lambda fila: -len(fila[1])):
        if re.search(r'\b' + re.escape(etiqueta) + r'\b', texto):
            return {nombre: mensaje}
    return {}


def valor_formulario(nombre, actual='', formulario=''):
    if getattr(g, 'formulario_id', '') and g.formulario_id != formulario:
        return actual
    valores = getattr(g, 'valores_formulario', {})
    return valores[nombre][0] if valores.get(nombre) else actual


def error_campo(nombre, formulario=''):
    if getattr(g, 'formulario_id', '') and g.formulario_id != formulario:
        return ''
    return getattr(g, 'errores_campos', {}).get(nombre, '')


def identificador_campo(nombre):
    g.indice_campo = getattr(g, 'indice_campo', 0) + 1
    return f'campo-{nombre}-{g.indice_campo}'
