from dominio.gestion_control.i_repositorio_sancion import IRepositorioSancion
from dominio.gestion_recursos.validacion_recurso import texto
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from servicios.validacion_identificadores import identificador


class ServicioAplicacionSancion:
    def __init__(self, repositorio: IRepositorioSancion):
        self.repositorio: IRepositorioSancion = repositorio

    def aplicar_sanciones_vencidas(self) -> int:
        return self.repositorio.aplicar_sanciones_vencidas()

    def levantar_sancion_vencimiento(self, id_prestamo, id_detalle, justificacion, dni_encargado) -> None:
        self.repositorio.levantar_sancion_vencimiento(
            identificador(id_prestamo), identificador(id_detalle),
            texto(justificacion, 'Justificación para quitar la sanción', 255, True), validar_dni(dni_encargado))
