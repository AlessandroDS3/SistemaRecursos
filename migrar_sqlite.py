"""Importación única, transaccional, desde un archivo SQLite de solo lectura."""
import argparse
from pathlib import Path
import sqlite3
from app.config import load_config
from app.repository import RecursoMySQLRepository


def migrar(source, config):
    source = Path(source).resolve(strict=True)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as old:
        old.row_factory = sqlite3.Row
        old.execute('BEGIN')
        data = {table: [dict(row) for row in old.execute(f'SELECT * FROM {table}')]
                for table in ('categoria_recurso', 'recurso', 'bien_material')}
    repo = RecursoMySQLRepository(config)
    repo.initialize()
    with repo.connection() as conn, conn.cursor(buffered=True) as cursor:
        for table in ('recurso', 'bien_material'):
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            if cursor.fetchone()[0]:
                raise ValueError('La base destino ya tiene recursos o bienes. Usa una base MySQL vacía.')
        cursor.execute('DELETE FROM categoria_recurso')
        columns = {
            'categoria_recurso': ('idCategoria', 'nombre', 'descripcion'),
            'recurso': ('idRecurso', 'nombre', 'tipo', 'marca', 'modelo', 'descripcion', 'idCategoriaRef'),
            'bien_material': ('idBien', 'idRecursoRef', 'codigoInventario', 'numeroSerie', 'fechaAdquisicion', 'estado', 'ubicacion'),
        }
        for table, names in columns.items():
            if data[table]:
                cursor.executemany(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(['%s'] * len(names))})",
                                   [tuple(row[name] for name in names) for row in data[table]])
        # El contexto confirma todo junto; IDs, fechas y series históricas se conservan.
    return {table: len(rows) for table, rows in data.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Importar SQLite a MySQL sin modificar el archivo original')
    parser.add_argument('archivo', type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    try:
        print('Importación completada:', migrar(args.archivo, load_config(args.config)))
    except Exception as exc:
        raise SystemExit(f'No se completó la importación: {exc}') from None
