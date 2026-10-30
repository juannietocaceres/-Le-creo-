"""Modelos pydantic: contrato de salida del LLM y resultado completo del agente."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class Tactica(BaseModel):
    id: str
    evidencia: str


class ContratoSalida(BaseModel):
    fuera_de_alcance: bool = False
    entidad_suplantada: str | None = None
    tacticas: list[Tactica] = []
    pide: list[str] = []
    enlaces: list[str] = []
    telefonos: list[str] = []
    explicacion: str = ""
    que_hacer: str = ""

    @field_validator("pide", mode="before")
    @classmethod
    def _pide_permitidos(cls, v: list[str]) -> list[str]:
        permitidos = {"clave", "codigo", "transferencia", "datos_personales", "clic"}
        return [x for x in v if x in permitidos]


class LlamadaHerramienta(BaseModel):
    nombre: str
    parametros: dict[str, Any]
    resultado: Any
    latencia_ms: int


class ResultadoAgente(BaseModel):
    contrato: ContratoSalida | None = None
    ok: bool = False
    error: str | None = None          # timeout | iteraciones | presupuesto_agotado | contrato_invalido | proveedor
    detalle: str | None = None        # mensaje legible del error, sin stack trace
    truncado: bool = False
    herramientas: list[LlamadaHerramienta] = []
    iteraciones: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    latencia_ms: int = 0
    proveedor_usado: str = ""
    modelo_usado: str = ""
