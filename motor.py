"""Motores de transcripción: audio real (AssemblyAI) o demo con frases de ejemplo.

Los dos llaman a on_parcial(hablante, texto), on_turno(hablante, texto) y
on_estado(mensaje) desde un hilo propio; quien los usa decide cómo llevarlo a su hilo.
"""
import asyncio
import threading
from typing import Callable

from config import Config

AVISO = ("Avisa a los participantes que vas a transcribir la reunión "
         "(en Chile lo exige la Ley 21.719).")

FRASES_DEMO = [
    ("Otros", "Hola, ¿me escuchan bien?"),
    ("Yo", "Sí, perfecto. Partamos con la revisión del avance."),
    ("Otros", "Terminamos la carga de datos y quedó pendiente la validación con finanzas."),
    ("Yo", "Ok, entonces la próxima semana revisamos la validación."),
    ("Otros", "De acuerdo, yo envío el resumen por correo."),
]


class MotorAudio:
    """Captura y transcribe en un hilo aparte, con su propio loop de asyncio."""

    def __init__(self, cfg: Config, on_parcial: Callable[[str, str], None],
                 on_turno: Callable[[str, str], None], on_estado: Callable[[str], None]):
        self.cfg = cfg
        self.on_parcial, self.on_turno, self.on_estado = on_parcial, on_turno, on_estado
        self.loop: asyncio.AbstractEventLoop | None = None
        self.detener: asyncio.Event | None = None
        self.hilo: threading.Thread | None = None

    async def _principal(self) -> None:
        from audio import CapturaAudio, buscar_dispositivo
        from stt import transcribir

        self.loop = asyncio.get_running_loop()
        self.detener = asyncio.Event()
        fuentes = [("Otros", self.cfg.dispositivo_otros)]
        if self.cfg.transcribir_mic:
            fuentes.append(("Yo", self.cfg.dispositivo_mic))

        capturas, tareas = [], []
        try:
            for hablante, nombre in fuentes:
                captura = CapturaAudio(buscar_dispositivo(nombre))
                captura.iniciar(self.loop)
                capturas.append(captura)
                self.on_estado(f"{hablante}: {captura.nombre} ({captura.frecuencia} Hz)")
                tareas.append(transcribir(
                    captura, hablante, self.cfg.assemblyai_key, self.cfg.modelo_stt,
                    self.cfg.url_stt, self.cfg.palabras_clave,
                    self.on_parcial, self.on_turno, self.on_estado, self.detener))
            await asyncio.gather(*tareas)
        finally:
            for c in capturas:
                c.detener()

    def _correr(self) -> None:
        try:
            asyncio.run(self._principal())
        except Exception as e:
            self.on_estado(f"Error de audio: {e}")

    def iniciar(self) -> None:
        self.hilo = threading.Thread(target=self._correr, daemon=True)
        self.hilo.start()

    def activo(self) -> bool:
        return self.hilo is not None and self.hilo.is_alive()

    def parar(self, espera: float = 5.0) -> None:
        if self.loop and self.detener:
            self.loop.call_soon_threadsafe(self.detener.set)
        if self.hilo:
            self.hilo.join(timeout=espera)


class MotorDemo:
    """Mismo contrato que MotorAudio, pero con FRASES_DEMO: sirve para probar sin audio ni API."""

    def __init__(self, on_parcial, on_turno, on_estado, pausa: float = 1.5):
        self.on_parcial, self.on_turno, self.on_estado = on_parcial, on_turno, on_estado
        self.pausa = pausa
        self.detener = threading.Event()
        self.hilo: threading.Thread | None = None

    def _correr(self) -> None:
        self.on_estado("Demo: frases de ejemplo, sin audio ni API")
        for hablante, texto in FRASES_DEMO:
            if self.detener.wait(self.pausa / 2):
                return
            self.on_parcial(hablante, texto[: len(texto) // 2])
            if self.detener.wait(self.pausa / 2):
                return
            self.on_turno(hablante, texto)
        self.on_estado("Demo terminada: detén para guardar")

    def iniciar(self) -> None:
        self.hilo = threading.Thread(target=self._correr, daemon=True)
        self.hilo.start()

    def activo(self) -> bool:
        return self.hilo is not None and self.hilo.is_alive()

    def parar(self, espera: float = 2.0) -> None:
        self.detener.set()
        if self.hilo:
            self.hilo.join(timeout=espera)
