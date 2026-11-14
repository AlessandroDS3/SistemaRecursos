"""Ejecuta toda la suite y exige que se incluyan las pruebas de MySQL."""
import os
from pathlib import Path
import sys
import unittest


def main():
    if not os.environ.get('TEST_MYSQL_PORT'):
        print('Falta TEST_MYSQL_PORT. Configura la conexión MySQL de pruebas según README.md.',
              file=sys.stderr)
        return 2
    raiz = Path(__file__).resolve().parent
    # Las pruebas importan los módulos de aplicación y sus auxiliares locales.
    sys.path.insert(0, str(raiz))
    suite = unittest.defaultTestLoader.discover(str(raiz / 'tests'))
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if resultado.skipped:
        print(f'Verificación incompleta: {len(resultado.skipped)} pruebas omitidas.', file=sys.stderr)
        return 1
    if resultado.testsRun == 0:
        print('No se encontraron pruebas.', file=sys.stderr)
        return 1
    return 0 if resultado.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
