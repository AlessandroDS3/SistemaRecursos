"""Campos de datos y filtros admitidos por los reportes."""

from dataclasses import dataclass

from dominio.gestion_control.sancion import ESTADOS_SANCION
from dominio.gestion_personas_usuarios.persona import ESTADOS_PERSONA, TIPOS_PERSONA
from dominio.gestion_recursos.bien_material import ESTADOS_BIEN
from dominio.gestion_prestamos.reserva import ESTADOS_RESERVA
from dominio.gestion_prestamos.prestamo import ESTADOS_PRESTAMO


@dataclass(frozen=True)
class CampoReporte:
    nombre: str
    etiqueta: str


@dataclass(frozen=True)
class DefinicionReporte:
    titulo: str
    descripcion: str
    filtros: tuple[str, ...]
    columnas: tuple[CampoReporte, ...]
    fecha: str = ''
    estados: tuple[str, ...] = ()
    etiqueta_estado: str = 'Estado'
    busqueda: str = 'Persona, DNI, integrante, recurso o inventario'


FILTROS_BIENES = ('desde', 'hasta', 'id_categoria', 'q')
FILTROS_PRESTAMO = (*FILTROS_BIENES, 'modalidad', 'tipo_persona')
TIPOS_EVENTO = ('DANADO', 'PERDIDO')
OPCIONES_FILTROS = {
    'modalidad': ('INDIVIDUAL', 'GRUPAL'),
    'tipo_persona': TIPOS_PERSONA,
    'cumplimiento': ('A_TIEMPO', 'TARDIA'),
    'tipo_gestion': ('PRESTAMO', 'RESERVA'),
}

REPORTES = {
    'prestamos': DefinicionReporte(
        titulo='Préstamos',
        descripcion='Entregas del período y situación actual de sus bienes. Cada bien ocupa una fila. El filtro de estado corresponde al préstamo completo.',
        fecha='entrega',
        filtros=(*FILTROS_PRESTAMO, 'estado'),
        estados=tuple(ESTADOS_PRESTAMO),
        etiqueta_estado='Estado del préstamo',
        columnas=(
            CampoReporte('id_prestamo', 'Préstamo'),
            CampoReporte('dni_persona', 'DNI'),
            CampoReporte('solicitante', 'Solicitante y grupo'),
            CampoReporte('tipo_prestamo', 'Modalidad'),
            CampoReporte('fecha_entrega', 'Entrega'),
            CampoReporte('codigo_inventario', 'Bien'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('fecha_limite_devolucion', 'Fecha límite'),
            CampoReporte('fecha_devolucion', 'Devolución'),
            CampoReporte('situacion', 'Situación del bien'),
            CampoReporte('integrantes', 'Integrantes'),
        ),
    ),
    'devoluciones': DefinicionReporte(
        titulo='Devoluciones y cumplimiento',
        descripcion='Devoluciones del período, comparadas con la fecha límite vigente de cada bien.',
        fecha='devolución',
        filtros=(*FILTROS_BIENES, 'cumplimiento'),
        columnas=(
            CampoReporte('id_prestamo', 'Préstamo'),
            CampoReporte('dni_persona', 'DNI'),
            CampoReporte('solicitante', 'Solicitante y grupo'),
            CampoReporte('tipo_prestamo', 'Modalidad'),
            CampoReporte('codigo_inventario', 'Bien'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('fecha_entrega', 'Entrega'),
            CampoReporte('fecha_limite_devolucion', 'Fecha límite'),
            CampoReporte('fecha_devolucion', 'Devolución'),
            CampoReporte('condicion_devolucion', 'Condición de devolución'),
            CampoReporte('cumplimiento', 'Cumplimiento'),
            CampoReporte('retraso_minutos', 'Retraso'),
            CampoReporte('integrantes', 'Integrantes'),
        ),
    ),
    'atrasados': DefinicionReporte(
        titulo='Bienes atrasados',
        descripcion='Solo bienes pendientes cuyo plazo ya venció. El retraso se calcula en minutos completos al consultar.',
        fecha='vencimiento',
        filtros=FILTROS_BIENES,
        columnas=(
            CampoReporte('id_prestamo', 'Préstamo'),
            CampoReporte('dni_persona', 'DNI'),
            CampoReporte('solicitante', 'Solicitante'),
            CampoReporte('codigo_inventario', 'Bien'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('fecha_entrega', 'Entrega'),
            CampoReporte('fecha_limite_devolucion', 'Fecha límite'),
            CampoReporte('retraso_minutos', 'Retraso'),
        ),
    ),
    'inventario': DefinicionReporte(
        titulo='Inventario',
        descripcion='Situación actual de los bienes. No representa el inventario de una fecha pasada.',
        filtros=('estado', 'id_categoria', 'ubicacion', 'q'),
        estados=ESTADOS_BIEN,
        etiqueta_estado='Estado actual del bien',
        busqueda='Recurso, inventario, marca, modelo o serie',
        columnas=(
            CampoReporte('id_bien', 'Identificador'),
            CampoReporte('codigo_inventario', 'Inventario'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('marca', 'Marca'),
            CampoReporte('modelo', 'Modelo'),
            CampoReporte('numero_serie', 'Serie'),
            CampoReporte('estado', 'Estado'),
            CampoReporte('ubicacion', 'Ubicación'),
            CampoReporte('fecha_adquisicion', 'Adquisición'),
        ),
    ),
    'reservas': DefinicionReporte(
        titulo='Solicitudes y reservas',
        descripcion='Solicitudes registradas en el período y su estado actual.',
        fecha='solicitud',
        filtros=('desde', 'hasta', 'estado', 'tipo_gestion', 'tipo_persona', 'id_categoria', 'q'),
        estados=ESTADOS_RESERVA,
        busqueda='DNI, nombre del solicitante o recurso',
        columnas=(
            CampoReporte('id_reserva', 'Solicitud'),
            CampoReporte('tipo_gestion', 'Tipo de gestión'),
            CampoReporte('dni_persona', 'DNI'),
            CampoReporte('solicitante', 'Solicitante'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('fecha_solicitud', 'Solicitud'),
            CampoReporte('fecha_requerida', 'Retiro solicitado'),
            CampoReporte('estado', 'Estado actual'),
            CampoReporte('fecha_limite_vencimiento', 'Vencimiento'),
        ),
    ),
    'sanciones': DefinicionReporte(
        titulo='Sanciones',
        descripcion='Sanciones del período y su estado actual. En las automáticas, la fecha corresponde al vencimiento que las originó. Los préstamos grupales muestran sus integrantes.',
        fecha='fecha de sanción',
        filtros=(*FILTROS_BIENES, 'estado'),
        estados=ESTADOS_SANCION,
        columnas=(
            CampoReporte('id_sancion', 'Sanción'),
            CampoReporte('gravedad', 'Gravedad'),
            CampoReporte('fecha_fin', 'Fin del periodo'),
            CampoReporte('fecha_regularizacion', 'Regularización'),
            CampoReporte('tipo_regularizacion', 'Forma de regularización'),
            CampoReporte('id_prestamo', 'Préstamo'),
            CampoReporte('dni_persona', 'DNI'),
            CampoReporte('solicitante', 'Responsable y grupo'),
            CampoReporte('tipo_prestamo', 'Modalidad'),
            CampoReporte('codigo_inventario', 'Bien'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('fecha', 'Fecha de sanción'),
            CampoReporte('motivo', 'Motivo'),
            CampoReporte('descripcion', 'Descripción'),
            CampoReporte('estado', 'Estado actual'),
            CampoReporte('fecha_levantamiento', 'Levantamiento'),
            CampoReporte('justificacion_levantamiento', 'Justificación'),
            CampoReporte('integrantes', 'Integrantes'),
        ),
    ),
    'danos_perdidas': DefinicionReporte(
        titulo='Daños y pérdidas',
        descripcion='Eventos del historial de bienes, incluidos los recuperados después. Registrado por identifica al operador que anotó el evento, no atribuye responsabilidad por el daño o pérdida.',
        fecha='evento',
        filtros=('desde', 'hasta', 'estado', 'id_categoria', 'q'),
        estados=TIPOS_EVENTO,
        etiqueta_estado='Tipo de evento',
        busqueda='Recurso, inventario, registrador o descripción',
        columnas=(
            CampoReporte('id_historial_estado', 'Evento'),
            CampoReporte('fecha', 'Fecha del evento'),
            CampoReporte('id_bien', 'Identificador del bien'),
            CampoReporte('codigo_inventario', 'Inventario'),
            CampoReporte('recurso', 'Recurso'),
            CampoReporte('categoria', 'Categoría'),
            CampoReporte('tipo_evento', 'Evento'),
            CampoReporte('estado_actual', 'Estado actual del bien'),
            CampoReporte('dni_registrador', 'DNI del registrador'),
            CampoReporte('registrador', 'Registrado por'),
            CampoReporte('observacion', 'Observación'),
        ),
    ),
    'personas': DefinicionReporte(
        titulo='Personas',
        descripcion='Listado de personas registradas, tengan o no una cuenta de acceso. Cada persona ocupa una fila.',
        filtros=('tipo_persona', 'estado', 'q'),
        estados=ESTADOS_PERSONA,
        etiqueta_estado='Estado de la persona',
        busqueda='DNI, nombres, apellidos o correo',
        columnas=(
            CampoReporte('dni', 'DNI'),
            CampoReporte('nombres', 'Nombres'),
            CampoReporte('apellidos', 'Apellidos'),
            CampoReporte('tipo_persona', 'Tipo de persona'),
            CampoReporte('telefono', 'Teléfono'),
            CampoReporte('correo', 'Correo'),
            CampoReporte('estado', 'Estado'),
        ),
    ),
}

# La cronología comparte sus columnas en pantalla, CSV y PDF.
COLUMNAS_HISTORIAL = tuple(CampoReporte(nombre, etiqueta) for nombre, etiqueta in (
    ('fecha', 'Fecha'), ('evento', 'Evento'), ('referencia', 'Referencia'),
    ('id_prestamo', 'Préstamo'), ('dni_persona', 'DNI del solicitante'),
    ('solicitante', 'Solicitante'), ('tipo_prestamo', 'Modalidad'),
    ('integrantes', 'Integrantes'), ('codigo_inventario', 'Inventario'),
    ('recurso', 'Recurso'), ('registrador', 'Registrado por'),
    ('dni_registrador', 'DNI del registrador'),
    ('estado_anterior', 'Estado anterior'), ('estado_nuevo', 'Estado nuevo'),
    ('transicion', 'Cambio registrado'), ('estado_prestamo', 'Estado actual del préstamo'),
    ('fecha_entrega', 'Entrega'), ('fecha_limite_devolucion', 'Plazo vigente'),
    ('fecha_devolucion', 'Devolución'), ('entregado_por', 'Entregado por'),
    ('recibido_por', 'Devolución recibida por'),
    ('condicion_entrega', 'Condición de entrega'),
    ('condicion_devolucion', 'Condición de devolución'), ('observacion', 'Observación'),
))
REPORTES.update({
    'historial_bien': DefinicionReporte(
        titulo='Historial por objeto',
        descripcion='Busca un bien por nombre del recurso o código de inventario y consulta sus préstamos y eventos registrados.',
        filtros=('codigo_inventario', 'q'), columnas=COLUMNAS_HISTORIAL,
    ),
    'historial_persona': DefinicionReporte(
        titulo='Historial por persona',
        descripcion='Préstamos individuales y grupales, solicitudes, incidencias y sanciones de una persona.',
        filtros=('dni_persona', 'q'), columnas=COLUMNAS_HISTORIAL,
    ),
})
