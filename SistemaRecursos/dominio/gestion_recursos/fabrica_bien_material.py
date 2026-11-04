from dominio.gestion_recursos.bien_material import BienMaterial


class FabricaBienMaterial:
    @classmethod
    def construir(cls, datos):
        return BienMaterial(
            id_recurso_ref=datos.get("id_recurso_ref"),
            codigo_inventario=datos.get("codigo_inventario"),
            fecha_adquisicion=datos.get("fecha_adquisicion"),
            numero_serie=datos.get("numero_serie", ""),
            descripcion_bien=datos.get("descripcion_bien", ""),
            ubicacion=datos.get("ubicacion", ""),
            estado=datos.get("estado", "DISPONIBLE"),
            id_bien=datos.get("id_bien"),
        )
