from dominio.gestion_recursos.recurso import Recurso


class FabricaRecurso:
    @classmethod
    def construir(cls, datos):
        return Recurso(
            nombre=datos.get("nombre"),
            id_categoria_ref=datos.get("id_categoria_ref"),
            marca=datos.get("marca", ""),
            modelo=datos.get("modelo", ""),
            descripcion=datos.get("descripcion", ""),
            id_recurso=datos.get("id_recurso"),
        )
