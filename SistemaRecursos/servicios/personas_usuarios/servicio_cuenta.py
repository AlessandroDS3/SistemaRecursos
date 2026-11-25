from dominio.compartido.validacion import Conflicto, NoEncontrado, comprobar_version
from werkzeug.security import check_password_hash, generate_password_hash
from dominio.compartido.validacion import dni, entero, texto
from dominio.gestion_personas_usuarios.contratos_personas_usuarios import IRepositorioCuenta
from dominio.gestion_personas_usuarios.cuenta import (
    CuentaCreada,
    ESTADOS_CUENTA,
    activacion_valida,
    base_nombre_usuario,
    generar_activacion,
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
            operacion.cerrar_sesiones_de_cuenta(actor)

    def activar_cuenta(self, usuario, codigo, nueva, confirmacion):
        usuario = validar_nombre_usuario(usuario)
        nueva = validar_clave(nueva)
        if nueva != confirmacion:
            raise ValueError('La nueva contraseña y su confirmación no coinciden.')
        if nueva == codigo:
            raise ValueError('Elige una contraseña diferente del código de activación.')
        with self.repositorio.transaccion() as op:
            identificador = op.consultar_id_por_nombre_usuario(usuario)
            cuenta = op.consultar_cuenta_para_cambiar_clave(identificador) if identificador else None
            if (cuenta is None or cuenta['estado_cuenta'] != 'ACTIVA' or cuenta['estado_persona'] != 'ACTIVA'
                    or not activacion_valida(cuenta['contrasena_hash'], codigo, op.consultar_fecha_actual())):
                raise ValueError('El usuario o el código es incorrecto, venció o ya fue utilizado.')
            op.actualizar_cuenta(identificador, dict(contrasena_hash=generate_password_hash(nueva, method='scrypt'),
                                                   debe_cambiar_clave=False))
            op.cerrar_sesiones_de_cuenta(identificador)
            op.registrar_historial_estado('CUENTA', identificador, 'PENDIENTE', 'ACTIVADA',
                                         cuenta['dni_persona'], 'Contraseña establecida.')

    def restablecer_clave(self, documento, motivo, version_recibida, actor):
        documento, actor = dni(documento), entero(actor)
        motivo = texto(motivo, 'Motivo del restablecimiento', 255, True)
        with self.repositorio.transaccion() as op:
            cuentas = op.consultar_cuentas_para_actualizar()
            administrador = exigir_permiso(op.consultar_cuenta_actor(actor), 'USUARIOS_GESTIONAR')
            cuenta = next((fila for fila in cuentas if fila['dni_persona'] == documento), None)
            if cuenta is None:
                raise NoEncontrado('Cuenta inexistente.')
            if administrador['rol'] != 'ADMINISTRADOR' or cuenta['rol'] == 'ADMINISTRADOR':
                raise PermissionError('El restablecimiento está disponible para cuentas de usuario y encargado.')
            if cuenta['estado_cuenta'] != 'ACTIVA' or cuenta['estado_persona'] != 'ACTIVA':
                raise Conflicto('La cuenta y la persona deben estar activas para restablecer el acceso.')
            comprobar_version(version_recibida, version_cuenta(cuenta))
            identificador = cuenta['id_usuario']
            codigo, huella = generar_activacion(op.consultar_fecha_actual())
            op.actualizar_cuenta(identificador, dict(contrasena_hash=huella, debe_cambiar_clave=True))
            op.cerrar_sesiones_de_cuenta(identificador)
            op.registrar_historial_estado('CUENTA', identificador, None, 'RESTABLECIDA',
                                         administrador['dni_persona'], motivo)
            return CuentaCreada(identificador, cuenta['nombre_usuario'], codigo)

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
            return dict(nombre_usuario='', requiere_nombre=True)
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
            codigo, huella = generar_activacion(operacion.consultar_fecha_actual())
            identificador = operacion.registrar_cuenta(
                documento,
                nombre,
                huella,
            )
            return CuentaCreada(identificador, nombre, codigo)

    def registrar_primer_administrador(self, datos: dict, nombre: str) -> CuentaCreada:
        """Inicialización local de una base que aún no tiene cuentas."""
        persona = Persona.desde_datos(dict(datos, tipo='ADMINISTRATIVO', estado='ACTIVA'))
        nombre = validar_nombre_usuario(nombre)
        with self.repositorio.transaccion() as operacion:
            codigo, huella = generar_activacion(operacion.consultar_fecha_actual())
            identificador = operacion.registrar_primera_cuenta_administradora(
                persona, nombre, huella,
            )
        return CuentaCreada(identificador, nombre, codigo)

    def _preparar_cambios_cuenta(self, datos: dict) -> dict:
        if datos.get('clave') or {'contrasena_hash', 'debe_cambiar_clave'} & datos.keys():
            raise ValueError('Usa el formulario de restablecimiento para cambiar las credenciales.')
        cambios: dict = {}
        if 'nombre_usuario' in datos:
            cambios['nombre_usuario'] = validar_nombre_usuario(datos['nombre_usuario'])
        if 'estado_cuenta' in datos:
            if datos['estado_cuenta'] not in ESTADOS_CUENTA:
                raise ValueError('Estado de cuenta inválido.')
            cambios['estado_cuenta'] = datos['estado_cuenta']
        if 'rol' in datos:
            if datos['rol'] not in ROLES:
                raise ValueError('Rol inexistente.')
            cambios['rol'] = datos['rol']
        return cambios

    def actualizar_cuenta(self, documento: str, datos: dict, actor: int) -> None:
        documento, actor = dni(documento), entero(actor)
        cambios = self._preparar_cambios_cuenta(datos)
        with self.repositorio.transaccion() as operacion:
            cuentas = operacion.consultar_cuentas_para_actualizar()
            cuenta = exigir_permiso(operacion.consultar_cuenta_actor(actor), 'USUARIOS_GESTIONAR')
            if 'rol' in cambios:
                exigir_permiso(cuenta, 'ROLES_GESTIONAR')
            actual = next((c for c in cuentas if c['dni_persona'] == documento), None)
            if actual is None:
                raise NoEncontrado('Cuenta inexistente.')
            if 'nombre_usuario' in cambios:
                ocupado = operacion.consultar_id_por_nombre_usuario(cambios['nombre_usuario'])
                if ocupado is not None and ocupado != actual['id_usuario']:
                    raise Conflicto('El nombre de usuario ya está registrado.')
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
            if actual['rol'] != 'ADMINISTRADOR' and nueva['rol'] == 'ADMINISTRADOR' and actual['debe_cambiar_clave']:
                raise ValueError('La persona debe establecer su contraseña antes de recibir el rol de administrador.')
            if cambios.get('estado_cuenta') == 'ACTIVA' and actual['estado_persona'] != 'ACTIVA':
                raise ValueError('La persona debe estar activa para habilitar la cuenta.')
            proteger_administradores(cuentas, actual, nueva, actor)
            operacion.actualizar_cuenta(actual['id_usuario'], cambios)
            if any(actual[campo] != nueva[campo] for campo in ('rol', 'estado_cuenta')):
                operacion.cerrar_sesiones_de_cuenta(actual['id_usuario'])
