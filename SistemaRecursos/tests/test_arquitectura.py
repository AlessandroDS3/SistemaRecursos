"""Las reglas de dependencia son comprobables sin abrir una base de datos."""
import ast
from pathlib import Path
import unittest


class ArquitecturaTest(unittest.TestCase):
    def test_capas_y_modulos_internos_no_forman_ciclos(self):
        raiz = Path(__file__).resolve().parents[1]
        archivos = [p for carpeta in ('dominio', 'servicios', 'repositorio', 'presentacion')
                    for p in (raiz / carpeta).rglob('*.py')] + [raiz / 'app.py']
        modulos = {'.'.join(p.relative_to(raiz).with_suffix('').parts): p for p in archivos}
        grafo = {m: set() for m in modulos}
        for modulo, ruta in modulos.items():
            for nodo in ast.walk(ast.parse(ruta.read_text(encoding='utf-8-sig'))):
                if isinstance(nodo, ast.ImportFrom):
                    nombres = [nodo.module or '']
                elif isinstance(nodo, ast.Import):
                    nombres = [n.name for n in nodo.names]
                else:
                    continue
                for nombre in nombres:
                    if modulo.startswith('dominio.'):
                        self.assertFalse(nombre.startswith(('servicios.', 'repositorio.', 'presentacion.', 'flask', 'mysql')),
                                         f'{modulo} depende de {nombre}')
                    if modulo.startswith('servicios.'):
                        self.assertFalse(nombre.startswith(('repositorio.', 'presentacion.', 'flask', 'mysql')),
                                         f'{modulo} depende de {nombre}')
                    if nombre in modulos:
                        grafo[modulo].add(nombre)
        visitados, activos = set(), set()

        def visitar(modulo):
            self.assertNotIn(modulo, activos, f'Ciclo de dependencias en {modulo}')
            if modulo in visitados:
                return
            activos.add(modulo)
            for destino in grafo[modulo]:
                visitar(destino)
            activos.remove(modulo)
            visitados.add(modulo)

        for modulo in modulos:
            visitar(modulo)
