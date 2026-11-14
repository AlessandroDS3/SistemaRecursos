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

    def consultar(self, identificador):
        fila = self.repositorio.consultar(entero(identificador))
        if fila is None:
            raise NoEncontrado('Política inexistente.')
        return fila, version(fila)

    def listar(self):
        return self.repositorio.listar()

    def configuracion(self):
        return self.repositorio.configuracion() or {}

    def limites(self):
        return self.repositorio.limites()

    def guardar(self, datos, actor, identificador=None):
        politica = PoliticaPrestamo.desde_datos(datos)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            if identificador:
                anterior = operacion.consultar(entero(identificador), bloquear=True)
                if anterior is None or not anterior['vigente']:
                    raise ValueError('La política ya no está vigente.')
                comprobar_version(datos.get('version'), version(anterior))
                operacion.desactivar(anterior['id_politica'])
            return operacion.guardar(politica)

    def guardar_configuracion(self, datos, actor):
        horario = HorarioAtencion(
            hora_apertura=datos.get('hora_apertura'), hora_cierre=datos.get('hora_cierre')
        )
        plazos = ConfiguracionReservas(
            **{k: datos[k] for k in ConfiguracionReservas.__dataclass_fields__ if k in datos}
        )
        valores = dict(
            hora_apertura=horario.hora_apertura,
            hora_cierre=horario.hora_cierre,
            plazo_espera=plazos.plazo_espera,
            unidad_espera=plazos.unidad_espera,
            plazo_retiro=plazos.plazo_retiro,
            unidad_retiro=plazos.unidad_retiro,
        )
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            operacion.guardar_configuracion(valores)

    def guardar_limite(self, tipo, cantidad, actor):
        if tipo not in TIPOS_PERSONA:
            raise ValueError('Tipo de persona inválido.')
        cantidad = entero(cantidad, 'Máximo total de bienes')
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(operacion.cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            if cuenta['rol'] != 'ADMINISTRADOR':
                raise PermissionError(
                    'Solo el administrador modifica el límite total de artículos.'
                )
            operacion.guardar_limite(tipo, cantidad)

    def eliminar(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'POLITICAS_GESTIONAR')
            identificador = entero(identificador)
            if operacion.consultar(identificador, bloquear=True) is None:
                raise NoEncontrado('Política inexistente.')
            operacion.eliminar(identificador)
