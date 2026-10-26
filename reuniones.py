"""Reuniones guardadas: un archivo Markdown por reunión, solo en este computador.

El archivo se reescribe completo (de forma atómica) después de cada frase, así un
cierre inesperado no pierde lo transcrito hasta ese momento. El audio nunca se guarda.
"""
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TITULO_POR_DEFECTO = "Reunión"


@dataclass
class Turno:
    segundo: float      # desde el inicio de la reunión
    hablante: str
    texto: str


def hhmmss(segundos: float) -> str:
    s = max(0, int(segundos))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _limpiar_titulo(titulo: str) -> str:
    """Deja solo lo que sirve en un nombre de archivo (letras con tilde incluidas)."""
    limpio = re.sub(r"[^\w\- ]+", "", titulo).strip()
    return re.sub(r"\s+", " ", limpio)[:60].strip() or TITULO_POR_DEFECTO


def _ruta_libre(carpeta: Path, inicio: datetime, titulo: str) -> Path:
    base = f"{inicio:%Y-%m-%d %H%M} - {_limpiar_titulo(titulo)}"
    ruta, n = carpeta / f"{base}.md", 2
    while ruta.exists():
        ruta, n = carpeta / f"{base} ({n}).md", n + 1
    return ruta


class Reunion:
    def __init__(self, carpeta: Path, titulo: str = "", inicio: datetime | None = None):
        self.carpeta = Path(carpeta)
        self.titulo = titulo.strip() or TITULO_POR_DEFECTO
        self.inicio = inicio or datetime.now()
        self.fin: datetime | None = None
        self.turnos: list[Turno] = []
        self.ruta = _ruta_libre(self.carpeta, self.inicio, self.titulo)

    def agregar(self, hablante: str, texto: str, momento: datetime | None = None) -> Turno:
        momento = momento or datetime.now()
        turno = Turno((momento - self.inicio).total_seconds(), hablante, texto.strip())
        self.turnos.append(turno)
        self.guardar()
        return turno

    def terminar(self, momento: datetime | None = None) -> Path | None:
        """Cierra la reunión. Sin frases no deja archivo y devuelve None."""
        self.fin = momento or datetime.now()
        if not self.turnos:
            return None
        return self.guardar()

    def markdown(self) -> str:
        hablantes = list(dict.fromkeys(t.hablante for t in self.turnos))
        duracion = hhmmss((self.fin - self.inicio).total_seconds()) if self.fin else "en curso"
        lineas = [
            f"# {self.titulo}",
            "",
            f"- Fecha: {self.inicio:%Y-%m-%d %H:%M}",
            f"- Duración: {duracion}",
            f"- Participantes: {', '.join(hablantes) or '—'}",
            "",
            "## Transcripción",
            "",
        ]
        for t in self.turnos:
            lineas += [f"**[{hhmmss(t.segundo)}] {t.hablante}:** {t.texto}", ""]
        return "\n".join(lineas)

    def guardar(self) -> Path:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        fd, temporal = tempfile.mkstemp(dir=self.carpeta, prefix=".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self.markdown())
            os.replace(temporal, self.ruta)
        except BaseException:
            Path(temporal).unlink(missing_ok=True)
            raise
        return self.ruta


def listar(carpeta: Path) -> list[Path]:
    """Reuniones guardadas, la más reciente primero (el nombre parte con la fecha)."""
    if not Path(carpeta).is_dir():
        return []
    return sorted(Path(carpeta).glob("*.md"), key=lambda p: p.name, reverse=True)
