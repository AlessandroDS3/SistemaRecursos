from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import (
    exigir_version_vigente,
    validar_dni,
    validar_entero,
    validar_texto,
    calcular_version_de_registro,
)
from dominio.gestion_personas_usuarios.contratos_personas_usuarios import IRepositorioPersona
from dominio.gestion_personas_usuarios.persona import (
    ESTADOS_PERSONA,
    Persona,
    TIPOS_PERSONA,
    validar_elegibilidad_del_solicitante,
)
from dominio.gestion_personas_usuarios.cuenta import proteger_administradores
from dominio.gestion_personas_usuarios.acceso import exigir_permiso


class ServicioAplicacionPersona:
    def __init__(self, repositorio: IRepositorioPersona):
        self.repositorio = repositorio

    def consultar_personas(self, filtros) -> dict:
        if filtros.get('estado', '') not in ('', *ESTADOS_PERSONA):
            raise ValueError('Estado de persona inválido.')
        if filtros.get('tipo', '') not in ('', *TIPOS_PERSONA):
            raise ValueError('Tipo de persona inválido.')
        if filtros.get('cuenta', '') not in ('', 'CON_CUENTA', 'SIN_CUENTA'):
            raise ValueError('Filtro de cuenta inválido.')
        return self.repositorio.consultar_personas(
            dict(
                q=validar_texto(filtros.get('q'), 'Búsqueda', 120),
                estado=filtros.get('estado', ''),
                tipo=filtros.get('tipo', ''),
                cuenta=filtros.get('cuenta', ''),
                pagina=validar_entero(filtros.get('pagina', 1), 'Página'),
            )
        )

    def consultar_persona(self, documento: str) -> tuple[Persona, str]:
        fila = self.repositorio.consultar_persona(validar_dni(documento))
        if fila is None:
            raise NoEncontrado('Persona inexistente.')
        persona = Persona.desde_datos(fila)
        return persona, calcular_version_de_registro(persona.como_diccionario())

    def registrar_persona(self, datos: dict, actor: int) -> str:
        return self._validar_y_guardar_persona(datos, actor)

    def consultar_cambios_tipo_persona(self, documento: str) -> list[dict]:
        return self.repositorio.consultar_cambios_tipo_persona(validar_dni(documento))

    def actualizar_persona(self, documento: str, datos: dict, actor: int) -> str:
        return self._validar_y_guardar_persona(datos, actor, validar_dni(documento))

    def _validar_y_guardar_persona(
        self, datos: dict, actor: int, documento_anterior: str | None = None
    ) -> str:
        actor = validar_entero(actor)
        valores = dict(datos)
        if documento_anterior is None:
            valores['estado'] = 'ACTIVA'
        persona = Persona.desde_datos(valores)
        bloquear_cuentas = False
        if documento_anterior is not None:
            # Decide los bloqueos; la versión se vuelve a comprobar dentro de la transacción.
            persona_anterior, version_anterior = self.consultar_persona(documento_anterior)
            exigir_version_vigente(datos.get('version'), version_anterior)
            bloquear_cuentas = (
                persona.estado != persona_anterior.estado or persona.dni != documento_anterior
            )
        with self.repositorio.transaccion() as operacion:
            cuentas = operacion.consultar_cuentas_para_actualizar() if bloquear_cuentas else []
            actor_cuenta = exigir_permiso(operacion.consultar_cuenta_actor(actor), 'PERSONAS_GESTIONAR')
            if documento_anterior is not None:
                # Estado y DNI conservan el orden cuentas -> persona; los demás cambios
                # bloquean únicamente la ficha y sus datos institucionales.
                anterior = operacion.consultar_persona(documento_anterior, bloquear=True)
                if anterior is None:
                    raise NoEncontrado('Persona inexistente.')
                exigir_version_vigente(
                    datos.get('version'), calcular_version_de_registro(Persona.desde_datos(anterior).como_diccionario())
                )
                if persona.tipo != anterior['tipo']:
                    if actor_cuenta['rol'] != 'ADMINISTRADOR':
                        raise PermissionError('Solo el administrador puede cambiar el tipo de persona.')
                    if persona.dni != documento_anterior:
                        raise ValueError('Conserva el DNI al cambiar el tipo de persona.')
                    motivo = validar_texto(datos.get('motivo_cambio_tipo'), 'Motivo del cambio de tipo', 255, True)
                    operacion.cambiar_tipo_persona(anterior, persona, motivo, actor_cuenta['dni_persona'])
                cuenta = next((c for c in cuentas if c['dni_persona'] == documento_anterior), None)
                if cuenta:
                    proteger_administradores(
                        cuentas, cuenta, dict(cuenta, estado_persona=persona.estado), actor
                    )
                    if cuenta['id_usuario'] == actor and persona.estado != 'ACTIVA':
                        raise ValueError('No puedes desactivar tu propia persona.')
                    operacion.cerrar_sesiones_de_cuenta(cuenta['id_usuario'])
            operacion.guardar_persona(persona, documento_anterior)
        return persona.dni

    def desactivar_persona(self, documento: str, actor: int) -> str:
        persona, version_actual = self.consultar_persona(documento)
        datos = dict(persona.como_diccionario(), estado='INACTIVA', version=version_actual)
        return self.actualizar_persona(documento, datos, actor)

    def buscar_personas(self, termino: str) -> list[dict]:
        termino = validar_texto(termino, 'Búsqueda', 120)
        personas = self.repositorio.buscar_personas(termino) if len(termino) >= 2 else []
        for persona in personas:
            persona['nombre_completo'] = f'{persona["nombres"]} {persona["apellidos"]}'
            try:
                validar_elegibilidad_del_solicitante(persona)
                persona['elegible'] = True
            except ValueError:
                persona['elegible'] = False
        return personas
