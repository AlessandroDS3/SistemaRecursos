from dataclasses import asdict
from dominio.compartido.validacion import Conflicto, NoEncontrado
from dominio.compartido.validacion import exigir_version_vigente, validar_entero, calcular_version_de_registro
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import TIPOS_PERSONA
from dominio.gestion_control.contratos_control import IRepositorioPoliticaPrestamo
from dominio.gestion_control.politica_prestamo import (
    ConfiguracionReservas,
    HorarioAtencion,
    PoliticaPrestamo,
)


class ServicioAplicacionPoliticaPrestamo:
    def __init__(self, repositorio: IRepositorioPoliticaPrestamo):
        self.repositorio = repositorio

    def consultar_politica_prestamo(self, identificador):
        fila = self.repositorio.consultar_politica_prestamo(validar_entero(identificador))
        if fila is None:
            raise NoEncontrado('Política inexistente.')
        return fila, calcular_version_de_registro(fila)

    def consultar_politicas_prestamo(self):
        return [
            dict(fila, version=calcular_version_de_registro({k: v for k, v in fila.items() if k != 'categoria'}))
            for fila in self.repositorio.consultar_politicas_prestamo()
        ]

    def consultar_horario_y_plazos_de_reserva(self):
        return self.repositorio.consultar_horario_y_plazos_de_reserva() or {}

    def consultar_limites_articulos(self):
        return self.repositorio.consultar_limites_articulos()

    def registrar_politica_prestamo(self, datos, actor):
        return self._guardar_nueva_version_de_politica(datos, actor)

    def actualizar_politica_prestamo(self, identificador, datos, actor):
        return self._guardar_nueva_version_de_politica(datos, actor, validar_entero(identificador))

    def _guardar_nueva_version_de_politica(self, datos, actor, identificador=None):
        politica = PoliticaPrestamo.desde_datos(datos)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(validar_entero(actor)), 'POLITICAS_GESTIONAR')
            if identificador is not None:
                anterior = operacion.consultar_politica_prestamo(identificador, bloquear=True)
                if anterior is None:
                    raise NoEncontrado('Política inexistente.')
                if not anterior['vigente']:
                    raise Conflicto('La política ya no está vigente.')
                exigir_version_vigente(datos.get('version'), calcular_version_de_registro(anterior))
                vigente = PoliticaPrestamo.desde_datos(anterior)
                if all(
                    valor == getattr(vigente, campo)
                    for campo, valor in asdict(politica).items()
                    if campo != 'id_politica'
                ):
                    return identificador
                operacion.desactivar_politica_prestamo(anterior['id_politica'])
            return operacion.insertar_politica_prestamo(politica)

    def guardar_horario_y_plazos_de_reserva(self, datos, actor):
        requeridos = ('hora_apertura', 'hora_cierre', *ConfiguracionReservas.__dataclass_fields__)
        if any(campo not in datos for campo in requeridos):
            raise ValueError('Envía el horario y los cuatro campos de vencimiento juntos.')
        dias = datos.get('dias_atencion')
        if not isinstance(dias, (list, tuple)) or not dias:
            raise ValueError('Selecciona al menos un día de atención.')
        dias_atencion = sum(
            1 << dia for dia in {validar_entero(valor, 'Día de atención', minimo=0, maximo=6) for valor in dias}
        )
        horario = HorarioAtencion(
            hora_apertura=datos['hora_apertura'], hora_cierre=datos['hora_cierre'],
            dias_atencion=dias_atencion,
        )
        plazos = ConfiguracionReservas(
            **{k: datos[k] for k in ConfiguracionReservas.__dataclass_fields__ if k in datos}
        )
        valores = {
            "hora_apertura": horario.hora_apertura,
            "hora_cierre": horario.hora_cierre,
            "dias_atencion": horario.dias_atencion,
            "plazo_espera": plazos.plazo_espera,
            "unidad_espera": plazos.unidad_espera,
            "plazo_retiro": plazos.plazo_retiro,
            "unidad_retiro": plazos.unidad_retiro,
        }
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(validar_entero(actor)), 'POLITICAS_GESTIONAR')
            operacion.guardar_horario_y_plazos_de_reserva(valores)

    def guardar_limite_articulos(self, tipo, cantidad, actor):
        if tipo not in TIPOS_PERSONA:
            raise ValueError('Tipo de persona inválido.')
        self._validar_y_guardar_limites_por_tipo_de_persona({tipo: cantidad}, actor)

    def guardar_limites_articulos(self, cantidades, actor):
        if set(cantidades) != set(TIPOS_PERSONA):
            raise ValueError('Indica el límite de bienes para cada tipo de persona.')
        self._validar_y_guardar_limites_por_tipo_de_persona(cantidades, actor)

    def _validar_y_guardar_limites_por_tipo_de_persona(self, cantidades, actor):
        cantidades = {
            tipo: validar_entero(cantidad, 'Límite de bienes')
            for tipo, cantidad in cantidades.items()
        }
        with self.repositorio.transaccion() as operacion:
            cuenta = exigir_permiso(
                operacion.consultar_cuenta_actor(validar_entero(actor)), 'POLITICAS_GESTIONAR'
            )
            if cuenta['rol'] != 'ADMINISTRADOR':
                raise PermissionError(
                    'Solo el administrador puede modificar el límite de bienes.'
                )
            for tipo, cantidad in cantidades.items():
                operacion.guardar_limite_articulos(tipo, cantidad)

    def eliminar_politica_prestamo(self, identificador, actor):
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(validar_entero(actor)), 'POLITICAS_GESTIONAR')
            identificador = validar_entero(identificador)
            if operacion.consultar_politica_prestamo(identificador, bloquear=True) is None:
                raise NoEncontrado('Política inexistente.')
            operacion.eliminar_politica_prestamo(identificador)
