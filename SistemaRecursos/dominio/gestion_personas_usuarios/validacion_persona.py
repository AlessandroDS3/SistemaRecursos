import re

TIPOS = ("ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO")
CORREO = re.compile(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+")
CAMPOS_TIPO = {
    "DOCENTE": (
        ("codigo_docente", "Código de docente", 20),
        ("departamento_academico", "Departamento académico", 100),
        ("facultad", "Facultad", 100),
        ("escuela_profesional", "Escuela profesional", 100),
    ),
    "ADMINISTRATIVO": (
        ("codigo_empleado", "Código de empleado", 20),
        ("area", "Área", 100),
    ),
}


class ValidacionPersonaError(ValueError):
    def __init__(self, errores):
        self.errores = errores
        super().__init__(next(iter(errores.values())))


def _validar_texto(errores, datos, campo, etiqueta, limite):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        errores[campo] = f"{etiqueta}: este campo es obligatorio."
    elif len(valor.strip()) > limite:
        errores[campo] = f"{etiqueta}: máximo {limite} caracteres."


def validar_datos_persona(datos):
    errores = {}
    tipo = datos.get("tipo")

    try:
        validar_dni(datos.get("dni"))
    except ValueError as error:
        errores["dni"] = str(error)
    if tipo == "ESTUDIANTE":
        cui = datos.get("cui")
        if not isinstance(cui, str) or not re.fullmatch(r"[0-9]{8}", cui):
            errores["cui"] = "El CUI debe tener exactamente 8 dígitos."

    for campo, etiqueta, limite in CAMPOS_TIPO.get(tipo, ()):
        _validar_texto(errores, datos, campo, etiqueta, limite)

    _validar_texto(errores, datos, "nombres", "Nombres", 100)
    _validar_texto(errores, datos, "apellidos", "Apellidos", 100)

    correo = datos.get("correo")
    if not isinstance(correo, str) or len(correo.strip()) > 120 or not CORREO.fullmatch(correo.strip()):
        errores["correo"] = "Ingresa un correo válido, por ejemplo nombre@dominio.com."

    telefono = datos.get("telefono", "")
    if not isinstance(telefono, str) or len(telefono) > 20:
        errores["telefono"] = "El teléfono admite hasta 20 caracteres."

    if tipo not in TIPOS:
        errores["tipo"] = "Selecciona un tipo de persona."

    if tipo == "ESTUDIANTE":
        if datos.get("estado_matricula") not in ("vigente", "no_vigente"):
            errores["estado_matricula"] = "Selecciona Vigente o No vigente."

        ciclo = datos.get("ciclo")
        if ciclo not in (None, ""):
            texto = str(ciclo)
            if not re.fullmatch(r"[0-9]+", texto) or not 1 <= int(texto) <= 2147483647:
                errores["ciclo"] = "El ciclo debe ser un entero positivo o quedar vacío."

        semestre = datos.get("semestre_academico")
        if semestre is not None and (not isinstance(semestre, str) or len(semestre.strip()) > 10):
            errores["semestre_academico"] = "El semestre admite hasta 10 caracteres."

    if errores:
        raise ValidacionPersonaError(errores)

def validar_dni(valor):
    if not isinstance(valor, str) or not re.fullmatch(r"[0-9]{8}", valor):
        raise ValueError("El DNI debe tener exactamente 8 dígitos.")
    return valor
