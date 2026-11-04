from __future__ import annotations
from dominio.gestion_control.politica_prestamo import PoliticaPrestamo
from dominio.gestion_recursos.i_repositorio_recurso import IRepositorioRecurso
from dominio.gestion_control.i_repositorio_politica_prestamo import IRepositorioPoliticaPrestamo
from dominio.gestion_control.fabrica_politica_prestamo import FabricaPoliticaPrestamo
from servicios.validacion_identificadores import identificador
from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_control.politica_vencimiento_reserva import PoliticaVencimientoReserva


class ServicioAplicacionPoliticaPrestamo:
    def __init__(self, repositorio_politicas: IRepositorioPoliticaPrestamo, repositorio_recursos: IRepositorioRecurso):
        self.repositorio: IRepositorioPoliticaPrestamo = repositorio_politicas
        self.recursos: IRepositorioRecurso = repositorio_recursos

    def registrar_politica(self, datos) -> PoliticaPrestamo:
        datos = dict(datos)
        datos.pop("id_politica", None)
        politica = FabricaPoliticaPrestamo.construir(datos)
        self._validar_categoria(politica.id_categoria_ref)
        return self.repositorio.registrar_politica(politica)

    def _validar_categoria(self, id_categoria):
        if not self.recursos.consultar_categoria(id_categoria):
            raise ValueError("Selecciona una categoría existente.")

    def consultar_categorias(self):
        return self.recursos.consultar_categorias()

    def consultar_horario_atencion(self) -> HorarioAtencion:
        return self.repositorio.consultar_horario_atencion()

    def actualizar_horario_atencion(self, datos) -> HorarioAtencion:
        horario = HorarioAtencion(hora_apertura=datos.get('hora_apertura'), hora_cierre=datos.get('hora_cierre'))
        return self.repositorio.actualizar_horario_atencion(horario)

    def consultar_politica_vencimiento_reserva(self) -> PoliticaVencimientoReserva:
        return self.repositorio.consultar_politica_vencimiento_reserva()

    def actualizar_politica_vencimiento_reserva(self, datos) -> PoliticaVencimientoReserva:
        politica = PoliticaVencimientoReserva(
            plazo_espera=datos.get("plazo_espera"), unidad_espera=datos.get("unidad_espera"),
            plazo_retiro=datos.get("plazo_retiro"), unidad_retiro=datos.get("unidad_retiro"),
        )
        return self.repositorio.actualizar_politica_vencimiento_reserva(politica)

    def consultar_politica(self, id_politica) -> PoliticaPrestamo:
        politica = self.repositorio.consultar_politica(identificador(id_politica))
        if not politica:
            raise LookupError("No se encontró la política de préstamo.")
        return politica

    def consultar_politicas(self) -> list[PoliticaPrestamo]:
        return self.repositorio.consultar_politicas()

    def actualizar_politica(self, datos) -> PoliticaPrestamo:
        actual = self.consultar_politica(datos.get("id_politica"))
        cambios = dict(datos)
        cambios.update(
            id_politica=actual.id_politica,
            tipo_persona=actual.tipo_persona.value,
            id_categoria_ref=actual.id_categoria_ref,
        )
        return self.repositorio.actualizar_politica(FabricaPoliticaPrestamo.construir(cambios))

    def eliminar_politica(self, id_politica) -> None:
        self.repositorio.eliminar_politica(self.consultar_politica(id_politica).id_politica)

    def validar_prestamo(self, tipo_persona, id_categoria_ref, salida=False):
        politica = self.repositorio.consultar_politica_aplicable(tipo_persona, id_categoria_ref)
        if not politica:
            raise ValueError(
                f"No existe una política para {tipo_persona} en esta categoría. El administrador debe registrarla antes de la entrega."
            )
        if salida and not politica.permite_salida:
            raise ValueError(
                f"La política de esta categoría para {tipo_persona} no permite salida de la institución."
            )
        return politica
