from soporte_mysql import crear_base_pruebas, crear_app_pruebas


def preparar_base_prestamos(self):
    from werkzeug.security import generate_password_hash

    crear_base_pruebas(self)
    personas = [('98000001', 'Admin'), ('98000002', 'Encargado'), ('99000001', 'Responsable'),
                ('99000002', 'Integrante'), ('99000003', 'Otra persona')]
    self.c.executemany('INSERT INTO persona(dni,nombres,apellidos,correo) VALUES(%s,%s,%s,%s)',
                      [(dni, nombre, 'Prueba', dni + '@ejemplo.com') for dni, nombre in personas])
    self.c.executemany('INSERT INTO administrativo(dni,codigo_empleado,area) VALUES(%s,%s,%s)',
                      [(dni, dni, 'Préstamos') for dni, _ in personas[:2]])
    self.c.executemany('INSERT INTO estudiante(dni,cui) VALUES(%s,%s)',
                      [(dni, dni) for dni, _ in personas[2:]])
    roles = ['ADMINISTRADOR', 'ENCARGADO_PRESTAMOS', 'USUARIO', 'USUARIO', 'USUARIO']
    self.clave = 'ClavePrueba2026!'
    clave_hash = generate_password_hash(self.clave, method='scrypt')
    self.c.executemany('''INSERT INTO usuario_sistema(id_usuario,dni_persona,nombre_usuario,contrasena_hash,rol)
        VALUES(%s,%s,%s,%s,%s)''', [(i, dni, 'cuenta' + str(i), clave_hash, rol)
            for i, ((dni, _), rol) in enumerate(zip(personas, roles), 1)])
    permisos = [(rol, permiso) for rol in set(roles)
                for permiso in ('PRESTAMOS_PROPIOS_CONSULTAR',)]
    permisos += [(rol, 'PRESTAMOS_GESTIONAR') for rol in roles[:2]]
    self.c.executemany('INSERT INTO rol_permiso(rol,permiso) VALUES(%s,%s)', permisos)
    self.c.execute("INSERT INTO categoria_recurso(id_categoria,nombre) VALUES(1,'Libros')")
    self.c.execute("INSERT INTO recurso(id_recurso,id_categoria,nombre) VALUES(1,1,'Libro de práctica')")
    self.c.execute("INSERT INTO bien_material(id_bien,id_recurso,codigo_inventario,estado) VALUES(1,1,'LIB-001','PRESTADO')")
    self.c.execute("INSERT INTO politica_prestamo(id_politica,tipo_persona,id_categoria,plazo_maximo,unidad_plazo) VALUES(1,'ESTUDIANTE',1,2,'DIAS')")
    self.c.execute("INSERT INTO configuracion_general VALUES(1,'08:00','16:00',2,'DIAS',24,'HORAS')")
    self.c.execute("""INSERT INTO prestamo(id_prestamo,dni_persona,dni_encargado,tipo_prestamo,fecha_solicitud,fecha_entrega)
        VALUES(1,'99000001','98000002','GRUPAL',UTC_TIMESTAMP(),UTC_TIMESTAMP())""")
    self.c.execute("INSERT INTO participante_prestamo(id_prestamo,dni_persona,responsable) VALUES(1,'99000001',TRUE),(1,'99000002',FALSE)")
    self.c.execute("""INSERT INTO detalle_prestamo(id_detalle,id_prestamo,id_bien,id_politica,fecha_limite_devolucion)
        VALUES(1,1,1,1,DATE_FORMAT(DATE_ADD(UTC_TIMESTAMP(),INTERVAL 1 DAY),'%Y-%m-%d %H:%i:00'))""")
    crear_app_pruebas(self)
