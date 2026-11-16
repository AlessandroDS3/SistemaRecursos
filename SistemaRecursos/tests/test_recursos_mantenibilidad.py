from concurrent.futures import ThreadPoolExecutor
from datetime import date
import re
from threading import Barrier
from unittest.mock import patch

from dominio.compartido.validacion import Conflicto, NoEncontrado
from repositorio.repositorio_bien_material_sql import RepositorioBienMaterialSQL
from repositorio.repositorio_recurso_sql import RepositorioRecursoSQL
from caso_mysql import CasoMySQL


class MantenimientoRecursos(CasoMySQL):
    def test_ediciones_antiguas_y_sin_version_se_rechazan(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        for consultar, guardar, identificador, campo in (
            (recursos.consultar_recurso, recursos.guardar_recurso, 1, 'nombre'),
            (recursos.consultar_categoria, recursos.guardar_categoria, 1, 'nombre'),
            (bienes.consultar_bien_material, bienes.guardar_bien_material, 2, 'ubicacion'),
        ):
            with self.subTest(operacion=guardar.__name__):
                original = consultar(identificador)
                guardar(dict(original, **{campo: 'Primera edición'}), 1, identificador)
                with self.assertRaises(Conflicto):
                    guardar(dict(original, **{campo: 'Edición antigua'}), 1, identificador)
                with self.assertRaises(Conflicto):
                    guardar({campo: 'Sin versión'}, 1, identificador)
                self.assertEqual(consultar(identificador)[campo], 'Primera edición')

    def test_actualizar_sin_cambios_es_correcto(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        for consultar, guardar, identificador in (
            (recursos.consultar_recurso, recursos.guardar_recurso, 1),
            (recursos.consultar_categoria, recursos.guardar_categoria, 1),
            (bienes.consultar_bien_material, bienes.guardar_bien_material, 2),
        ):
            with self.subTest(operacion=guardar.__name__):
                datos = consultar(identificador)
                self.assertEqual(guardar(datos, 1, identificador), identificador)
                self.assertEqual(guardar(consultar(identificador), 1, identificador), identificador)

    def test_bien_parcial_conserva_omitidos_y_vacio_limpia_opcionales(self):
        bienes = self.servicios['bienes']
        identificador = bienes.guardar_bien_material(
            dict(
                id_recurso=1,
                codigo_inventario='PARCIAL',
                numero_serie='SERIE',
                fecha_adquisicion='2026-11-14',
                ubicacion='Almacén',
                descripcion_bien='Con cable',
            ),
            1,
        )
        datos = bienes.consultar_bien_material(identificador)
        bienes.guardar_bien_material(
            dict(
                version=datos['version'],
                ubicacion='Laboratorio 2',
                id_recurso=2,
                id_bien=1,
                estado='PERDIDO',
            ),
            1,
            identificador,
        )
        actual = bienes.consultar_bien_material(identificador)
        self.assertEqual(
            tuple(
                actual[c]
                for c in (
                    'id_recurso',
                    'codigo_inventario',
                    'numero_serie',
                    'fecha_adquisicion',
                    'descripcion_bien',
                    'estado',
                )
            ),
            (1, 'PARCIAL', 'SERIE', date(2026, 11, 14), 'Con cable', 'DISPONIBLE'),
        )
        bienes.guardar_bien_material(
            dict(
                version=actual['version'],
                numero_serie='',
                fecha_adquisicion='',
                descripcion_bien='',
            ),
            1,
            identificador,
        )
        actual = bienes.consultar_bien_material(identificador)
        self.assertEqual(
            (actual['numero_serie'], actual['fecha_adquisicion'], actual['descripcion_bien']),
            ('', None, None),
        )
        self.assertEqual(actual['ubicacion'], 'Laboratorio 2')
        with self.assertRaises(ValueError):
            bienes.guardar_bien_material(
                dict(version=actual['version'], codigo_inventario=''), 1, identificador
            )
        self.assertEqual(
            bienes.consultar_bien_material(identificador)['codigo_inventario'], 'PARCIAL'
        )

    def test_cambiar_estado_no_invalida_la_edicion_descriptiva(self):
        bienes = self.servicios['bienes']
        original = bienes.consultar_bien_material(2)
        bienes.cambiar_estado_bien_material(
            2,
            dict(
                estado_esperado='DISPONIBLE',
                estado='MANTENIMIENTO',
                motivo='Revisión',
            ),
            1,
        )
        bienes.guardar_bien_material(dict(version=original['version'], ubicacion='Taller'), 1, 2)
        actual = bienes.consultar_bien_material(2)
        self.assertEqual((actual['ubicacion'], actual['estado']), ('Taller', 'MANTENIMIENTO'))
        self.assertEqual(len(bienes.consultar_historial_bien_material(2)), 1)

    def test_busquedas_coherentes_y_estado_del_mismo_bien(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        self.ejecutar("UPDATE recurso SET marca='Epson',modelo='X49' WHERE id_recurso=1")
        for consulta, ids in (('Epson', [1, 2, 3]), ('X49', [1, 2, 3]), ('INV-2', [2])):
            with self.subTest(q=consulta):
                filtros = {'q': consulta}
                catalogo = recursos.consultar_recursos(filtros)
                inventario = bienes.consultar_bienes_materiales(filtros)
                panel = recursos.consultar_administracion_recursos(filtros)
                self.assertEqual([r['id_recurso'] for r in catalogo], [1])
                self.assertEqual([b['id_bien'] for b in inventario], ids)
                self.assertEqual([g['recurso']['id_recurso'] for g in panel['grupos']], [1])
                self.assertEqual([b['id_bien'] for b in panel['grupos'][0]['bienes']], ids)
                self.assertEqual(panel['resumen']['bienes'], len(ids))
                self.assertEqual((catalogo[0]['total'], catalogo[0]['disponibles']), (3, 2))
        filtros = dict(q='INV-1', estado='DISPONIBLE')
        self.assertEqual(recursos.consultar_recursos(filtros), [])
        self.assertEqual(bienes.consultar_bienes_materiales(filtros), [])
        self.assertEqual(recursos.consultar_administracion_recursos(filtros)['grupos'], [])

    def test_panel_conserva_recursos_sin_bienes_y_filtra_categoria(self):
        recursos = self.servicios['recursos']
        panel = recursos.consultar_administracion_recursos({})
        self.assertEqual(panel['resumen'], dict(recursos=2, bienes=3, disponibles=2))
        self.assertEqual(
            next(g['bienes'] for g in panel['grupos'] if g['recurso']['id_recurso'] == 2), []
        )
        categoria = recursos.guardar_categoria(dict(nombre='Otra'), 1)
        recurso = recursos.guardar_recurso(dict(nombre='Sin bienes', id_categoria=categoria), 1)
        panel = recursos.consultar_administracion_recursos(dict(id_categoria=str(categoria)))
        self.assertEqual([g['recurso']['id_recurso'] for g in panel['grupos']], [recurso])
        self.assertEqual(panel['resumen'], dict(recursos=1, bienes=0, disponibles=0))
        self.assertEqual(len(recursos.consultar_recursos(dict(q='Sin bienes'))), 1)
        self.assertEqual(recursos.consultar_recursos(dict(q='Sin bienes', estado='DISPONIBLE')), [])

    def test_inexistentes_devuelven_404_y_cero_no_crea_registros(self):
        self.login()
        for ruta, datos in (
            ('/recursos/999/eliminar', {}),
            ('/bienes/999/eliminar', {}),
            ('/recursos/categorias/999/eliminar', {}),
            ('/recursos/999/editar', {'nombre': 'Inexistente'}),
            ('/bienes/999/editar', {'ubicacion': 'Inexistente'}),
            ('/recursos/categorias', {'id_categoria': '999', 'nombre': 'Inexistente'}),
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.post(ruta, datos).status_code, 404)
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        for guardar in (
            recursos.guardar_recurso,
            recursos.guardar_categoria,
            bienes.guardar_bien_material,
        ):
            with self.subTest(operacion=guardar.__name__), self.assertRaises(ValueError):
                guardar(
                    dict(nombre='No crear', id_categoria=1, id_recurso=1, codigo_inventario='NO'),
                    1,
                    0,
                )
        self.assertEqual(self.fila('SELECT COUNT(*) FROM recurso'), (2,))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM categoria_recurso'), (1,))
        self.assertEqual(self.fila('SELECT COUNT(*) FROM bien_material'), (3,))

    def test_eliminar_sin_relaciones_borra_solo_el_registro_solicitado(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        categoria = recursos.guardar_categoria(dict(nombre='Temporal'), 1)
        recurso = recursos.guardar_recurso(dict(nombre='Temporal', id_categoria=categoria), 1)
        bien = bienes.guardar_bien_material(dict(id_recurso=recurso, codigo_inventario='TEMP'), 1)
        bienes.eliminar_bien_material(bien, 1)
        self.assertEqual(recursos.consultar_recurso(recurso)['id_categoria'], categoria)
        recursos.eliminar_recurso(recurso, 1)
        self.assertEqual(recursos.consultar_categoria(categoria)['nombre'], 'Temporal')
        recursos.eliminar_categoria(categoria, 1)
        for consultar, identificador in (
            (bienes.consultar_bien_material, bien),
            (recursos.consultar_recurso, recurso),
            (recursos.consultar_categoria, categoria),
        ):
            with self.assertRaises(NoEncontrado):
                consultar(identificador)

    def test_eliminacion_protege_relaciones_e_historial_con_motivos(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        with self.assertRaisesRegex(Conflicto, 'recursos registrados'):
            recursos.eliminar_categoria(1, 1)
        with self.assertRaisesRegex(Conflicto, 'bienes registrados'):
            recursos.eliminar_recurso(1, 1)
        bienes.cambiar_estado_bien_material(
            2,
            dict(
                estado_esperado='DISPONIBLE',
                estado='MANTENIMIENTO',
                motivo='Revisión',
            ),
            1,
        )
        with self.assertRaisesRegex(Conflicto, 'historial'):
            bienes.eliminar_bien_material(2, 1)
        self.assertEqual(len(bienes.consultar_historial_bien_material(2)), 1)
        self.reservar(id_recurso=2)
        with self.assertRaisesRegex(Conflicto, 'reservas'):
            recursos.eliminar_recurso(2, 1)
        self.ejecutar(
            """INSERT INTO reserva(dni_persona,id_recurso,id_bien,fecha_solicitud,fecha_requerida,estado)
                         VALUES('02167885',1,3,UTC_TIMESTAMP(),UTC_TIMESTAMP(),'CANCELADA')"""
        )
        with self.assertRaisesRegex(Conflicto, 'reservas'):
            bienes.eliminar_bien_material(3, 1)
        categoria = recursos.guardar_categoria(dict(nombre='Con política'), 1)
        self.ejecutar(
            """INSERT INTO politica_prestamo(tipo_persona,id_categoria,plazo_maximo,unidad_plazo)
                         VALUES('ESTUDIANTE',%s,2,'DIAS')""",
            (categoria,),
        )
        with self.assertRaisesRegex(Conflicto, 'políticas'):
            recursos.eliminar_categoria(categoria, 1)

    def test_formularios_envian_version_y_rechazan_reenvio_antiguo(self):
        self.login()
        for ruta_get, ruta_post, datos in (
            ('/recursos/1/editar', '/recursos/1/editar', dict(nombre='Nuevo recurso')),
            ('/bienes/2/editar', '/bienes/2/editar', dict(ubicacion='Nueva ubicación')),
            (
                '/recursos/categorias',
                '/recursos/categorias',
                dict(id_categoria='1', nombre='Nueva categoría'),
            ),
        ):
            with self.subTest(ruta=ruta_post):
                pagina = self.cliente.get(ruta_get).get_data(as_text=True)
                version = re.search(r'name="version"\s+value="([^"]+)"', pagina).group(1)
                datos = dict(datos, version=version)
                self.assertEqual(self.post(ruta_post, datos).status_code, 302)
                self.assertEqual(self.post(ruta_post, datos).status_code, 409)

    def test_dos_ediciones_simultaneas_solo_guardan_una(self):
        recursos, bienes = self.servicios['recursos'], self.servicios['bienes']
        for consultar, guardar, identificador, campo, repositorio, metodo in (
            (
                recursos.consultar_recurso,
                recursos.guardar_recurso,
                1,
                'nombre',
                RepositorioRecursoSQL,
                'consultar_recurso',
            ),
            (
                recursos.consultar_categoria,
                recursos.guardar_categoria,
                1,
                'nombre',
                RepositorioRecursoSQL,
                'consultar_categoria',
            ),
            (
                bienes.consultar_bien_material,
                bienes.guardar_bien_material,
                2,
                'ubicacion',
                RepositorioBienMaterialSQL,
                'consultar_bien_material',
            ),
        ):
            with self.subTest(operacion=guardar.__name__):
                original = consultar(identificador)
                barrera = Barrier(2)
                lectura = getattr(repositorio, metodo)

                def leer_juntos(repo, id_registro, bloquear=False):
                    if bloquear:
                        barrera.wait(timeout=5)
                    return lectura(repo, id_registro, bloquear)

                with (
                    patch.object(repositorio, metodo, leer_juntos),
                    ThreadPoolExecutor(max_workers=2) as ejecutor,
                ):
                    tareas = [
                        ejecutor.submit(guardar, dict(original, **{campo: valor}), 1, identificador)
                        for valor in ('Primero', 'Segundo')
                    ]
                    errores = [tarea.exception(timeout=10) for tarea in tareas]
                self.assertEqual(sum(error is None for error in errores), 1, errores)
                self.assertTrue(
                    all(error is None or isinstance(error, Conflicto) for error in errores), errores
                )
                self.assertIn(consultar(identificador)[campo], ('Primero', 'Segundo'))
