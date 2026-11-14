from dominio.compartido.validacion import comprobar_version, version
from dominio.gestion_personas_usuarios.rol import IRepositorioRol, validar_matriz
from dominio.gestion_personas_usuarios.acceso import exigir_permiso


class ServicioAplicacionRol:
    def __init__(self, repositorio: IRepositorioRol):
        self.repositorio = repositorio

    def consultar_matriz_permisos(self):
        matriz = self.repositorio.consultar_matriz_permisos()
        return matriz, version(matriz)

    def guardar_matriz_permisos(self, matriz, version_recibida, actor):
        matriz = {rol: sorted(set(permisos)) for rol, permisos in matriz.items()}
        validar_matriz(matriz)
        with self.repositorio.transaccion() as operacion:
            exigir_permiso(operacion.consultar_cuenta_actor(actor), 'ROLES_GESTIONAR')
            actual = operacion.consultar_matriz_permisos(bloquear=True)
            comprobar_version(version_recibida, version(actual))
            operacion.guardar_matriz_permisos(matriz)
