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
    def consultar(self, documento, bloquear=False):
        return self.consultar_sql(
            CONSULTA + ' WHERE p.dni=%s' + (' FOR UPDATE' if bloquear else ''),
            (documento,),
            una=True,
        )

    def listar(self, filtros):
        condiciones, parametros = [], []
        if filtros.get('q'):
            condiciones.append(
                "(p.dni LIKE %s OR p.nombres LIKE %s OR p.apellidos LIKE %s OR e.cui LIKE %s)"
            )
            parametros.extend([f"%{filtros['q']}%"] * 4)
        if filtros.get('estado'):
            condiciones.append('p.estado=%s')
            parametros.append(filtros['estado'])
        sql = CONSULTA + (' WHERE ' + ' AND '.join(condiciones) if condiciones else '')
        total = self.consultar_sql(
            'SELECT COUNT(*) AS total FROM (' + sql + ') personas', parametros, una=True
        )['total']
        pagina = min(filtros.get('pagina', 1), max(1, (total + 24) // 25))
        filas = self.consultar_sql(
            sql + ' ORDER BY p.apellidos,p.nombres,p.dni LIMIT 25 OFFSET %s',
            (*parametros, (pagina - 1) * 25),
        )
        return dict(personas=filas, total=total, pagina=pagina, paginas=max(1, (total + 24) // 25))

    def guardar(self, persona, documento_anterior=None):
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

    def cuentas_bloqueadas(self):
        return cargar_cuentas_bloqueadas(self)

    def desactivar(self, documento):
        self.ejecutar("UPDATE persona SET estado='INACTIVA' WHERE dni=%s", (documento,))

    def buscar(self, termino):
        return self.consultar_sql(
            CONSULTA + ' WHERE p.dni LIKE %s OR p.apellidos LIKE %s OR e.cui LIKE %s LIMIT 20',
            (f'%{termino}%',) * 3,
        )
