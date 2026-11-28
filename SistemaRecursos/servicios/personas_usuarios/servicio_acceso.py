import logging
from secrets import token_urlsafe
import unicodedata

from werkzeug.security import check_password_hash, generate_password_hash
from dominio.compartido.validacion import validar_entero
from dominio.gestion_personas_usuarios.contratos_personas_usuarios import IRepositorioAcceso
from dominio.gestion_personas_usuarios.cuenta import PREFIJO_ACTIVACION
from dominio.gestion_personas_usuarios.sesion import (
    INTERVALO_ACTIVIDAD,
    AccesoBloqueado,
    LimitadorIntentos,
    calcular_huella_del_token_de_sesion,
    sesion_vigente,
)

registro = logging.getLogger(__name__)


class ServicioAplicacionAcceso:
    def __init__(self, repositorio: IRepositorioAcceso, limitador_usuario=None, limitador_origen=None):
        self.repositorio = repositorio
        # Hash de una clave aleatoria: iguala el tiempo de respuesta cuando la cuenta no existe.
        self._hash_ausente = generate_password_hash(token_urlsafe(32), method='scrypt')
        # Un laboratorio comparte IP: el límite por origen es más alto que por cuenta.
        self.limitador_usuario = limitador_usuario or LimitadorIntentos(maximo=5)
        self.limitador_origen = limitador_origen or LimitadorIntentos(maximo=20)

    def autenticar_cuenta(self, nombre, clave, origen=''):
        """Devuelve una CuentaAcceso activa si la contraseña coincide; en otro caso, None.

        Lanza AccesoBloqueado si el usuario o el origen superaron el límite de intentos.
        """
        if (
            not isinstance(nombre, str)
            or not isinstance(clave, str)
            or len(nombre) > 50
            or len(clave) > 256
        ):
            return None
        clave_usuario = ('usuario', ''.join(c for c in unicodedata.normalize('NFKD', nombre.strip().casefold())
                                            if not unicodedata.combining(c)))
        clave_origen = ('origen', origen or 'desconocido')
        minutos = max(
            self.limitador_usuario.calcular_minutos_de_bloqueo_restantes(clave_usuario),
            self.limitador_origen.calcular_minutos_de_bloqueo_restantes(clave_origen),
        )
        if minutos:
            raise AccesoBloqueado(minutos)
        cuenta_acceso = self.repositorio.consultar_cuenta_por_usuario(nombre.strip())
        activada = cuenta_acceso and not cuenta_acceso.contrasena_hash.startswith(PREFIJO_ACTIVACION)
        hash_a_comprobar = cuenta_acceso.contrasena_hash if activada else self._hash_ausente
        try:
            correcta = check_password_hash(hash_a_comprobar, clave)
        except (ValueError, TypeError):
            correcta = False
        if not activada or not correcta or not cuenta_acceso.puede_acceder():
            self.limitador_usuario.registrar_intento_de_acceso_fallido(clave_usuario)
            self.limitador_origen.registrar_intento_de_acceso_fallido(clave_origen)
            # Se registra el intento sin la contraseña.
            registro.warning('Acceso fallido desde %s', clave_origen[1])
            return None
        self.limitador_usuario.borrar_intentos_y_bloqueo(clave_usuario)
        self.repositorio.registrar_ultimo_inicio_de_sesion(cuenta_acceso.id_usuario)
        return cuenta_acceso

    def consultar_cuenta_activa(self, identificador):
        """Recupera una CuentaAcceso activa, o None si el identificador o el estado no sirven."""
        try:
            cuenta_acceso = self.repositorio.consultar_cuenta_por_id(validar_entero(identificador))
        except ValueError:
            return None
        if cuenta_acceso is None or not cuenta_acceso.puede_acceder():
            return None
        return cuenta_acceso

    def crear_sesion_de_cuenta(self, id_usuario) -> str:
        """Registra una sesión en el servidor y devuelve el token que irá en la cookie."""
        token = token_urlsafe(32)
        self.repositorio.crear_sesion(calcular_huella_del_token_de_sesion(token), validar_entero(id_usuario))
        return token

    def validar_sesion(self, token, id_usuario) -> bool:
        """La sesión existe, pertenece a la cuenta, no se cerró ni venció."""
        if not isinstance(token, str) or not token:
            return False
        try:
            id_usuario = validar_entero(id_usuario)
        except ValueError:
            return False
        huella = calcular_huella_del_token_de_sesion(token)
        fila = self.repositorio.consultar_sesion(huella)
        ahora = self.repositorio.consultar_fecha_actual()
        if not sesion_vigente(fila, id_usuario, ahora):
            if fila and fila['fecha_cierre'] is None:
                self.repositorio.cerrar_sesion(huella)
            return False
        if ahora - fila['ultima_actividad'] >= INTERVALO_ACTIVIDAD:
            self.repositorio.registrar_actividad_sesion(huella)
        return True

    def cerrar_sesion(self, token) -> None:
        if isinstance(token, str) and token:
            self.repositorio.cerrar_sesion(calcular_huella_del_token_de_sesion(token))
