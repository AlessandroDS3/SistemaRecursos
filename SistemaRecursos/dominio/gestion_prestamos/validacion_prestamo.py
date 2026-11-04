from dominio.gestion_personas_usuarios.validacion_persona import validar_dni
from dominio.gestion_recursos.validacion_recurso import entero
from dominio.gestion_personas_usuarios.estudiante import tiene_matricula_vigente


class ConflictoPrestamoError(ValueError):
    pass


def validar_persona(persona):
    if persona.get("estado") != "ACTIVA":
        raise ValueError("La persona seleccionada está inactiva.")
    if persona.get("tipo") not in {"ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO"}:
        raise ValueError("La persona no tiene un tipo institucional registrado.")
    if persona["tipo"] == "ESTUDIANTE" and not tiene_matricula_vigente(
        persona.get("estado_matricula")
    ):
        raise ValueError(
            "El estudiante debe tener matrícula vigente para participar en un préstamo."
        )


def lista_ids(valores, campo):
    if not isinstance(valores, (list, tuple)) or len(valores) > 100:
        raise ValueError(f"{campo}: selecciona hasta 100 elementos.")
    ids = [entero(v, campo) for v in valores]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{campo}: no se permiten elementos repetidos.")
    return ids


def lista_dnis(valores):
    if not isinstance(valores, (list, tuple)) or len(valores) > 100:
        raise ValueError("Selecciona hasta 100 participantes.")
    dnis = [validar_dni(valor) for valor in valores]
    if len(set(dnis)) != len(dnis):
        raise ValueError("No se permiten participantes repetidos.")
    return dnis
