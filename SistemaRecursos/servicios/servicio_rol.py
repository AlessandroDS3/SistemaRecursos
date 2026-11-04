from __future__ import annotations
from dominio.gestion_personas_usuarios.permiso import Permiso
from dominio.gestion_personas_usuarios.rol import Rol
from dominio.gestion_personas_usuarios.i_repositorio_rol import IRepositorioRol
from servicios.validacion_identificadores import identificador
from dominio.gestion_personas_usuarios.i_repositorio_acceso import IRepositorioAcceso
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.resultados_consulta import CuentaParaRol
from dominio.gestion_personas_usuarios.usuario_sistema import UsuarioSistema
from dominio.gestion_personas_usuarios.rol import validar_permisos_administrador


class ServicioAplicacionRol:
    def __init__(self, repositorio_roles: IRepositorioRol, repositorio_cuentas: IRepositorioAcceso):
        self.repositorio: IRepositorioRol = repositorio_roles
        self.cuentas: IRepositorioAcceso = repositorio_cuentas

    def consultar_roles(self) -> list[Rol]:
        return self.repositorio.consultar_roles()

    def consultar_permisos(self) -> list[Permiso]:
        return self.repositorio.consultar_permisos()

    @staticmethod
    def _construir_matriz(formulario, roles, permisos):
        permisos_validos = set()
        for permiso in permisos:
            permisos_validos.add(permiso.id_permiso)
        matriz = {}
        for rol in roles:
            if not rol.activo:
                continue
            seleccionados = set()
            for valor in formulario.getlist(f"permisos_{rol.id_rol}"):
                seleccionados.add(identificador(valor))
            for id_permiso in seleccionados:
                if id_permiso not in permisos_validos:
                    raise LookupError("Uno de los permisos seleccionados no existe.")
            matriz[rol.id_rol] = sorted(seleccionados)
        return matriz

    def actualizar_matriz_permisos(self, formulario) -> None:
        roles = self.consultar_roles()
        permisos = self.consultar_permisos()
        matriz = self._construir_matriz(formulario, roles, permisos)
        validar_permisos_administrador(roles, permisos, matriz)
        self.repositorio.actualizar_matriz_permisos(matriz)

    def consultar_cuentas_para_roles(self, termino: str) -> list[CuentaParaRol]:
        termino = termino.strip()
        if len(termino) > 120:
            raise ValueError("La búsqueda admite hasta 120 caracteres.")
        if len(termino) < 2:
            return []
        return self.cuentas.consultar_cuentas_para_roles(termino, limite=20)

    def actualizar_rol_cuenta(self, dni: str, id_rol, id_usuario_actor: int) -> UsuarioSistema:
        cuenta = self.cuentas.consultar_cuenta_persona(validar_dni(dni))
        if not cuenta:
            raise LookupError("Esta persona todavía no tiene una cuenta de acceso.")
        rol = self.repositorio.consultar_rol(identificador(id_rol))
        if not rol or not rol.activo:
            raise ValueError("Selecciona un rol activo.")
        return self.cuentas.actualizar_rol_cuenta(cuenta.id_usuario, rol.id_rol, identificador(id_usuario_actor))
