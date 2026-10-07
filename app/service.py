"""Casos de uso de esta primera entrega."""
from .domain import Recurso, BienMaterial, ValidationError
from .errors import ConflictError


class GestionRecursosService:
    def __init__(self, repository):
        self.repository = repository

    def registrar(self, data):
        recurso = Recurso.desde_datos(data.get("recurso"))
        bien = BienMaterial.desde_datos(data.get("bien"))
        if recurso.idCategoriaRef not in [c["idCategoria"] for c in self.repository.categorias()]:
            raise ValidationError("La categoría no existe.")
        return self.repository.crear(recurso, bien)

    def agregar_bien(self, recurso_id, data):
        bien = BienMaterial.desde_datos(data)
        return self.repository.agregar_bien(recurso_id, bien)
