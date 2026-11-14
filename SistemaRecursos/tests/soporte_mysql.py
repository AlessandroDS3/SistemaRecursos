"""Bases efímeras por prueba; los escenarios no cargan datos_prueba.sql."""

import os
from pathlib import Path
from uuid import uuid4

import mysql.connector

from app import create_app
from repositorio.conexion_mysql import MySQLConnection

SQL = Path(__file__).resolve().parents[1] / 'sql'


def ejecutar_sql(cursor, contenido):
    cursor.execute(contenido)
    while True:
        if cursor.with_rows:
            cursor.fetchall()
        if not cursor.nextset():
            break


def crear_base_pruebas(caso):
    cfg = dict(
        host='127.0.0.1',
        port=int(os.environ['TEST_MYSQL_PORT']),
        user=os.environ.get('TEST_MYSQL_USER', 'root'),
        password=os.environ.get('TEST_MYSQL_PASSWORD', ''),
        use_pure=True,
        connection_timeout=5,
    )
    caso.nombre = 'test_recursos_' + uuid4().hex
    caso.cn = mysql.connector.connect(**cfg)
    caso.addCleanup(caso.cn.close)
    caso.c = caso.cn.cursor(buffered=True)
    caso.addCleanup(caso.c.close)
    caso.addCleanup(caso.c.execute, f'DROP DATABASE IF EXISTS {caso.nombre}')
    ejecutar_sql(
        caso.c,
        (SQL / 'schema.sql')
        .read_text(encoding='utf-8-sig')
        .replace('prestamos_escuela', caso.nombre),
    )
    caso.cn.commit()
    caso.db = MySQLConnection(dict(cfg, database=caso.nombre))


def crear_app_pruebas(caso):
    caso.cn.commit()
    caso.app = create_app(
        {'TESTING': True, 'MYSQL_CONFIG': caso.db.config, 'INICIAR_PROCESADOR_VENCIMIENTOS': False}
    )


def preparar_personas(caso):
    from werkzeug.security import generate_password_hash

    c = caso.c
    personas = [
        ('98000001', 'Administrador'),
        ('98000002', 'Encargado'),
        ('02167885', 'Usuario'),
        ('99000001', 'Estudiante uno'),
        ('99000002', 'Estudiante dos'),
        ('99000003', 'Estudiante tres'),
        ('99000011', 'Sin cuenta'),
        ('99000012', 'Edición concurrente'),
    ]
    c.executemany(
        'INSERT INTO persona(dni,nombres,apellidos,correo) VALUES(%s,%s,%s,%s)',
        [(dni, nombre, 'Prueba', dni + '@ejemplo.com') for dni, nombre in personas],
    )
    c.executemany(
        'INSERT INTO administrativo(dni,codigo_empleado,area) VALUES(%s,%s,%s)',
        [(dni, dni, 'Préstamos') for dni, _ in personas[:2]],
    )
    c.executemany(
        'INSERT INTO estudiante(dni,cui) VALUES(%s,%s)', [(dni, dni) for dni, _ in personas[2:]]
    )
    permisos_usuario = [
        'CATALOGO_CONSULTAR',
        'PRESTAMOS_PROPIOS_CONSULTAR',
        'RESERVAS_PROPIAS_GESTIONAR',
    ]
    permisos_encargado = permisos_usuario + [
        'PERSONAS_CONSULTAR',
        'PERSONAS_GESTIONAR',
        'PRESTAMOS_GESTIONAR',
        'REPORTES_CONSULTAR',
    ]
    permisos_admin = permisos_encargado + [
        'USUARIOS_GESTIONAR',
        'ROLES_CONSULTAR',
        'ROLES_GESTIONAR',
        'RECURSOS_GESTIONAR',
        'POLITICAS_GESTIONAR',
    ]
    for rol, permisos in [
        ('USUARIO', permisos_usuario),
        ('ENCARGADO_PRESTAMOS', permisos_encargado),
        ('ADMINISTRADOR', permisos_admin),
    ]:
        c.executemany(
            'INSERT INTO rol_permiso VALUES(%s,%s)', [(rol, permiso) for permiso in permisos]
        )
    cuentas = [
        (1, '98000001', 'admin', 'AdminPrueba2026!', 'ADMINISTRADOR'),
        (2, '98000002', 'encargado1', 'EncargadoPrueba2026!', 'ENCARGADO_PRESTAMOS'),
        (3, '02167885', 'usuario1', 'UsuarioPrueba2026!', 'USUARIO'),
    ]
    c.executemany(
        """INSERT INTO usuario_sistema(id_usuario,dni_persona,nombre_usuario,contrasena_hash,rol)
        VALUES(%s,%s,%s,%s,%s)""",
        [
            (i, dni, usuario, generate_password_hash(clave), rol)
            for i, dni, usuario, clave, rol in cuentas
        ],
    )


def preparar_catalogo(caso):
    c = caso.c
    c.execute("INSERT INTO categoria_recurso(id_categoria,nombre) VALUES(1,'Equipos')")
    c.execute(
        "INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(1,1,'Equipo de práctica'),(2,1,'Equipo para reservas')"
    )
    c.execute(
        "INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario,estado) VALUES(1,1,'INV-1','PRESTADO'),(2,1,'INV-2','DISPONIBLE'),(3,1,'INV-3','DISPONIBLE')"
    )
    c.execute(
        "INSERT INTO politica_prestamo(id_politica,tipo_persona,id_categoria,plazo_maximo,unidad_plazo) VALUES(24,'ESTUDIANTE',1,2,'DIAS')"
    )
    c.execute("INSERT INTO limite_articulos_prestamo VALUES('ESTUDIANTE',4)")
    c.execute("INSERT INTO configuracion_general VALUES(1,'08:00','16:00',2,'DIAS',24,'HORAS')")


def preparar_dos_prestamos(caso):
    """Un préstamo vencido y otro devuelto; sin sanciones ni incidencias iniciales."""
    c = caso.c
    c.execute(
        """INSERT INTO prestamo(id_prestamo,dni_persona,dni_encargado,fecha_solicitud,fecha_entrega,estado)
        VALUES(1,'02167885','98000002','2026-10-30 16:38','2026-10-30 16:38','ACTIVO'),
              (2,'99000003','98000002','2026-10-29 14:00','2026-10-29 14:00','DEVUELTO')"""
    )
    c.execute(
        """INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion,
                     fecha_devolucion,dni_encargado_devolucion,condicion_devolucion)
        VALUES(1,1,1,24,DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 DAY),NULL,NULL,NULL),
              (2,2,3,24,'2026-10-31 14:00','2026-10-30 14:00','98000002','BUENO')"""
    )
    c.execute(
        """INSERT INTO historial_estado(entidad,id_entidad,estado_anterior,estado_nuevo,fecha,dni_responsable)
        VALUES('PRESTAMO',1,NULL,'ACTIVO','2026-10-30 16:38','98000002'),
              ('PRESTAMO',2,NULL,'ACTIVO','2026-10-29 14:00','98000002'),
              ('PRESTAMO',2,'ACTIVO','DEVUELTO','2026-10-30 14:00','98000002'),
              ('BIEN_MATERIAL',1,'DISPONIBLE','PRESTADO','2026-10-30 16:38','98000002')"""
    )
    c.execute(
        """INSERT INTO reserva(id_reserva,dni_persona,id_recurso,fecha_solicitud,fecha_requerida,fecha_limite_vencimiento)
        VALUES(1,'02167885',1,UTC_TIMESTAMP(),UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY))"""
    )


def preparar_base_integracion(caso, prestamos=False, catalogo=True):
    crear_base_pruebas(caso)
    preparar_personas(caso)
    if catalogo:
        preparar_catalogo(caso)
    if prestamos:
        preparar_dos_prestamos(caso)
    crear_app_pruebas(caso)
