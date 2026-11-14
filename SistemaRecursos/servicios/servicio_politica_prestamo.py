from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import comprobar_version, entero, version
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
from dominio.gestion_control.politica_prestamo import (
    ConfiguracionReservas,
    HorarioAtencion,
    IRepositorioPoliticaPrestamo,
    PoliticaPrestamo,
)


class ServicioAplicacionPoliticaPrestamo:
    def __init__(self, repositorio: IRepositorioPoliticaPrestamo):
        self.repositorio = repositorio

    def consultar_politica_prestamo(self, identificador):
        fila = self.repositorio.consultar_politica_prestamo(entero(identificador))
        if fila is None:
            raise NoEncontrado('Política inexistente.')
        return fila, version(fila)

    def consultar_politicas_prestamo(self):
        return self.repositorio.consultar_politicas_prestamo()

    def consultar_configuracion_general(self):
        return self.repositorio.consultar_configuracion_general() or {}

    def consultar_limites_articulos(self):
        return self.repositorio.consultar_limites_articulos()

    def guardar_politica_prestamo(self, datos, actor, identificador=None):
        politica = PoliticaPrestamo.desde_datos(datos)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            if identificador:
                anterior = operacion.consultar_politica_prestamo(
                    entero(identificador), bloquear=True
                )
                if anterior is None or not anterior['vigente']:
                    raise ValueError('La política ya no está vigente.')
                comprobar_version(datos.get('version'), version(anterior))
                operacion.desactivar_politica_prestamo(anterior['id_politica'])
            return operacion.guardar_politica_prestamo(politica)

    def guardar_configuracion_general(self, datos, actor):
        horario = HorarioAtencion(
            hora_apertura=datos.get('hora_apertura'), hora_cierre=datos.get('hora_cierre')
        )
        plazos = ConfiguracionReservas(
            **{k: datos[k] for k in ConfiguracionReservas.__dataclass_fields__ if k in datos}
        )
        valores = {
            "hora_apertura": horario.hora_apertura,
            "hora_cierre": horario.hora_cierre,
            "plazo_espera": plazos.plazo_espera,
            "unidad_espera": plazos.unidad_espera,
            "plazo_retiro": plazos.plazo_retiro,
            "unidad_retiro": plazos.unidad_retiro,
        }
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            operacion.guardar_configuracion_general(valores)

    def guardar_limite_articulos(self, tipo, cantidad, actor):
        if tipo not in TIPOS_PERSONA:
            raise ValueError('Tipo de persona inválido.')
        cantidad = entero(cantidad, 'Máximo total de bienes')
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR'
            )
            if cuenta['rol'] != 'ADMINISTRADOR':
                raise PermissionError(
                    'Solo el administrador modifica el límite total de artículos.'
                )
            operacion.guardar_limite_articulos(tipo, cantidad)

    def eliminar_politica_prestamo(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            identificador = entero(identificador)
            if operacion.consultar_politica_prestamo(identificador, bloquear=True) is None:
                raise NoEncontrado('Política inexistente.')
            operacion.eliminar_politica_prestamo(identificador)
