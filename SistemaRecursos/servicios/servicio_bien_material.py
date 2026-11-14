from __future__ import annotations
from dominio.gestion_personas_usuarios.personas import validar_dni
from dominio.gestion_recursos.recursos import (
    BienMaterial,
    ConflictoRecursoError,
    ESTADOS_CAMBIO_MANUAL,
    ESTADOS_GESTION_PRESTAMOS,
    EstadoBienMaterial,
    IRepositorioBienMaterial,
    IRepositorioRecurso,
    ResultadoBienes,
    crear_bien_material,
)
from dominio.compartido.validaciones import entero as identificador, texto


class ServicioAplicacionBienMaterial:
    def __init__(self, repositorio_bienes: IRepositorioBienMaterial, repositorio_recursos: IRepositorioRecurso):
        self.repositorio: IRepositorioBienMaterial = repositorio_bienes
        self.recursos: IRepositorioRecurso = repositorio_recursos

    def registrar_bien_material(self, datos) -> BienMaterial:
        datos = dict(datos, estado="DISPONIBLE")
        datos.pop("id_bien", None)
        bien = crear_bien_material(datos)
        if not self.recursos.consultar_recurso(bien.id_recurso):
            raise LookupError("No se encontró el recurso.")
        return self.repositorio.registrar_bien_material(bien)

    def consultar_bien_material(self, id_bien) -> BienMaterial:
        bien = self.repositorio.consultar_bien_material(identificador(id_bien))
        if not bien:
            raise LookupError("No se encontró el bien.")
        return bien

    def consultar_bienes_materiales(self, filtros=None) -> ResultadoBienes:
        filtros = filtros or {}
        valores = {"q": texto(filtros.get("q", ""), "Búsqueda", 120)}
        if filtros.get("estado"):
            try:
                valores["estado"] = EstadoBienMaterial(filtros["estado"]).value
            except (ValueError, TypeError):
                raise ValueError("Selecciona un estado válido.") from None
        if filtros.get("id_recurso"):
            valores["id_recurso"] = identificador(filtros["id_recurso"])
        return self.repositorio.consultar_bienes_materiales(valores)

    def contar_disponibles(self) -> int:
        return self.repositorio.contar_disponibles()

    def actualizar_bien_material(self, datos) -> BienMaterial:
        actual = self.consultar_bien_material(datos.get("id_bien"))
        datos = dict(
            datos,
            id_bien=actual.id_bien,
            id_recurso=actual.id_recurso,
            estado=actual.estado.value,
        )
        return self.repositorio.actualizar_bien_material(crear_bien_material(datos))

    def eliminar_bien_material(self, id_bien) -> None:
        self.repositorio.eliminar_bien_material(self.consultar_bien_material(id_bien).id_bien)


    def cambiar_estado_bien_material(self, datos, dni_responsable) -> BienMaterial:
        bien = self.consultar_bien_material(datos.get("id_bien"))
        estado = datos.get("estado")
        if estado not in ESTADOS_CAMBIO_MANUAL or bien.estado in ESTADOS_GESTION_PRESTAMOS:
            raise ConflictoRecursoError(
                "No se puede alterar manualmente un préstamo o una reserva."
            )
        esperado = datos.get("estado_esperado")
        if esperado != bien.estado.value:
            raise ConflictoRecursoError(
                "El estado cambió. Recarga el bien antes de intentarlo otra vez."
            )
        motivo = texto(datos.get("motivo"), "Motivo", 255, True)
        # Validación del dominio antes de persistir; el repositorio vuelve a comprobar
        # la versión del estado bajo bloqueo para evitar cambios concurrentes.
        bien.cambiar_estado(estado)
        return self.repositorio.cambiar_estado_bien_material(
            bien.id_bien,
            estado,
            motivo,
            validar_dni(dni_responsable),
            esperado,
        )

    def consultar_detalle_bien_material(self, id_bien):
        bien = self.consultar_bien_material(id_bien)
        return {
            "bien": bien,
            "historial": self.repositorio.consultar_historial_bien_material(bien.id_bien),
            "prestamo_pendiente": self.repositorio.consultar_prestamo_pendiente(bien.id_bien),
        }
