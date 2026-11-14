from dominio.gestion_personas_usuarios.rol import ROLES
from repositorio.base_sql import RepositorioSQL


class RepositorioRolSQL(RepositorioSQL):
    def consultar_matriz(self, bloquear=False):
        filas = self.consultar_sql(
            'SELECT rol,permiso FROM rol_permiso ORDER BY rol,permiso'
            + (' FOR UPDATE' if bloquear else '')
        )
        return {rol: sorted(f['permiso'] for f in filas if f['rol'] == rol) for rol in ROLES}

    def guardar_matriz(self, matriz):
        self.ejecutar('DELETE FROM rol_permiso')
        for rol, permisos in matriz.items():
            for permiso in sorted(set(permisos)):
                self.insertar('rol_permiso', dict(rol=rol, permiso=permiso))
