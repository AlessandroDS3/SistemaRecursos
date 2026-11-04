from __future__ import annotations
from dominio.gestion_personas_usuarios.usuario_sistema import UsuarioSistema
from dominio.resultados_consulta import CuentaParaRol
from abc import ABC, abstractmethod


class IRepositorioAcceso(ABC):
    @abstractmethod
    def consultar_cuenta_persona(self, dni) -> UsuarioSistema | None:
        """Lectura sin escrituras. Devuelve UsuarioSistema | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_cuentas(self) -> list[UsuarioSistema]:
        """Lectura sin escrituras. Devuelve list[UsuarioSistema]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_resumen_cuentas(self, dnis_persona) -> dict[str, dict[str, bool]]:
        """Lectura sin escrituras. Devuelve dict[str, dict[str, bool]]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_por_nombre_usuario(self, nombre_usuario) -> UsuarioSistema | None:
        """Lectura sin escrituras. Devuelve UsuarioSistema | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_cuenta_por_id(self, id_usuario) -> UsuarioSistema | None:
        """Lectura sin escrituras. Devuelve UsuarioSistema | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def registrar_cuenta(self, usuario) -> UsuarioSistema:
        """Escritura explícita. Devuelve UsuarioSistema y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_cuenta(
        self,
        id_usuario,
        nombre_usuario=None,
        id_rol=None,
        contrasena_hash=None,
        activar=None,
        id_usuario_actor=None,
    ) -> UsuarioSistema:
        """Escritura explícita. Devuelve UsuarioSistema y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def registrar_acceso(self, id_usuario) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_cuentas_para_roles(self, termino: str, limite: int = 20) -> list[CuentaParaRol]:
        """Busca cuentas por apellidos, DNI o CUI. No devuelve hashes ni contraseñas."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_rol_cuenta(self, id_usuario: int, id_rol: int, id_usuario_actor: int) -> UsuarioSistema:
        """Cambia solo el rol, conservando la protección de la última cuenta administradora."""
        raise NotImplementedError
