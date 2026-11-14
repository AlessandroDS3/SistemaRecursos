from __future__ import annotations
from dominio.cuentas import (
    CuentaParaRol,
    IRepositorioCuenta,
    IRepositorioRol,
    Permiso,
    Rol,
    UsuarioSistema,
    validar_permisos_administrador,
)
from dominio.personas import validar_dni
from dominio.validaciones import entero as identificador


class ServicioAplicacionRol:
    def __init__(self, repositorio_roles: IRepositorioRol, repositorio_cuentas: IRepositorioCuenta):
        self.repositorio: IRepositorioRol = repositorio_roles
        self.cuentas: IRepositorioCuenta = repositorio_cuentas

    def consultar_roles(self) -> list[Rol]:
        return self.repositorio.consultar_roles()

    def consultar_permisos(self) -> list[Permiso]:
        return self.repositorio.consultar_permisos()

    @staticmethod
    def _construir_matriz(formulario, roles, permisos):
        permisos_validos = set()
        for permiso in permisos:
            permisos_validos.add(permiso.codigo)
        matriz = {}
        for rol in roles:
            seleccionados = set()
            for valor in formulario.get(f"permisos_{rol.nombre.value}", []):
                seleccionados.add(valor)
            for codigo_permiso in seleccionados:
                if codigo_permiso not in permisos_validos:
                    raise LookupError("Uno de los permisos seleccionados no existe.")
            matriz[rol.nombre.value] = sorted(seleccionados)
        return matriz

    def actualizar_matriz_permisos(self, formulario) -> None:
        roles = self.consultar_roles()
        permisos = self.consultar_permisos()
        matriz = self._construir_matriz(formulario, roles, permisos)
        validar_permisos_administrador(roles, permisos, matriz)
        self.repositorio.actualizar_matriz_permisos(matriz, version=formulario.get("version"))

    def consultar_cuentas_para_roles(self, termino: str) -> list[CuentaParaRol]:
        termino = termino.strip()
        if len(termino) > 120:
            raise ValueError("La búsqueda admite hasta 120 caracteres.")
        if len(termino) < 2:
            return []
        return self.cuentas.consultar_cuentas_para_roles(termino, limite=20)

    def actualizar_rol_cuenta(self, dni: str, nombre_rol, id_usuario_actor: int) -> UsuarioSistema:
        cuenta = self.cuentas.consultar_cuenta_persona(validar_dni(dni))
        if not cuenta:
            raise LookupError("Esta persona todavía no tiene una cuenta de acceso.")
        rol = self.repositorio.consultar_rol(nombre_rol)
        if not rol:
            raise ValueError("Selecciona un rol válido.")
        return self.cuentas.actualizar_rol_cuenta(cuenta.id_usuario, rol.nombre.value, identificador(id_usuario_actor))
