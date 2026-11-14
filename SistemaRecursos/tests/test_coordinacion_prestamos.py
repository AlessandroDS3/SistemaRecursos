from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dominio.gestion_control.control import HorarioAtencion
from dominio.gestion_control.control import PoliticaPrestamo, LimiteArticulosPrestamo
from dominio.gestion_prestamos.prestamos import ContextoEntrega
from dominio.gestion_prestamos.prestamos import SolicitudPrestamo
from dominio.gestion_prestamos.prestamos import ConflictoPrestamoError
from servicios.servicio_prestamo import ServicioAplicacionPrestamo


class CoordinacionEntregaTest(unittest.TestCase):
    def setUp(self):
        self.solicitud = SolicitudPrestamo(dni_persona='99000001',dni_encargado='98000002',ids_bienes=[1])
        self.contexto = ContextoEntrega(
            personas={'99000001':{'estado':'ACTIVA','tipo':'ESTUDIANTE','estado_matricula':'VIGENTE'},
                      '98000002':{'estado':'ACTIVA','tipo':'ADMINISTRATIVO'}},
            tiene_vencidos=False,tiene_sanciones=False,
            limite=LimiteArticulosPrestamo(tipo_persona='ESTUDIANTE',maximo_articulos=4),pendientes=0,
            bienes=[{'id_bien':1,'id_categoria':1,'estado':'DISPONIBLE'}],tiene_entregas_pendientes=False,
            politicas={1:PoliticaPrestamo(tipo_persona='ESTUDIANTE',id_categoria=1,plazo_maximo=2,unidad_plazo='DIAS',id_politica=1)},
            horario=HorarioAtencion(),ahora=datetime(2026,11,12,14))

    def test_reglas_de_elegibilidad_cupo_inventario_y_politicas_sin_mysql(self):
        variantes=[{'tiene_vencidos':True},{'tiene_sanciones':True},{'pendientes':4},
                   {'bienes':[]},{'bienes':[{'id_bien':1,'id_categoria':1,'estado':'PRESTADO'}]},
                   {'tiene_entregas_pendientes':True},{'politicas':{}},{'horario':None},
                   {'personas':{}},{'ahora':datetime(2026,11,12,23)}]
        for cambios in variantes:
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                replace(self.contexto,**cambios).construir_prestamo(self.solicitud)

    def test_bien_reservado_solo_se_acepta_en_la_entrega_de_su_reserva(self):
        contexto=replace(self.contexto,bienes=[{'id_bien':1,'id_categoria':1,'estado':'RESERVADO'}])
        with self.assertRaises(ConflictoPrestamoError):contexto.construir_prestamo(self.solicitud)
        self.assertEqual(contexto.construir_prestamo(self.solicitud,1).detalles[0].id_bien,1)

    def test_servicio_coordina_carga_regla_guardado_y_una_sola_transaccion(self):
        eventos=[];contexto=self.contexto
        class Operacion:
            def cargar_entrega(self,solicitud):eventos.append('cargar');return contexto
            def guardar_entrega(self,prestamo,bienes,ahora):eventos.append('guardar');return prestamo
        class Repositorio:
            @contextmanager
            def transaccion(self):
                eventos.append('abrir')
                try:yield Operacion()
                except Exception:eventos.append('rollback');raise
                else:eventos.append('commit')
        servicio=ServicioAplicacionPrestamo(Repositorio(),None,None,None)
        self.assertEqual(len(servicio.registrar_solicitud(self.solicitud).detalles),1)
        self.assertEqual(eventos,['abrir','cargar','guardar','commit'])

    def test_una_regla_rechazada_no_llega_al_guardado(self):
        contexto=replace(self.contexto,tiene_sanciones=True)
        guardar=[]
        @contextmanager
        def transaccion():yield SimpleNamespace(cargar_entrega=lambda solicitud:contexto,
            guardar_entrega=lambda *args:guardar.append(args))
        servicio=ServicioAplicacionPrestamo(SimpleNamespace(transaccion=transaccion),None,None,None)
        with self.assertRaises(ConflictoPrestamoError):servicio.registrar_solicitud(self.solicitud)
        self.assertEqual(guardar,[])


@unittest.skipUnless(os.environ.get('TEST_MYSQL_PORT'),'Configura MySQL de pruebas.')
class EntregaTransaccionalTest(unittest.TestCase):
    def setUp(self):
        from soporte_prestamos import preparar_base_prestamos
        preparar_base_prestamos(self)
        self.servicio=self.app.extensions['prestamos']
        with self.db.sesion(escritura=True) as c:
            c.execute('DELETE FROM prestamo')
            c.execute("UPDATE bien_material SET estado='DISPONIBLE'")
            c.execute("UPDATE configuracion_general SET hora_apertura='00:00',hora_cierre='23:59'")
            c.execute("INSERT INTO limite_articulos_prestamo VALUES('ESTUDIANTE',4)")

    def solicitud(self,grupal=False):
        participantes=[{'dni_persona':'99000001','responsable':True},{'dni_persona':'99000002'}] if grupal else []
        return SolicitudPrestamo(dni_persona='99000001',dni_encargado='98000002',ids_bienes=[1],
            tipo_prestamo='GRUPAL' if grupal else 'INDIVIDUAL',participantes=participantes)

    def estado(self):
        with self.db.sesion() as c:
            resultado={}
            for tabla in ('prestamo','detalle_prestamo','participante_prestamo','historial_estado'):
                c.execute('SELECT COUNT(*) AS n FROM '+tabla);resultado[tabla]=c.fetchone()['n']
            c.execute('SELECT estado FROM bien_material WHERE id_bien=1');resultado['bien']=c.fetchone()['estado']
            return resultado

    def preparar_reserva(self):
        with self.db.sesion(escritura=True) as c:
            c.execute('''INSERT INTO reserva(dni_persona,id_recurso,fecha_solicitud,fecha_requerida,fecha_limite_vencimiento)
                VALUES('99000001',1,UTC_TIMESTAMP(),DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY))''')
            identificador=c.lastrowid
        servicio=self.app.extensions['reservas']
        servicio.preparar_reserva(identificador,{},'98000002',True)
        return identificador

    def test_entrega_grupal_persiste_el_conjunto_y_rechaza_segundo_prestamo(self):
        prestamo=self.servicio.registrar_solicitud(self.solicitud(True))
        estado=self.estado()
        self.assertEqual((estado['prestamo'],estado['detalle_prestamo'],estado['participante_prestamo'],estado['bien']),(1,1,2,'PRESTADO'))
        with self.assertRaises(ConflictoPrestamoError):self.servicio.registrar_solicitud(self.solicitud())
        self.assertEqual(self.estado(),estado)
        self.assertGreater(prestamo.id_prestamo,0)

    def test_fallo_en_historial_revierte_prestamo_detalles_grupo_e_inventario(self):
        from repositorio.repositorio_prestamo_sql import OperacionPrestamoSQL
        anterior=self.estado()
        with patch.object(OperacionPrestamoSQL,'_guardar_historial',side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):self.servicio.registrar_solicitud(self.solicitud(True))
        self.assertEqual(self.estado(),anterior)

    def test_reserva_y_prestamo_se_confirman_juntos(self):
        identificador=self.preparar_reserva()
        prestamo=self.app.extensions['reservas'].entregar_reserva(identificador,{'acepta_condiciones':'1'},'98000002',True)
        with self.db.sesion() as c:
            c.execute('SELECT estado,id_prestamo_ref FROM reserva WHERE id_reserva=%s',(identificador,))
            fila=c.fetchone()
            self.assertEqual((fila['estado'],fila['id_prestamo_ref']),('ATENDIDA',prestamo))
        self.assertEqual(self.estado()['bien'],'PRESTADO')

    def test_fallo_al_cerrar_reserva_revierte_tambien_el_prestamo(self):
        identificador=self.preparar_reserva();anterior=self.estado()
        repo=self.app.extensions['reservas'].repositorio
        with patch.object(repo,'_guardar_resolucion',side_effect=RuntimeError('Fallo al cerrar reserva')):
            with self.assertRaises(RuntimeError):
                self.app.extensions['reservas'].entregar_reserva(identificador,{'acepta_condiciones':'1'},'98000002',True)
        self.assertEqual(self.estado(),anterior)
        with self.db.sesion() as c:
            c.execute('SELECT estado,id_prestamo_ref FROM reserva WHERE id_reserva=%s',(identificador,))
            self.assertEqual(c.fetchone(),{'estado':'LISTA_PARA_RETIRO','id_prestamo_ref':None})

    def test_dos_entregas_concurrentes_no_prestan_dos_veces_el_mismo_bien(self):
        from concurrent.futures import ThreadPoolExecutor
        def entregar():
            try:self.servicio.registrar_solicitud(self.solicitud());return True
            except ConflictoPrestamoError:return False
        with ThreadPoolExecutor(max_workers=2) as executor:resultados=list(executor.map(lambda _:entregar(),range(2)))
        self.assertEqual(sorted(resultados),[False,True])
        self.assertEqual(self.estado()['detalle_prestamo'],1)

    def test_devolucion_y_perdida_siguen_las_reglas_del_dominio(self):
        prestamo=self.servicio.registrar_solicitud(self.solicitud())
        detalle=prestamo.detalles[0]
        self.servicio.reportar_perdida(prestamo.id_prestamo,detalle.id_detalle,'Equipo extraviado','98000002')
        self.assertEqual(self.estado()['bien'],'PERDIDO')
        with self.assertRaises(ConflictoPrestamoError):
            self.servicio.reportar_perdida(prestamo.id_prestamo,detalle.id_detalle,'Repetida','98000002')
        self.servicio.registrar_devolucion(prestamo.id_prestamo,{'detalles':[str(detalle.id_detalle)],
            'condicion_'+str(detalle.id_detalle):'DANADO',
            'observacion_'+str(detalle.id_detalle):'Equipo recuperado con daños'},'98000002')
        self.assertEqual(self.estado()['bien'],'DANADO')
        self.assertEqual(self.servicio.consultar_prestamo(prestamo.id_prestamo,'99000001')['estado'],'DEVUELTO')

    def test_devolucion_tardia_conserva_sancion_para_todo_el_grupo(self):
        prestamo=self.servicio.registrar_solicitud(self.solicitud(True))
        detalle=prestamo.detalles[0]
        with self.db.sesion(escritura=True) as c:
            c.execute('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE id_detalle=%s',(detalle.id_detalle,))
        self.servicio.registrar_devolucion(prestamo.id_prestamo,{'detalles':[str(detalle.id_detalle)],
            'condicion_'+str(detalle.id_detalle):'BUENO'},'98000002')
        with self.db.sesion() as c:
            c.execute("SELECT COUNT(*) AS n FROM sancion s JOIN incidencia i ON i.id_incidencia=s.id_incidencia_ref WHERE i.id_detalle=%s AND i.tipo='RETRASO'",(detalle.id_detalle,))
            self.assertEqual(c.fetchone()['n'],1)
        for dni in ('99000001','99000002'):
            solicitud=SolicitudPrestamo(dni_persona=dni,dni_encargado='98000002',ids_bienes=[1])
            with self.subTest(dni=dni), self.assertRaisesRegex(ConflictoPrestamoError,'sanción activa'):
                self.servicio.registrar_solicitud(solicitud)

    def test_devolucion_parcial_y_actualizacion_de_vencimientos(self):
        with self.db.sesion(escritura=True) as c:
            c.execute("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario) VALUES(2,1,'LIB-002')")
        solicitud=SolicitudPrestamo(dni_persona='99000001',dni_encargado='98000002',ids_bienes=[1,2])
        prestamo=self.servicio.registrar_solicitud(solicitud)
        primero,segundo=prestamo.detalles
        self.servicio.registrar_devolucion(prestamo.id_prestamo,{'detalles':[str(primero.id_detalle)],
            'condicion_'+str(primero.id_detalle):'BUENO'},'98000002')
        self.assertEqual(self.servicio.consultar_prestamo(prestamo.id_prestamo,'99000001')['estado'],'PARCIALMENTE_DEVUELTO')
        with self.db.sesion(escritura=True) as c:
            c.execute('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE id_detalle=%s',(segundo.id_detalle,))
        self.servicio.actualizar_prestamos_vencidos('98000002')
        with self.db.sesion() as c:
            c.execute('SELECT estado FROM prestamo WHERE id_prestamo=%s',(prestamo.id_prestamo,))
            self.assertEqual(c.fetchone()['estado'],'VENCIDO')

    def test_fallo_al_cerrar_devolucion_revierte_inventario_sancion_e_incidencia(self):
        from repositorio.repositorio_prestamo_sql import OperacionPrestamoSQL

        prestamo = self.servicio.registrar_solicitud(self.solicitud(True))
        detalle = prestamo.detalles[0]
        with self.db.sesion(escritura=True) as c:
            c.execute('UPDATE detalle_prestamo SET fecha_limite_devolucion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE id_detalle=%s', (detalle.id_detalle,))
        anterior = self.estado()
        datos = {'detalles': [str(detalle.id_detalle)],
                 f'condicion_{detalle.id_detalle}': 'BUENO'}
        with patch.object(OperacionPrestamoSQL, '_guardar_historial', side_effect=RuntimeError('Fallo al cerrar')):
            with self.assertRaises(RuntimeError):
                self.servicio.registrar_devolucion(prestamo.id_prestamo, datos, '98000002')
        self.assertEqual(self.estado(), anterior)
        with self.db.sesion() as c:
            c.execute('SELECT fecha_devolucion FROM detalle_prestamo WHERE id_detalle=%s', (detalle.id_detalle,))
            self.assertIsNone(c.fetchone()['fecha_devolucion'])
            for tabla in ('incidencia', 'sancion'):
                c.execute('SELECT COUNT(*) AS n FROM ' + tabla)
                self.assertEqual(c.fetchone()['n'], 0)
