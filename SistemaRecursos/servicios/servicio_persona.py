from __future__ import annotations
from dominio.gestion_personas_usuarios.persona import Persona
from dominio.resultados_consulta import ResultadoPersonas
from dominio.gestion_personas_usuarios.i_repositorio_persona import IRepositorioPersona
from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from servicios.validacion_identificadores import identificador
from dominio.gestion_personas_usuarios.fabrica_persona import FabricaPersona


class ServicioAplicacionPersona:
    def __init__(self, repositorio_personas: IRepositorioPersona):
        self.repositorio: IRepositorioPersona = repositorio_personas

    def registrar_persona(self, datos) -> Persona:
        datos = dict(datos)
        datos["estado"] = "ACTIVA"
        return self.repositorio.registrar_persona(FabricaPersona.construir(datos))

    def consultar_persona(self, dni) -> Persona:
        persona = self.repositorio.consultar_persona(validar_dni(dni))
        if persona is None:
            raise LookupError("No se encontró la persona.")
        return persona

    def consultar_personas(self, filtros, incluir_cuenta=False) -> ResultadoPersonas:
        filtros = dict(filtros or {})
        termino = filtros.get("q", "")
        if not isinstance(termino, str) or len(termino) > 120:
            raise ValueError("La búsqueda admite hasta 120 caracteres.")
        filtros["q"] = termino.strip()
        filtros["pagina"] = identificador(filtros.get("pagina", 1))
        if filtros["q"] and not any(len(p) >= 2 for p in filtros["q"].split()):
            return {
                "personas": [], "resumen": {"total": 0, "activas": 0, "inactivas": 0},
                "pagina": 1, "paginas": 1, "aviso": "Escribe al menos dos caracteres para buscar.",
            }
        if filtros.get("tipo", "") not in {"", "ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO"}:
            raise ValueError("Selecciona un tipo de persona válido.")
        if filtros.get("estado", "") not in {"", "ACTIVA", "INACTIVA"}:
            raise ValueError("Selecciona un estado válido.")
        cuentas_validas = {"", "CON_ACCESO", "SIN_CUENTA", "ACCESO_INACTIVO"}
        if not incluir_cuenta or filtros.get("cuenta", "") not in cuentas_validas:
            filtros["cuenta"] = ""
        return self.repositorio.consultar_personas(filtros)

    def actualizar_persona(self, datos, dni_actual, id_usuario_actor=None) -> Persona:
        id_usuario_actor = identificador(id_usuario_actor) if id_usuario_actor is not None else None
        actual = self.consultar_persona(dni_actual)
        if datos.get("tipo") != actual.tipo:
            raise ValueError("No se puede cambiar el tipo de una persona registrada.")
        datos = dict(datos)
        datos.setdefault("estado", actual.estado)
        for campo in ("codigo_docente", "departamento_academico", "facultad", "escuela_profesional", "codigo_empleado", "area"):
            datos.setdefault(campo, getattr(actual, campo, None))
        return self.repositorio.actualizar_persona(
            FabricaPersona.construir(datos), dni_actual=actual.dni,
            id_usuario_actor=id_usuario_actor, version=datos.get("version"),
        )

    def desactivar_persona(self, dni, id_usuario_actor=None) -> None:
        id_usuario_actor = identificador(id_usuario_actor) if id_usuario_actor is not None else None
        persona = self.consultar_persona(dni)
        self.repositorio.desactivar_persona(persona.dni, id_usuario_actor=id_usuario_actor)
