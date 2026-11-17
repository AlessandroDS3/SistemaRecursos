"""Campos de datos, indicadores y filtros admitidos por los reportes."""

from dataclasses import dataclass
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
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
    indicadores: tuple[CampoReporte, ...]
    fecha: str = ''
    estados: tuple[str, ...] = ()
    etiqueta_estado: str = 'Estado'
    busqueda: str = 'Persona, DNI, integrante, recurso o inventario'


FILTROS_PRESTAMO = ('desde', 'hasta', 'modalidad', 'tipo_persona', 'id_categoria', 'q')
ESTADOS_SANCION = ('ACTIVA', 'CUMPLIDA', 'LEVANTADA', 'ANULADA')
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
        indicadores=(
            CampoReporte('prestamos', 'Préstamos'),
            CampoReporte('detalles', 'Bienes'),
            CampoReporte('devueltos', 'Devueltos'),
            CampoReporte('pendientes', 'Pendientes'),
            CampoReporte('vencidos', 'Bienes vencidos pendientes'),
        ),
    ),
    'devoluciones': DefinicionReporte(
        titulo='Devoluciones y cumplimiento',
        descripcion='Devoluciones del período, comparadas con la fecha límite vigente de cada bien. Los porcentajes corresponden al resultado filtrado; el promedio de retraso incluye solo las tardías.',
        fecha='devolución',
        filtros=(*FILTROS_PRESTAMO, 'estado', 'cumplimiento'),
        estados=tuple(ESTADOS_PRESTAMO),
        etiqueta_estado='Estado actual del préstamo',
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
        indicadores=(
            CampoReporte('detalles', 'Bienes devueltos'),
            CampoReporte('puntuales', 'A tiempo'),
            CampoReporte('tardias', 'Tardías'),
            CampoReporte('porcentaje_puntual', 'Cumplimiento'),
            CampoReporte('retraso_promedio', 'Retraso promedio de tardías'),
        ),
    ),
    'atrasados': DefinicionReporte(
        titulo='Bienes atrasados',
        descripcion='Solo bienes pendientes cuyo plazo ya venció. El retraso se calcula en minutos completos al consultar.',
        fecha='vencimiento',
        filtros=FILTROS_PRESTAMO,
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
        indicadores=(
            CampoReporte('detalles', 'Bienes atrasados'),
            CampoReporte('prestamos', 'Préstamos'),
            CampoReporte('responsables', 'Responsables principales'),
            CampoReporte('retraso_maximo', 'Mayor retraso'),
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
        indicadores=(
            CampoReporte('detalles', 'Bienes'),
            CampoReporte('recursos', 'Recursos'),
            CampoReporte('disponibles', 'Disponibles'),
            CampoReporte('prestados', 'Prestados'),
            CampoReporte('reservados', 'Reservados'),
            CampoReporte('danados', 'Dañados'),
            CampoReporte('mantenimiento', 'En mantenimiento'),
            CampoReporte('perdidos', 'Perdidos'),
        ),
    ),
    'reservas': DefinicionReporte(
        titulo='Solicitudes y reservas',
        descripcion='Solicitudes registradas en el período y su estado actual.',
        fecha='solicitud',
        filtros=('desde', 'hasta', 'estado', 'tipo_gestion', 'tipo_persona', 'id_categoria', 'q'),
        estados=ESTADOS_RESERVA,
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
        indicadores=(
            CampoReporte('detalles', 'Solicitudes'),
            CampoReporte('pendientes', 'Pendientes'),
            CampoReporte('atendidas', 'Atendidas'),
            CampoReporte('canceladas', 'Canceladas'),
            CampoReporte('rechazadas', 'Rechazadas'),
            CampoReporte('expiradas', 'Expiradas'),
        ),
    ),
    'sanciones': DefinicionReporte(
        titulo='Sanciones',
        descripcion='Sanciones del período y su estado actual. En las automáticas, la fecha corresponde al vencimiento que las originó. Los préstamos grupales muestran sus integrantes.',
        fecha='fecha de sanción',
        filtros=(*FILTROS_PRESTAMO, 'estado'),
        estados=ESTADOS_SANCION,
        columnas=(
            CampoReporte('id_sancion', 'Sanción'),
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
        indicadores=(
            CampoReporte('detalles', 'Sanciones'),
            CampoReporte('activas', 'Activas'),
            CampoReporte('levantadas', 'Levantadas'),
            CampoReporte('cumplidas', 'Cumplidas'),
            CampoReporte('anuladas', 'Anuladas'),
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
        indicadores=(
            CampoReporte('detalles', 'Eventos'),
            CampoReporte('bienes', 'Bienes afectados'),
            CampoReporte('danos', 'Daños registrados'),
            CampoReporte('perdidas', 'Pérdidas registradas'),
        ),
    ),
}
