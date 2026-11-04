from __future__ import annotations
from dominio.gestion_control.politica_prestamo import PoliticaPrestamo
from dominio.gestion_control.i_repositorio_politica_prestamo import IRepositorioPoliticaPrestamo
from dominio.gestion_control.fabrica_politica_prestamo import FabricaPoliticaPrestamo
from dominio.gestion_prestamos.validacion_prestamo import ConflictoPrestamoError
from repositorio.conexion_mysql import MySQLConnection
from repositorio.horario_atencion_sql import consultar_horario_atencion
from dominio.gestion_control.horario_atencion import HorarioAtencion
from dominio.gestion_control.politica_vencimiento_reserva import PoliticaVencimientoReserva
from repositorio.politica_vencimiento_reserva_sql import consultar_politica_vencimiento_reserva


class RepositorioPoliticaPrestamoSQL(IRepositorioPoliticaPrestamo):
    def __init__(self, conexion=None):
        self.conexion = conexion or MySQLConnection()

    def registrar_politica(self, politica) -> PoliticaPrestamo:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "INSERT INTO politica_prestamo (tipo_persona,id_categoria_ref,plazo_maximo,unidad_plazo,permite_salida) VALUES (%s,%s,%s,%s,%s)",
                (
                    politica.tipo_persona.value,
                    politica.id_categoria_ref,
                    politica.plazo_maximo,
                    politica.unidad_plazo,
                    politica.permite_salida,
                ),
            )
            nuevo_id = cursor.lastrowid
        politica.id_politica = nuevo_id
        return politica

    def consultar_politica(self, id_politica) -> PoliticaPrestamo | None:
        with self.conexion.sesion() as cursor:
            cursor.execute("SELECT * FROM politica_prestamo WHERE id_politica=%s AND vigente=TRUE", (id_politica,))
            fila = cursor.fetchone()
            return FabricaPoliticaPrestamo.construir(fila) if fila else None

    def consultar_politica_aplicable(self, tipo_persona, id_categoria_ref) -> PoliticaPrestamo | None:
        with self.conexion.sesion() as cursor:
            cursor.execute(
                "SELECT * FROM politica_prestamo WHERE tipo_persona=%s AND id_categoria_ref=%s AND vigente=TRUE",
                (tipo_persona, id_categoria_ref),
            )
            fila = cursor.fetchone()
            return FabricaPoliticaPrestamo.construir(fila) if fila else None

    def consultar_politicas(self) -> list[PoliticaPrestamo]:
        with self.conexion.sesion() as cursor:
            cursor.execute("SELECT * FROM politica_prestamo WHERE vigente=TRUE ORDER BY tipo_persona,id_categoria_ref")
            return [FabricaPoliticaPrestamo.construir(fila) for fila in cursor.fetchall()]

    def actualizar_politica(self, politica) -> PoliticaPrestamo:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute(
                "SELECT * FROM politica_prestamo WHERE id_politica=%s AND vigente=TRUE FOR UPDATE",
                (politica.id_politica,),
            )
            anterior = cursor.fetchone()
            if not anterior:
                raise LookupError("No se encontró la política.")
            if (
                anterior["tipo_persona"] != politica.tipo_persona.value
                or anterior["id_categoria_ref"] != politica.id_categoria_ref
            ):
                cursor.execute(
                    "SELECT id_detalle FROM detalle_prestamo WHERE id_politica_ref=%s LIMIT 1",
                    (politica.id_politica,),
                )
                if cursor.fetchone():
                    raise ConflictoPrestamoError(
                        "Esta política ya se utilizó. Puedes cambiar su plazo y permiso de salida para nuevos préstamos, pero debes conservar el tipo de persona y la categoría asociados."
                    )
            cursor.execute(
                "UPDATE politica_prestamo SET tipo_persona=%s,id_categoria_ref=%s,plazo_maximo=%s,unidad_plazo=%s,permite_salida=%s WHERE id_politica=%s AND vigente=TRUE",
                (
                    politica.tipo_persona.value,
                    politica.id_categoria_ref,
                    politica.plazo_maximo,
                    politica.unidad_plazo,
                    politica.permite_salida,
                    politica.id_politica,
                ),
            )
        return politica

    def eliminar_politica(self, id_politica) -> None:
        with self.conexion.sesion(escritura=True) as cursor:
            cursor.execute("DELETE FROM politica_prestamo WHERE id_politica=%s AND vigente=TRUE", (id_politica,))

    def consultar_horario_atencion(self) -> HorarioAtencion:
        with self.conexion.sesion() as cursor:
            return consultar_horario_atencion(cursor)

    def actualizar_horario_atencion(self, horario: HorarioAtencion) -> HorarioAtencion:
        with self.conexion.sesion(escritura=True) as cursor:
            consultar_horario_atencion(cursor, bloquear=True)
            cursor.execute('UPDATE horario_atencion SET hora_apertura=%s,hora_cierre=%s WHERE id_horario=1',
                (horario.apertura_texto, horario.cierre_texto))
        return horario

    def consultar_politica_vencimiento_reserva(self) -> PoliticaVencimientoReserva:
        with self.conexion.sesion() as cursor:
            return consultar_politica_vencimiento_reserva(cursor)

    def actualizar_politica_vencimiento_reserva(self, politica: PoliticaVencimientoReserva) -> PoliticaVencimientoReserva:
        with self.conexion.sesion(escritura=True) as cursor:
            consultar_politica_vencimiento_reserva(cursor, bloquear=True)
            cursor.execute(
                "UPDATE politica_vencimiento_reserva SET plazo_espera=%s,unidad_espera=%s,"
                "plazo_retiro=%s,unidad_retiro=%s WHERE id_politica=1",
                (politica.plazo_espera, politica.unidad_espera, politica.plazo_retiro, politica.unidad_retiro),
            )
        return politica
