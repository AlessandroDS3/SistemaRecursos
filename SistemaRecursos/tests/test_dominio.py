from datetime import datetime, timedelta
import unittest
from dominio.compartido.validacion import Conflicto, entero, fecha_local
from dominio.gestion_personas_usuarios.persona import Persona
from dominio.gestion_personas_usuarios.cuenta import proteger_administradores
from dominio.gestion_personas_usuarios.rol import validar_matriz
from dominio.gestion_recursos.bien_material import BienMaterial, validar_cambio_estado
from dominio.gestion_control.politica_prestamo import (
    ConfiguracionReservas,
    HorarioAtencion,
    PoliticaPrestamo,
)
from dominio.gestion_control.reporte import FiltroReporte, celda_csv
from dominio.gestion_prestamos.prestamo import SolicitudPrestamo, estado_prestamo
from dominio.gestion_prestamos.ampliacion_prestamo import AmpliacionPrestamo
from dominio.gestion_prestamos.devolucion import Devolucion


class ReglasDominio(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 14, 15)  # 10:00 de Lima.
        self.politica = dict(
            id_politica=1,
            tipo_persona='ESTUDIANTE',
            id_categoria=1,
            plazo_maximo=2,
            unidad_plazo='DIAS',
            permite_salida=False,
        )
        self.solicitud = SolicitudPrestamo(
            dni_persona='12345678', dni_encargado='87654321', bienes=[1, 2]
        )
        self.contexto = dict(
            personas={
                '12345678': dict(estado='ACTIVA', tipo='ESTUDIANTE', estado_matricula='VIGENTE')
            },
            sancion=False,
            vencido=False,
            limite=4,
            pendientes=2,
            entregas_pendientes=False,
            bienes=[dict(id_bien=i, id_categoria=1, estado='DISPONIBLE') for i in (1, 2)],
            politicas={1: self.politica},
            horario=HorarioAtencion(),
            ahora=self.ahora,
        )

    def test_cupo_total_cuenta_bienes_de_todas_las_categorias(self):
        self.assertEqual(len(self.solicitud.planificar(self.contexto)), 2)
        self.contexto['pendientes'] = 3
        with self.assertRaises(Conflicto):
            self.solicitud.planificar(self.contexto)

    def test_ningun_bien_pendiente_se_vuelve_a_entregar(self):
        self.contexto['entregas_pendientes'] = True
        with self.assertRaises(Conflicto):
            self.solicitud.planificar(self.contexto)

    def test_revalidacion_de_todos_los_integrantes(self):
        self.solicitud = SolicitudPrestamo(
            dni_persona='12345678',
            dni_encargado='87654321',
            bienes=[1],
            tipo_prestamo='GRUPAL',
            participantes=['99999999'],
        )
        self.contexto['bienes'] = self.contexto['bienes'][:1]
        self.contexto['personas']['99999999'] = dict(
            estado='INACTIVA', tipo='ESTUDIANTE', estado_matricula='VIGENTE'
        )
        with self.assertRaises(ValueError):
            self.solicitud.planificar(self.contexto)

    def test_grupo_no_admite_duplicados_ni_responsable_repetido(self):
        for integrantes in (['12345678'], ['99999999', '99999999'], []):
            with self.subTest(integrantes=integrantes), self.assertRaises(ValueError):
                SolicitudPrestamo(
                    dni_persona='12345678',
                    dni_encargado='87654321',
                    bienes=[1],
                    tipo_prestamo='GRUPAL',
                    participantes=integrantes,
                )

    def test_sancion_y_vencimiento_impiden_entrega(self):
        for campo in ('sancion', 'vencido'):
            with self.subTest(campo=campo), self.assertRaises(Conflicto):
                self.solicitud.planificar(dict(self.contexto, **{campo: True}))

    def test_horas_terminan_al_cierre_y_dias_conservan_la_hora(self):
        horario = HorarioAtencion()
        por_horas = PoliticaPrestamo.desde_datos(
            dict(self.politica, unidad_plazo='HORAS', plazo_maximo=24)
        )
        self.assertEqual(por_horas.vencimiento(self.ahora, horario), datetime(2026, 11, 14, 21))
        self.assertEqual(
            PoliticaPrestamo.desde_datos(self.politica).vencimiento(self.ahora, horario),
            self.ahora + timedelta(days=2),
        )
        with self.assertRaises(ValueError):
            horario.cierre(datetime(2026, 11, 14, 22))

    def test_ampliacion_limite_y_formulario_duplicado(self):
        anterior = self.ahora + timedelta(hours=1)
        detalle = dict(
            fecha_limite_devolucion=anterior, fecha_devolucion=None, estado_bien='PRESTADO'
        )
        ampliacion = AmpliacionPrestamo(cantidad=2, unidad='DIAS', fecha_anterior=anterior)
        politica = PoliticaPrestamo.desde_datos(self.politica)
        nueva = ampliacion.calcular(detalle, self.ahora, politica, HorarioAtencion())
        self.assertEqual(nueva, anterior + timedelta(days=2))
        with self.assertRaises(Conflicto):
            ampliacion.calcular(
                dict(detalle, fecha_limite_devolucion=nueva),
                self.ahora,
                politica,
                HorarioAtencion(),
            )
        with self.assertRaises(ValueError):
            AmpliacionPrestamo(cantidad=3, unidad='DIAS', fecha_anterior=anterior).calcular(
                detalle, self.ahora, politica, HorarioAtencion()
            )

    def test_no_ampliar_perdido_devuelto_o_vencido(self):
        anterior = self.ahora + timedelta(hours=1)
        detalle = dict(
            fecha_limite_devolucion=anterior, fecha_devolucion=None, estado_bien='PRESTADO'
        )
        for cambios in (dict(estado_bien='PERDIDO'), dict(fecha_devolucion=self.ahora)):
            with self.subTest(cambios=cambios), self.assertRaises(Conflicto):
                AmpliacionPrestamo(cantidad=1, unidad='HORAS', fecha_anterior=anterior).calcular(
                    dict(detalle, **cambios),
                    self.ahora,
                    PoliticaPrestamo.desde_datos(self.politica),
                    HorarioAtencion(),
                )
        with self.assertRaises(Conflicto):
            AmpliacionPrestamo(cantidad=1, unidad='HORAS', fecha_anterior=anterior).calcular(
                detalle, anterior, PoliticaPrestamo.desde_datos(self.politica), HorarioAtencion()
            )

    def test_devolucion_danada_exige_descripcion_y_recupera_perdido(self):
        with self.assertRaises(ValueError):
            Devolucion(id_detalle=1, condicion='DANADO')
        devolucion = Devolucion(id_detalle=1, condicion='DANADO', observacion='Cable roto')
        devolucion.validar(dict(fecha_devolucion=None, estado_bien='PERDIDO'))
        self.assertEqual(devolucion.estado_bien, 'DANADO')

    def test_estado_prestamo_parcial_vencido_y_devuelto(self):
        devuelto = dict(
            fecha_devolucion=self.ahora, fecha_limite_devolucion=self.ahora + timedelta(days=1)
        )
        pendiente = dict(devuelto, fecha_devolucion=None)
        self.assertEqual(
            estado_prestamo([devuelto, pendiente], self.ahora), 'PARCIALMENTE_DEVUELTO'
        )
        self.assertEqual(
            estado_prestamo(
                [
                    devuelto,
                    dict(pendiente, fecha_limite_devolucion=self.ahora - timedelta(seconds=1)),
                ],
                self.ahora,
            ),
            'VENCIDO',
        )
        self.assertEqual(estado_prestamo([devuelto], self.ahora), 'DEVUELTO')

    def test_reservas_tienen_topes_segun_la_unidad(self):
        for datos in (dict(plazo_espera=31), dict(plazo_retiro=721), dict(unidad_espera='SEMANAS')):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                ConfiguracionReservas(**datos)
        with self.assertRaises(ValueError):
            HorarioAtencion(hora_apertura=timedelta(hours=8, seconds=1))

    def test_bien_admite_fecha_desconocida_y_evitar_cambios_manual_prestado(self):
        self.assertIsNone(
            BienMaterial(
                id_recurso=1, codigo_inventario='INV', fecha_adquisicion=''
            ).fecha_adquisicion
        )
        with self.assertRaises(Conflicto):
            validar_cambio_estado('PRESTADO', 'DISPONIBLE', 'PRESTADO')

    def test_datos_incompletos_son_errores_de_validacion(self):
        for constructor in (Persona.desde_datos, PoliticaPrestamo.desde_datos):
            with self.subTest(constructor=constructor), self.assertRaises(ValueError):
                constructor({})
        for valor in (True, 1.5, '1.0', '0', None):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                entero(valor)

    def test_reportes_incluyen_hasta_fin_del_dia_de_lima(self):
        filtro = FiltroReporte(desde='2026-11-14', hasta='2026-11-14')
        self.assertEqual(filtro.inicio, datetime(2026, 11, 14, 5))
        self.assertEqual(filtro.fin, datetime(2026, 11, 15, 5))
        self.assertEqual(fecha_local('2026-11-14T10:00'), self.ahora)
        with self.assertRaises(ValueError):
            FiltroReporte(desde='2026-11-15', hasta='2026-11-14')

    def test_csv_impide_formulas_incluso_con_espacios_y_tab(self):
        for valor in ('=1+1', ' +CMD()', '\ttexto', '\r=1', '@SUM(A1)', '-1'):
            with self.subTest(valor=valor):
                self.assertTrue(celda_csv(valor).startswith("'"))
        self.assertEqual(celda_csv('Equipo normal'), 'Equipo normal')

    def test_no_se_pierde_ultimo_administrador(self):
        actual = dict(
            id_usuario=1, rol='ADMINISTRADOR', estado_cuenta='ACTIVA', estado_persona='ACTIVA'
        )
        with self.assertRaises(ValueError):
            proteger_administradores([actual], actual, dict(actual, rol='USUARIO'), 1)
        with self.assertRaises(ValueError):
            validar_matriz(dict(USUARIO=[], ENCARGADO_PRESTAMOS=[], ADMINISTRADOR=[]))
