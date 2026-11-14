"""Comprueba límites de dependencia y ausencia de las implementaciones reemplazadas."""

import ast
from pathlib import Path
import unittest

RAIZ = Path(__file__).resolve().parents[1]


class Arquitectura(unittest.TestCase):
    def test_dependencias_apuntan_hacia_dominio_y_no_forman_ciclos(self):
        archivos = [
            p
            for carpeta in ('dominio', 'servicios', 'repositorio', 'presentacion')
            for p in (RAIZ / carpeta).rglob('*.py')
        ]
        modulos = {'.'.join(p.relative_to(RAIZ).with_suffix('').parts): p for p in archivos}
        grafo = {nombre: set() for nombre in modulos}
        for modulo, ruta in modulos.items():
            for nodo in ast.walk(ast.parse(ruta.read_text(encoding='utf-8-sig'))):
                nombres = (
                    [nodo.module or '']
                    if isinstance(nodo, ast.ImportFrom)
                    else ([n.name for n in nodo.names] if isinstance(nodo, ast.Import) else [])
                )
                for nombre in nombres:
                    if modulo.startswith('dominio.'):
                        self.assertFalse(
                            nombre.startswith(
                                (
                                    'servicios',
                                    'repositorio',
                                    'presentacion',
                                    'flask',
                                    'mysql',
                                    'werkzeug',
                                )
                            ),
                            (modulo, nombre),
                        )
                    if modulo.startswith('servicios.'):
                        self.assertFalse(
                            nombre.startswith(('repositorio', 'presentacion', 'flask', 'mysql')),
                            (modulo, nombre),
                        )
                    if modulo.startswith('presentacion.'):
                        self.assertFalse(nombre.startswith('repositorio'), (modulo, nombre))
                    if modulo.startswith('repositorio.'):
                        self.assertFalse(
                            nombre.startswith(('servicios', 'presentacion')), (modulo, nombre)
                        )
                    if nombre in modulos:
                        grafo[modulo].add(nombre)
        visitados, activos = set(), set()

        def visitar(modulo):
            self.assertNotIn(modulo, activos, f'Ciclo en {modulo}')
            if modulo in visitados:
                return
            activos.add(modulo)
            for dependencia in grafo[modulo]:
                visitar(dependencia)
            activos.remove(modulo)
            visitados.add(modulo)

        for modulo in modulos:
            visitar(modulo)

    def test_servicios_no_manipulan_cursores_ni_sql(self):
        for archivo in (RAIZ / 'servicios').glob('*.py'):
            arbol = ast.parse(archivo.read_text(encoding='utf-8-sig'))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Attribute):
                    self.assertNotIn(
                        nodo.attr,
                        ('_cursor', 'execute', 'consultar_sql', 'sesion', 'commit'),
                        str(archivo),
                    )

    def test_recorridos_tienen_nombres_reconocibles(self):
        for nombre, area in (
            ('acceso', 'gestion_personas_usuarios'),
            ('cuenta', 'gestion_personas_usuarios'),
            ('persona', 'gestion_personas_usuarios'),
            ('rol', 'gestion_personas_usuarios'),
            ('recurso', 'gestion_recursos'),
            ('bien_material', 'gestion_recursos'),
            ('prestamo', 'gestion_prestamos'),
            ('reserva', 'gestion_prestamos'),
            ('ampliacion_prestamo', 'gestion_prestamos'),
            ('politica_prestamo', 'gestion_control'),
            ('sancion', 'gestion_control'),
            ('reporte', 'gestion_control'),
        ):
            for ruta in (
                f'dominio/{area}/{nombre}.py',
                f'servicios/servicio_{nombre}.py',
                f'repositorio/repositorio_{nombre}_sql.py',
                f'presentacion/controladores/controlador_{nombre}.py',
            ):
                self.assertTrue((RAIZ / ruta).is_file(), ruta)
