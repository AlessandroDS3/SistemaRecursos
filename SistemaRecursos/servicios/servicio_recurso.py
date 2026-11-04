from __future__ import annotations
from dominio.gestion_recursos.recurso import Recurso
from dominio.resultados_consulta import ResultadoRecursos
from dominio.gestion_recursos.i_repositorio_bien_material import IRepositorioBienMaterial
from dominio.gestion_recursos.i_repositorio_recurso import IRepositorioRecurso
from dominio.gestion_recursos.fabrica_recurso import FabricaRecurso
from dominio.gestion_recursos.categoria_recurso import CategoriaRecurso
from dominio.gestion_recursos.bien_material import EstadoBienMaterial
from dominio.gestion_recursos.validacion_recurso import texto, ConflictoRecursoError
from servicios.validacion_identificadores import identificador


class ServicioAplicacionRecurso:
    def __init__(self, repositorio_recursos: IRepositorioRecurso, repositorio_bienes: IRepositorioBienMaterial):
        self.repositorio: IRepositorioRecurso = repositorio_recursos
        self.bienes: IRepositorioBienMaterial = repositorio_bienes

    def consultar_administracion_recursos(self, filtros=None):
        valores = self._validar_filtros(filtros)
        recursos = self.repositorio.consultar_recursos(valores)
        return dict(
            recursos=recursos,
            categorias=self.consultar_categorias(),
            filtros=valores,
            estados=EstadoBienMaterial,
        )

    def registrar_recurso(self, datos) -> Recurso:
        datos = dict(datos)
        datos.pop("id_recurso", None)
        recurso = FabricaRecurso.construir(datos)
        self.consultar_categoria(recurso.id_categoria_ref)
        datos_bien = {
            campo: datos.get(campo, "")
            for campo in ("codigo_inventario", "numero_serie", "fecha_adquisicion", "ubicacion", "descripcion_bien")
        }
        if not datos.get("codigo_inventario", "").strip():
            if any(str(datos_bien[k] or "").strip() for k in ("numero_serie", "ubicacion", "descripcion_bien")):
                raise ValueError("Introduce un código para registrar el primer bien físico.")
            return self.repositorio.registrar_recurso(recurso)
        return self.repositorio.registrar_recurso_con_bien(recurso, datos_bien)

    def consultar_recurso(self, id_recurso) -> Recurso:
        recurso = self.repositorio.consultar_recurso(identificador(id_recurso))
        if not recurso:
            raise LookupError("No se encontró el recurso.")
        return recurso

    def actualizar_recurso(self, datos) -> Recurso:
        actual = self.consultar_recurso(datos.get("id_recurso"))
        datos = dict(datos, id_recurso=actual.id_recurso)
        recurso = FabricaRecurso.construir(datos)
        self.consultar_categoria(recurso.id_categoria_ref)
        return self.repositorio.actualizar_recurso(recurso)

    def eliminar_recurso(self, id_recurso) -> None:
        recurso = self.consultar_recurso(id_recurso)
        if self.bienes.existen_por_recurso(recurso.id_recurso):
            raise ConflictoRecursoError("El recurso tiene bienes asociados y debe conservarse.")
        self.repositorio.eliminar_recurso(recurso.id_recurso)

    def consultar_recursos(self, filtros=None) -> ResultadoRecursos:
        valores = self._validar_filtros(filtros)
        return {"recursos": self.repositorio.consultar_recursos(valores)}

    @staticmethod
    def _validar_filtros(filtros):
        filtros = filtros or {}
        valores = {
            "q": texto(filtros.get("q", ""), "Búsqueda", 120),
            "solo_disponibles": filtros.get("solo_disponibles") == "1",
        }
        if filtros.get("id_categoria_ref"):
            valores["id_categoria_ref"] = identificador(filtros["id_categoria_ref"])
        for campo in ('id_recurso', 'id_bien'):
            if filtros.get(campo):
                valores[campo] = identificador(filtros[campo])
        if filtros.get("estado"):
            try:
                valores["estado"] = EstadoBienMaterial(filtros["estado"]).value
            except (ValueError, TypeError):
                raise ValueError("El estado del ejemplar del filtro no es válido.") from None
        return valores

    def opciones_catalogo(self, filtros):
        valores = self._validar_filtros(filtros)
        recursos = []
        bienes = []
        if valores.get('id_categoria_ref'):
            recursos = self.repositorio.consultar_recursos({'id_categoria_ref': valores['id_categoria_ref']})
            if valores.get('id_recurso') and any(r['id_recurso'] == valores['id_recurso'] for r in recursos):
                bienes = self.bienes.consultar_bienes_por_recurso(valores['id_recurso'])
        return {'recursos': recursos, 'bienes': bienes}

    def consultar_disponibilidad_recurso(self, id_recurso):
        recurso = self.consultar_recurso(id_recurso)
        resultado = self.bienes.consultar_bienes_materiales(
            {"id_recurso": recurso.id_recurso}
        )
        return {
            "recurso": recurso,
            "bienes": resultado["bienes"],
            "total": resultado["resumen"]["total"],
            "disponibles": resultado["resumen"]["disponibles"],
        }

    def consultar_categorias(self) -> list[CategoriaRecurso]:
        return self.repositorio.consultar_categorias()

    def consultar_categoria(self, id_categoria) -> CategoriaRecurso:
        categoria = self.repositorio.consultar_categoria(identificador(id_categoria))
        if not categoria:
            raise LookupError("No se encontró la categoría.")
        return categoria

    def registrar_categoria(self, datos) -> CategoriaRecurso:
        categoria = CategoriaRecurso(
            nombre=datos.get("nombre"), descripcion=datos.get("descripcion", "")
        )
        return self.repositorio.registrar_categoria(categoria)

    def actualizar_categoria(self, datos) -> CategoriaRecurso:
        actual = self.consultar_categoria(datos.get("id_categoria"))
        categoria = CategoriaRecurso(
            id_categoria=actual.id_categoria,
            nombre=datos.get("nombre"), descripcion=datos.get("descripcion", ""),
        )
        return self.repositorio.actualizar_categoria(categoria)

    def eliminar_categoria(self, id_categoria) -> None:
        categoria = self.consultar_categoria(id_categoria)
        self.repositorio.eliminar_categoria(categoria.id_categoria)
