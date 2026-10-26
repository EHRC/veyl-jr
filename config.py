"""Configuración de Veyl Jr. Todo se lee desde el archivo .env junto al código
(copia .env.example). Una variable de entorno ya definida gana sobre el .env.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

CARPETA_POR_DEFECTO = Path.home() / "Documents" / "Veyl Jr" / "Reuniones"


def _bool(valor: str | None, defecto: bool = False) -> bool:
    if valor is None or valor.strip() == "":
        return defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes"}


def _lista(valor: str | None) -> list[str]:
    return [x.strip() for x in (valor or "").split(",") if x.strip()]


@dataclass
class Config:
    assemblyai_key: str
    modelo_stt: str
    url_stt: str
    dispositivo_otros: str
    dispositivo_mic: str
    transcribir_mic: bool
    palabras_clave: list[str]
    carpeta_reuniones: Path


def cargar_config() -> Config:
    carpeta = os.getenv("CARPETA_REUNIONES", "").strip()
    return Config(
        assemblyai_key=os.getenv("ASSEMBLYAI_API_KEY", "").strip(),
        modelo_stt=os.getenv("STT_MODEL", "universal-streaming-multilingual"),
        url_stt=os.getenv("STT_URL", "wss://streaming.assemblyai.com/v3/ws"),
        dispositivo_otros=os.getenv("DISPOSITIVO_OTROS", "BlackHole"),
        dispositivo_mic=os.getenv("DISPOSITIVO_MIC", ""),
        transcribir_mic=_bool(os.getenv("TRANSCRIBIR_MIC"), True),
        palabras_clave=_lista(os.getenv("PALABRAS_CLAVE")),
        carpeta_reuniones=Path(carpeta).expanduser() if carpeta else CARPETA_POR_DEFECTO,
    )
