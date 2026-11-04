from dominio.gestion_control.politica_prestamo import PoliticaPrestamo


class FabricaPoliticaPrestamo:
    @staticmethod
    def _entero(valor, mensaje):
        texto = str(valor).strip()
        if not texto.isascii() or not texto.isdecimal():
            raise ValueError(mensaje)
        return int(texto)

    @classmethod
    def construir(cls, datos):
        plazo = cls._entero(
            datos.get("plazo_maximo"), "El plazo máximo debe ser un número entero."
        )
        salida = datos.get("permite_salida", False)
        if salida not in (True, False, 0, 1, "0", "1"):
            raise ValueError("El permiso de salida no es válido.")

        return PoliticaPrestamo(
            tipo_persona=datos.get("tipo_persona"),
            id_categoria_ref=datos.get("id_categoria_ref"),
            plazo_maximo=plazo,
            unidad_plazo=datos.get("unidad_plazo"),
            permite_salida=salida in (True, 1, "1"),
            id_politica=datos.get("id_politica"),
        )
