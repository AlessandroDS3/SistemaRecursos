from dataclasses import asdict
from mysql.connector import IntegrityError, errorcode

from dominio.compartido.validacion import Conflicto
from repositorio.base_datos.base_sql import RepositorioSQL


class RepositorioPoliticaPrestamoSQL(RepositorioSQL):
    def consultar_politicas_prestamo(self):
        return self.consultar_sql('''SELECT p.*,c.nombre AS categoria FROM politica_prestamo p
            JOIN categoria_recurso c ON c.id_categoria=p.id_categoria
            WHERE p.vigente=TRUE ORDER BY p.tipo_persona,c.nombre''')

    def consultar_politica_prestamo(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE id_politica=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def consultar_horario_y_plazos_de_reserva(self, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM configuracion_general WHERE id_configuracion=1'
            + (' FOR UPDATE' if bloquear else ''),
            una=True,
        )

    def consultar_limites_articulos(self):
        return self.consultar_sql('SELECT * FROM limite_articulos_prestamo ORDER BY tipo_persona')

    def insertar_politica_prestamo(self, politica):
        datos = asdict(politica)
        datos.pop('id_politica')
        return self.insertar_fila_sql('politica_prestamo', datos)

    def desactivar_politica_prestamo(self, identificador):
        self.ejecutar_escritura_sql(
            'UPDATE politica_prestamo SET vigente=FALSE WHERE id_politica=%s', (identificador,)
        )

    def eliminar_politica_prestamo(self, identificador):
        try:
            self.ejecutar_escritura_sql('DELETE FROM politica_prestamo WHERE id_politica=%s', (identificador,))
        except IntegrityError as error:
            if error.errno == errorcode.ER_ROW_IS_REFERENCED_2:
                raise Conflicto(
                    'La política tiene préstamos asociados y se conserva para su historial.'
                ) from None
            raise

    def guardar_horario_y_plazos_de_reserva(self, datos):
        columnas = ','.join(k + '=%s' for k in datos)
        if self.consultar_horario_y_plazos_de_reserva(bloquear=True) is None:
            self.insertar_fila_sql('configuracion_general', dict(id_configuracion=1, **datos))
        else:
            self.ejecutar_escritura_sql(
                'UPDATE configuracion_general SET ' + columnas + ' WHERE id_configuracion=1',
                tuple(datos.values()),
            )

    def guardar_limite_articulos(self, tipo, cantidad):
        self.ejecutar_escritura_sql(
            '''INSERT INTO limite_articulos_prestamo(tipo_persona,maximo_articulos) VALUES(%s,%s)
            ON DUPLICATE KEY UPDATE maximo_articulos=%s''',
            (tipo, cantidad, cantidad),
        )
