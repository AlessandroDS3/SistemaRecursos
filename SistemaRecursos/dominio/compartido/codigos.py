"""Códigos de dominio compatibles con cadenas en formularios y consultas."""

from enum import Enum


class Codigo(str, Enum):
    def __str__(self) -> str:
        return self.value
