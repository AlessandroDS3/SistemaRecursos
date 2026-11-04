from dominio.gestion_personas_usuarios.estudiante import Estudiante
from dominio.gestion_personas_usuarios.docente import Docente
from dominio.gestion_personas_usuarios.administrativo import Administrativo
from dominio.gestion_personas_usuarios.validacion_persona import validar_datos_persona


class FabricaPersona:
    @classmethod
    def construir(cls, datos):
        datos = dict(datos)
        if "dni" not in datos and "documento_identidad" in datos:
            datos["dni"] = datos["documento_identidad"]
        validar_datos_persona(datos)

        if datos["tipo"] == "ESTUDIANTE":
            ciclo = datos.get("ciclo")
            if ciclo in (None, ""):
                ciclo = None
            else:
                ciclo = int(ciclo)
            return Estudiante(
                dni=datos["dni"],
                nombres=datos["nombres"],
                apellidos=datos["apellidos"],
                correo=datos["correo"],
                telefono=datos.get("telefono", ""),
                cui=datos["cui"],
                estado=datos.get("estado", "ACTIVA"),
                estado_matricula=datos["estado_matricula"],
                ciclo=ciclo,
                semestre_academico=datos.get("semestre_academico") or None,
            )

        if datos["tipo"] == "DOCENTE":
            return Docente(
                dni=datos["dni"],
                nombres=datos["nombres"],
                apellidos=datos["apellidos"],
                correo=datos["correo"],
                telefono=datos.get("telefono", ""),
                estado=datos.get("estado", "ACTIVA"),
                codigo_docente=datos["codigo_docente"],
                departamento_academico=datos["departamento_academico"],
                facultad=datos["facultad"],
                escuela_profesional=datos["escuela_profesional"],
            )

        return Administrativo(
            dni=datos["dni"],
            nombres=datos["nombres"],
            apellidos=datos["apellidos"],
            correo=datos["correo"],
            telefono=datos.get("telefono", ""),
            estado=datos.get("estado", "ACTIVA"),
            codigo_empleado=datos["codigo_empleado"],
            area=datos["area"],
        )
