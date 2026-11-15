from dominio.gestion_personas_usuarios.persona import CAMPOS_TIPO
from repositorio.base_sql import RepositorioSQL
from repositorio.repositorio_cuenta_sql import cargar_cuentas_bloqueadas

TABLAS_TIPO = {'ESTUDIANTE': 'estudiante', 'DOCENTE': 'docente', 'ADMINISTRATIVO': 'administrativo'}
CONSULTA = '''SELECT p.*,e.cui,e.ciclo,e.estado_matricula,d.codigo_docente,d.departamento_academico,
    d.facultad,d.escuela_profesional,a.codigo_empleado,a.area,
    CASE WHEN e.dni IS NOT NULL THEN 'ESTUDIANTE' WHEN d.dni IS NOT NULL THEN 'DOCENTE'
         WHEN a.dni IS NOT NULL THEN 'ADMINISTRATIVO' END AS tipo
    FROM persona p LEFT JOIN estudiante e ON e.dni=p.dni LEFT JOIN docente d ON d.dni=p.dni
    LEFT JOIN administrativo a ON a.dni=p.dni'''


class RepositorioPersonaSQL(RepositorioSQL):
    def consultar_persona(self, documento, bloquear=False):
        return self.consultar_sql(
            CONSULTA + ' WHERE p.dni=%s' + (' FOR UPDATE' if bloquear else ''),
            (documento,),
            una=True,
        )

    def consultar_personas(self, filtros):
        condiciones, parametros = [], []
        if filtros.get('q'):
            condiciones.append(
                "(listado.dni LIKE %s OR listado.nombres LIKE %s OR listado.apellidos LIKE %s OR listado.cui LIKE %s)"
            )
            parametros.extend([f"%{filtros['q']}%"] * 4)
        if filtros.get('estado'):
            condiciones.append('listado.estado=%s')
            parametros.append(filtros['estado'])
        if filtros.get('tipo'):
            condiciones.append('listado.tipo=%s')
            parametros.append(filtros['tipo'])
        if filtros.get('cuenta'):
            condiciones.append(
                'u.id_usuario IS ' + ('NOT NULL' if filtros['cuenta'] == 'CON_CUENTA' else 'NULL')
            )
        sql = (
            'SELECT listado.*,u.id_usuario,u.estado_cuenta FROM ('
            + CONSULTA
            + ') listado LEFT JOIN usuario_sistema u ON u.dni_persona=listado.dni'
            + (' WHERE ' + ' AND '.join(condiciones) if condiciones else '')
        )
        resumen = self.consultar_sql(
            "SELECT COUNT(*) AS total,COALESCE(SUM(estado='ACTIVA'),0) AS activas,"
            "COALESCE(SUM(estado='INACTIVA'),0) AS inactivas FROM (" + sql + ') personas',
            parametros,
            una=True,
        )
        total = resumen['total']
        pagina = min(filtros.get('pagina', 1), max(1, (total + 24) // 25))
        filas = self.consultar_sql(
            sql + ' ORDER BY listado.apellidos,listado.nombres,listado.dni LIMIT 25 OFFSET %s',
            (*parametros, (pagina - 1) * 25),
        )
        return dict(
            personas=filas,
            total=total,
            pagina=pagina,
            paginas=max(1, (total + 24) // 25),
            activas=int(resumen['activas']),
            inactivas=int(resumen['inactivas']),
        )

    def guardar_persona(self, persona, documento_anterior=None):
        datos = persona.datos()
        comunes = {
            k: datos[k] for k in ('dni', 'nombres', 'apellidos', 'telefono', 'correo', 'estado')
        }
        especificos = {k: datos[k] for k in CAMPOS_TIPO[persona.tipo]}
        tabla = TABLAS_TIPO[persona.tipo]
        if documento_anterior is None:
            self.insertar('persona', comunes)
            self.insertar(tabla, dict(dni=persona.dni, **especificos))
        else:
            self.ejecutar(
                'UPDATE persona SET ' + ','.join(k + '=%s' for k in comunes) + ' WHERE dni=%s',
                (*comunes.values(), documento_anterior),
            )
            self.ejecutar(
                'UPDATE '
                + tabla
                + ' SET '
                + ','.join(k + '=%s' for k in especificos)
                + ' WHERE dni=%s',
                (*especificos.values(), persona.dni),
            )

    def consultar_cuentas_bloqueadas(self):
        return cargar_cuentas_bloqueadas(self)

    def desactivar_persona(self, documento):
        self.ejecutar("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (documento,))

    def buscar_personas(self, termino):
        return self.consultar_sql(
            CONSULTA + ' WHERE p.dni LIKE %s OR p.apellidos LIKE %s OR e.cui LIKE %s LIMIT 20',
            (f'%{termino}%',) * 3,
        )
