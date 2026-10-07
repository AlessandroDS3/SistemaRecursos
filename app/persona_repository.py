from dataclasses import asdict
import mysql.connector
from .repository import RecursoMySQLRepository
from .personas import CAMPOS
from .errors import ConflictError

TABLAS = {'ESTUDIANTE': 'estudiante', 'DOCENTE': 'docente', 'ADMINISTRATIVO': 'administrativo'}

class PersonaMySQLRepository(RecursoMySQLRepository):
    def crear_persona(self, persona):
        with self.connection() as conn, conn.cursor() as cursor:
            try:
                cursor.execute('''INSERT INTO persona
                    (nombres,apellidos,documentoIdentidad,correo,telefono,tipo,estado)
                    VALUES (%(nombres)s,%(apellidos)s,%(documentoIdentidad)s,%(correo)s,
                            %(telefono)s,%(tipo)s,%(estado)s)''',
                    {k:v for k,v in asdict(persona).items() if k != 'detalles'})
                pid = cursor.lastrowid
                campos = CAMPOS[persona.tipo]
                cursor.execute(f"INSERT INTO {TABLAS[persona.tipo]} (idPersona,{','.join(campos)}) "
                               f"VALUES ({','.join(['%s'] * (len(campos)+1))})",
                               (pid, *(persona.detalles[c] for c in campos)))
                return pid
            except mysql.connector.IntegrityError as exc:
                if exc.errno == 1062:
                    raise ConflictError('El documento o el código institucional ya está registrado.') from None
                raise

    def listar_personas(self):
        with self.connection() as conn, conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT * FROM persona ORDER BY idPersona DESC')
            personas = cursor.fetchall()
            detalles = {}
            for tipo, tabla in TABLAS.items():
                cursor.execute(f'SELECT * FROM {tabla}')
                for row in cursor.fetchall():
                    detalles[row.pop('idPersona')] = row
        for persona in personas:
            persona['fechaRegistro'] = persona['fechaRegistro'].isoformat()
            persona['detalles'] = detalles.get(persona['idPersona'], {})
        return personas
