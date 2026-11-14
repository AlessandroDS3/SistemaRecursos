from dataclasses import asdict
from repositorio.base_sql import RepositorioSQL


class RepositorioPoliticaPrestamoSQL(RepositorioSQL):
    def listar(self):
        return self.consultar_sql('''SELECT p.*,c.nombre AS categoria FROM politica_prestamo p
            JOIN categoria_recurso c ON c.id_categoria=p.id_categoria
            WHERE p.vigente=TRUE ORDER BY p.tipo_persona,c.nombre''')

    def consultar(self, identificador, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM politica_prestamo WHERE id_politica=%s'
            + (' FOR UPDATE' if bloquear else ''),
            (identificador,),
            una=True,
        )

    def configuracion(self, bloquear=False):
        return self.consultar_sql(
            'SELECT * FROM configuracion_general WHERE id_configuracion=1'
            + (' FOR UPDATE' if bloquear else ''),
            una=True,
        )

    def limites(self):
        return self.consultar_sql('SELECT * FROM limite_articulos_prestamo ORDER BY tipo_persona')

    def guardar(self, politica):
        datos = asdict(politica)
        datos.pop('id_politica')
        return self.insertar('politica_prestamo', datos)

    def desactivar(self, identificador):
        self.ejecutar(
            'UPDATE politica_prestamo SET vigente=FALSE WHERE id_politica=%s', (identificador,)
        )

    def eliminar(self, identificador):
        self.ejecutar('DELETE FROM politica_prestamo WHERE id_politica=%s', (identificador,))

    def guardar_configuracion(self, datos):
        columnas = ','.join(k + '=%s' for k in datos)
        if self.configuracion(bloquear=True) is None:
            self.insertar('configuracion_general', dict(id_configuracion=1, **datos))
        else:
            self.ejecutar(
                'UPDATE configuracion_general SET ' + columnas + ' WHERE id_configuracion=1',
                tuple(datos.values()),
            )

    def guardar_limite(self, tipo, cantidad):
        self.ejecutar(
            '''INSERT INTO limite_articulos_prestamo(tipo_persona,maximo_articulos) VALUES(%s,%s)
            ON DUPLICATE KEY UPDATE maximo_articulos=%s''',
            (tipo, cantidad, cantidad),
        )
