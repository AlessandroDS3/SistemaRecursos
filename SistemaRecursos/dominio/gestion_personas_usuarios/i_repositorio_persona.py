from __future__ import annotations
from dominio.gestion_personas_usuarios.persona import Persona
from dominio.resultados_consulta import ResultadoPersonas
from typing import Any
from abc import ABC, abstractmethod


class IRepositorioPersona(ABC):
    @abstractmethod
    def registrar_persona(self, persona) -> Persona:
        """Escritura explícita. Devuelve Persona y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def consultar_persona(self, dni) -> Persona | None:
        """Lectura sin escrituras. Devuelve Persona | None; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_personas(self, filtros) -> ResultadoPersonas:
        """Lectura sin escrituras. Devuelve ResultadoPersonas; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def consultar_solicitantes(self, texto, limite=20) -> list[dict[str, Any]]:
        """Lectura sin escrituras. Devuelve list[dict[str, Any]]; None indica ausencia y un listado vacío no es un error."""
        raise NotImplementedError

    @abstractmethod
    def actualizar_persona(self, persona, dni_actual, id_usuario_actor=None) -> Persona:
        """Escritura explícita. Devuelve Persona y propaga errores de validación o integridad."""
        raise NotImplementedError

    @abstractmethod
    def desactivar_persona(self, dni, id_usuario_actor=None) -> None:
        """Escritura explícita. Devuelve None y propaga errores de validación o integridad."""
        raise NotImplementedError
