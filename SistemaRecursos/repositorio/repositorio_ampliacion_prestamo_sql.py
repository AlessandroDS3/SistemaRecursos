from dominio.compartido.validacion import NoEncontrado
from dominio.compartido.validacion import Conflicto
from repositorio.base_sql import RepositorioSQL


class RepositorioAmpliacionPrestamoSQL(RepositorioSQL):
    def cargar(self, prestamo, detalle):
        cabecera = self.consultar_sql(
            'SELECT * FROM prestamo WHERE id_prestamo=%s FOR UPDATE', (prestamo,), una=True
        )
        if cabecera is None:
            raise NoEncontrado('Préstamo inexistente.')
        fila = self.consultar_sql(
            '''SELECT d.*,b.estado AS estado_bien FROM detalle_prestamo d
            JOIN bien_material b ON b.id_bien=d.id_bien WHERE d.id_prestamo=%s AND d.id_detalle=%s FOR UPDATE''',
            (prestamo, detalle),
            una=True,
        )
        if fila is None:
            raise NoEncontrado('El detalle no pertenece a este préstamo.')
        politica = self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE id_politica=%s FOR UPDATE',
            (fila['id_politica'],),
            una=True,
        )
        horario = self.consultar_sql(
            'SELECT hora_apertura,hora_cierre FROM configuracion_general WHERE id_configuracion=1 FOR UPDATE',
            una=True,
        )
        return cabecera, fila, politica, horario

    def guardar(self, detalle, anterior, nueva):
        self.ejecutar(
            '''UPDATE detalle_prestamo SET fecha_limite_devolucion=%s
            WHERE id_detalle=%s AND fecha_limite_devolucion=%s AND fecha_devolucion IS NULL''',
            (nueva, detalle, anterior),
        )
        if self._cursor.rowcount != 1:
            raise Conflicto('El plazo cambió. Recarga el préstamo.')
