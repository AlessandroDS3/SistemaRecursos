from dominio.compartido.validacion import Conflicto, NoEncontrado, comprobar_version
from werkzeug.security import check_password_hash, generate_password_hash
from dominio.compartido.validacion import dni, entero
from dominio.gestion_personas_usuarios.contratos_personas_usuarios import IRepositorioCuenta
from dominio.gestion_personas_usuarios.cuenta import (
    CuentaCreada,
    ESTADOS_CUENTA,
    base_nombre_usuario,
    generar_clave_temporal,
    nombre_usuario_disponible,
    proteger_administradores,
    validar_clave,
    validar_nombre_usuario,
    version_cuenta,
)
from dominio.gestion_personas_usuarios.rol import ROLES
from dominio.gestion_personas_usuarios.acceso import exigir_permiso
from dominio.gestion_personas_usuarios.persona import Persona


class ServicioAplicacionCuenta:
    def __init__(self, repositorio: IRepositorioCuenta, dominios_institucionales=('unsa.edu.pe',)):
        self.repositorio = repositorio
        self.dominios_institucionales = tuple(
            dominio.strip().lower().lstrip('@')
            for dominio in dominios_institucionales
            if dominio.strip()
        )

    def cambiar_clave_propia(self, actor: int, actual: str, nueva: str, confirmacion: str) -> None:
        actor = entero(actor)
        nueva = validar_clave(nueva)
        if nueva != confirmacion:
            raise ValueError('La nueva contraseña y su confirmación no coinciden.')
        if not isinstance(actual, str) or not 1 <= len(actual) <= 256:
            raise ValueError('Introduce tu contraseña actual.')
        with self.repositorio.transaccion() as operacion:
            cuenta = operacion.consultar_cuenta_para_cambiar_clave(actor)
            if (
                cuenta is None
                or cuenta['estado_cuenta'] != 'ACTIVA'
                or cuenta['estado_persona'] != 'ACTIVA'
            ):
                raise PermissionError('La cuenta no tiene acceso activo.')
            if not check_password_hash(cuenta['contrasena_hash'], actual):
                raise ValueError('La contraseña actual es incorrecta.')
            if check_password_hash(cuenta['contrasena_hash'], nueva):
                raise ValueError('La nueva contraseña debe ser diferente de la actual.')
            operacion.actualizar_cuenta(
                actor,
                {
                    'contrasena_hash': generate_password_hash(nueva, method='scrypt'),
                    'debe_cambiar_clave': False,
                },
            )

    def consultar_cuenta(self, documento: str) -> dict:
        cuenta = self.repositorio.consultar_cuenta(dni(documento))
        if cuenta is None:
            raise NoEncontrado('La persona no tiene una cuenta de acceso.')
        cuenta['version'] = version_cuenta(cuenta)
        cuenta.pop('contrasena_hash')
        return cuenta

    def tiene_cuenta(self, documento: str) -> bool:
        return self.repositorio.consultar_cuenta(dni(documento)) is not None

    def consultar_propuesta_cuenta(self, documento: str) -> dict:
        persona = self._validar_persona_sin_cuenta(self.repositorio, dni(documento))
        try:
            nombre = self._proponer_nombre(self.repositorio, persona)
        except ValueError:
            nombre = ''
        return dict(nombre_usuario=nombre)

    def _proponer_nombre(self, repositorio, persona):
        base = base_nombre_usuario(persona, self.dominios_institucionales)
        ocupados = repositorio.consultar_nombres_usuario(base[:45])
        return nombre_usuario_disponible(base, ocupados)

    @staticmethod
    def _validar_persona_sin_cuenta(
        repositorio: IRepositorioCuenta, documento: str, bloquear=False
    ) -> dict:
        persona = repositorio.consultar_persona_para_cuenta(documento, bloquear=bloquear)
        if persona is None:
            raise NoEncontrado('Persona inexistente.')
        if persona['estado'] != 'ACTIVA':
            raise ValueError('La persona debe estar activa para crear su cuenta.')
        if repositorio.consultar_cuenta(documento) is not None:
            raise Conflicto('La persona ya tiene una cuenta de acceso.')
        return persona

    def registrar_cuenta(self, documento: str, nombre: str, actor: int) -> CuentaCreada:
        documento = dni(documento)
        actor = entero(actor)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'USUARIOS_GESTIONAR')
            persona = self._validar_persona_sin_cuenta(operacion, documento, bloquear=True)
            nombre = (
                validar_nombre_usuario(nombre)
                if nombre
                else self._proponer_nombre(operacion, persona)
            )
            if operacion.consultar_id_por_nombre_usuario(nombre) is not None:
                raise Conflicto('El nombre de usuario ya está registrado.')
            clave = generar_clave_temporal()
            identificador = operacion.registrar_cuenta(
                documento,
                nombre,
                generate_password_hash(clave, method='scrypt'),
            )
            return CuentaCreada(identificador, nombre, clave)

    def registrar_primer_administrador(self, datos: dict, nombre: str) -> CuentaCreada:
        """Inicialización local de una base que aún no tiene cuentas."""
        persona = Persona.desde_datos(dict(datos, tipo='ADMINISTRATIVO', estado='ACTIVA'))
        nombre = validar_nombre_usuario(nombre)
        clave = generar_clave_temporal()
        with self.repositorio.transaccion() as operacion:
            identificador = operacion.registrar_primera_cuenta_administradora(
                persona, nombre, generate_password_hash(clave, method='scrypt'),
            )
        return CuentaCreada(identificador, nombre, clave)

    def actualizar_cuenta(self, documento: str, datos: dict, actor: int) -> None:
        if 'rol' in datos:
            raise ValueError('Cambia el rol desde la sección Roles y permisos.')
        self._actualizar_cuenta(documento, datos, actor, 'USUARIOS_GESTIONAR')

    def asignar_rol_cuenta(self, documento: str, rol: str, actor: int) -> None:
        self._actualizar_cuenta(documento, dict(rol=rol), actor, 'ROLES_GESTIONAR')

    def _preparar_cambios_cuenta(self, datos: dict) -> dict:
        clave = validar_clave(datos.get('clave', ''), permitir_vacia=True)
        cambios: dict = {}
        if 'nombre_usuario' in datos:
            cambios['nombre_usuario'] = validar_nombre_usuario(datos['nombre_usuario'])
        if clave:
            cambios['contrasena_hash'] = generate_password_hash(clave, method='scrypt')
            cambios['debe_cambiar_clave'] = True
        if 'estado_cuenta' in datos:
            if datos['estado_cuenta'] not in ESTADOS_CUENTA:
                raise ValueError('Estado de cuenta inválido.')
            cambios['estado_cuenta'] = datos['estado_cuenta']
        if 'rol' in datos:
            if datos['rol'] not in ROLES:
                raise ValueError('Rol inexistente.')
            cambios['rol'] = datos['rol']
        return cambios

    def _actualizar_cuenta(self, documento: str, datos: dict, actor: int, permiso: str) -> None:
        documento, actor = dni(documento), entero(actor)
        cambios = self._preparar_cambios_cuenta(datos)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), permiso)
            cuentas = operacion.consultar_cuentas_para_actualizar()
            actual = next((c for c in cuentas if c['dni_persona'] == documento), None)
            if actual is None:
                raise NoEncontrado('Cuenta inexistente.')
            if 'nombre_usuario' in cambios:
                ocupado = operacion.consultar_id_por_nombre_usuario(cambios['nombre_usuario'])
                if ocupado is not None and ocupado != actual['id_usuario']:
                    raise Conflicto('El nombre de usuario ya está registrado.')
            if permiso == 'USUARIOS_GESTIONAR':
                comprobar_version(datos.get('version'), version_cuenta(actual))
            cuenta_actor = next((c for c in cuentas if c['id_usuario'] == actor), None)
            administrador = (
                cuenta_actor is not None
                and cuenta_actor['rol'] == 'ADMINISTRADOR'
                and cuenta_actor['estado_cuenta'] == cuenta_actor['estado_persona'] == 'ACTIVA'
            )
            if (
                actual['rol'] == 'ADMINISTRADOR'
                and actual['id_usuario'] != actor
                and not administrador
            ):
                raise PermissionError(
                    'Solo un administrador puede editar otra cuenta administradora.'
                )
            nueva = dict(actual, **cambios)
            if cambios.get('estado_cuenta') == 'ACTIVA' and actual['estado_persona'] != 'ACTIVA':
                raise ValueError('La persona debe estar activa para habilitar la cuenta.')
            proteger_administradores(cuentas, actual, nueva, actor)
            operacion.actualizar_cuenta(actual['id_usuario'], cambios)

    def buscar_cuentas(self, termino: str = '') -> list[dict]:
        return self.repositorio.buscar_cuentas(termino.strip())
