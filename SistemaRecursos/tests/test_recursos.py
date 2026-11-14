from mysql.connector import IntegrityError
from dominio.compartido.validacion import Conflicto
from caso_mysql import CasoMySQL


class RecursosYPoliticas(CasoMySQL):
    def test_recurso_y_primer_bien_son_una_transaccion(self):
        with self.assertRaises(IntegrityError):
            self.servicios['recursos'].guardar(
                dict(nombre='No debe existir', id_categoria=1, codigo_inventario='INV-2'), 1
            )
        self.assertEqual(
            self.fila("SELECT COUNT(*) FROM recurso WHERE nombre='No debe existir'"), (0,)
        )
        recurso = self.servicios['recursos'].guardar(
            dict(nombre='Nuevo', id_categoria=1, codigo_inventario='NUEVO'), 1
        )
        self.assertEqual(
            self.fila("SELECT id_recurso FROM bien_material WHERE codigo_inventario='NUEVO'"),
            (recurso,),
        )

    def test_actualizar_bien_con_fecha_y_descripcion_vacias(self):
        self.servicios['bienes'].guardar(
            dict(codigo_inventario='INV-2', fecha_adquisicion='', descripcion_bien=''), 1, 2
        )
        self.assertEqual(
            self.fila(
                'SELECT fecha_adquisicion,descripcion_bien FROM bien_material WHERE id_bien=2'
            ),
            (None, None),
        )

    def test_cambio_estado_comprueba_version_y_registra_actor(self):
        datos = dict(estado='MANTENIMIENTO', estado_esperado='DISPONIBLE', motivo='Revisión')
        self.servicios['bienes'].cambiar_estado(2, datos, 1)
        with self.assertRaises(Conflicto):
            self.servicios['bienes'].cambiar_estado(2, datos, 1)
        self.assertEqual(
            self.fila(
                "SELECT estado_anterior,estado_nuevo,dni_responsable FROM historial_estado WHERE entidad='BIEN_MATERIAL' AND id_entidad=2"
            ),
            ('DISPONIBLE', 'MANTENIMIENTO', '98000001'),
        )

    def test_bien_con_pendiente_no_se_habilita_ni_se_elimina(self):
        prestamo = self.prestar()
        self.servicios['prestamos'].reportar_perdida(
            prestamo, self.prestamo(prestamo)['detalles'][0]['id_detalle'], 'No encontrado', 2
        )
        with self.assertRaises(Conflicto):
            self.servicios['bienes'].cambiar_estado(
                2, dict(estado='DISPONIBLE', estado_esperado='PERDIDO', motivo='Hallado'), 1
            )
        with self.assertRaises(IntegrityError):
            self.servicios['bienes'].eliminar(2, 1)

    def test_editar_politica_conserva_version_aplicada(self):
        prestamo = self.prestar()
        anterior, version = self.servicios['politicas'].consultar(24)
        nueva = self.servicios['politicas'].guardar(
            dict(anterior, plazo_maximo=3, version=version), 1, 24
        )
        self.assertNotEqual(nueva, 24)
        self.assertEqual(
            self.fila('SELECT vigente,plazo_maximo FROM politica_prestamo WHERE id_politica=24'),
            (0, 2),
        )
        self.assertEqual(self.prestamo(prestamo)['detalles'][0]['id_politica'], 24)

    def test_configuracion_y_limites_se_administran_en_politicas(self):
        self.servicios['politicas'].guardar_configuracion(
            dict(
                hora_apertura='09:00',
                hora_cierre='17:00',
                plazo_espera='30',
                unidad_espera='DIAS',
                plazo_retiro='720',
                unidad_retiro='HORAS',
            ),
            1,
        )
        self.servicios['politicas'].guardar_limite('ESTUDIANTE', 6, 1)
        self.assertEqual(
            self.fila('SELECT plazo_espera,plazo_retiro FROM configuracion_general'), (30, 720)
        )
        self.assertEqual(
            self.fila(
                "SELECT maximo_articulos FROM limite_articulos_prestamo WHERE tipo_persona='ESTUDIANTE'"
            ),
            (6,),
        )
        with self.assertRaises(ValueError):
            self.servicios['politicas'].guardar_configuracion(
                dict(
                    hora_apertura='09:00',
                    hora_cierre='17:00',
                    plazo_espera='31',
                    unidad_espera='DIAS',
                ),
                1,
            )
