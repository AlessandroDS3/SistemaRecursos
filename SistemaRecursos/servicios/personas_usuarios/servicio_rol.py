from dominio.gestion_personas_usuarios.rol import ROLES, permisos_del_rol


class ServicioAplicacionRol:
    def consultar_matriz_permisos(self):
        return {rol: permisos_del_rol(rol) for rol in ROLES}
