from dominio.compartido.validacion import NoEncontrado
from werkzeug.security import generate_password_hash
from dominio.compartido.validacion import dni, entero
from dominio.gestion_personas_usuarios.cuenta import (
    IRepositorioCuenta,
    proteger_administradores,
    validar_credenciales_nuevas,
)
from dominio.gestion_personas_usuarios.rol import ROLES
from dominio.gestion_personas_usuarios.acceso import exigir_permiso


class ServicioAplicacionCuenta:
    def __init__(self, repositorio: IRepositorioCuenta):
        self.repositorio = repositorio

    def consultar(self, documento):
        cuenta = self.repositorio.consultar(dni(documento))
        if cuenta is None:
            raise NoEncontrado('La persona no tiene una cuenta de acceso.')
        return cuenta

    def crear(self, documento, nombre, clave, actor):
        documento = dni(documento)
        nombre = validar_credenciales_nuevas(nombre, clave)
        hash_clave = generate_password_hash(clave, method='scrypt')
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(entero(actor)), 'USUARIOS_GESTIONAR')
            if operacion.estado_persona(documento) != 'ACTIVA':
                raise ValueError('La persona debe estar activa para crear su cuenta.')
            return operacion.guardar(documento, nombre, hash_clave)

    def actualizar(self, documento, datos, actor):
        if 'rol' in datos:
            raise ValueError('Cambia el rol desde la sección Roles y permisos.')
        return self._actualizar(documento, datos, actor, 'USUARIOS_GESTIONAR')

    def asignar_rol(self, documento, rol, actor):
        return self._actualizar(documento, dict(rol=rol), actor, 'ROLES_GESTIONAR')

    def _actualizar(self, documento, datos, actor, permiso):
        documento, actor = dni(documento), entero(actor)
        cambios = {}
        if 'nombre_usuario' in datos:
            cambios['nombre_usuario'] = validar_credenciales_nuevas(
                datos['nombre_usuario'], datos.get('clave', ''), True
            )
        if datos.get('clave'):
            cambios['contrasena_hash'] = generate_password_hash(datos['clave'], method='scrypt')
        if 'estado_cuenta' in datos:
            if datos['estado_cuenta'] not in ('ACTIVA', 'INACTIVA', 'BLOQUEADA'):
                raise ValueError('Estado de cuenta inválido.')
            cambios['estado_cuenta'] = datos['estado_cuenta']
        if 'rol' in datos:
            if datos['rol'] not in ROLES:
                raise ValueError('Rol inexistente.')
            cambios['rol'] = datos['rol']
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.cuenta_actor(actor), permiso)
            cuentas = operacion.cargar_cuentas()
            actual = next((c for c in cuentas if c['dni_persona'] == documento), None)
            if actual is None:
                raise NoEncontrado('Cuenta inexistente.')
            cuenta_actor = next((c for c in cuentas if c['id_usuario'] == actor), None)
            administrador = (
                cuenta_actor
                and cuenta_actor['rol'] == 'ADMINISTRADOR'
                and (cuenta_actor['estado_cuenta'] == cuenta_actor['estado_persona'] == 'ACTIVA')
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
            operacion.actualizar(actual['id_usuario'], cambios)

    def buscar(self, termino=''):
        return self.repositorio.buscar(termino.strip())
