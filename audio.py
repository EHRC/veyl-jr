"""Captura de audio local: micrófono (tú) y BlackHole (audio del sistema = los demás).

Se envía a la transcripción como PCM 16-bit mono a la frecuencia nativa del
dispositivo (AssemblyAI acepta 8.000 a 96.000 Hz), así no hay que remuestrear.
"""
import asyncio

import numpy as np


def _sd():
    import sounddevice as sd  # import diferido: requiere PortAudio
    return sd


def listar_dispositivos() -> None:
    sd = _sd()
    defecto = sd.default.device[0]
    print("Dispositivos de entrada disponibles:\n")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            marca = "  <- micrófono por defecto" if i == defecto else ""
            print(f"  [{i}] {d['name']}  ({d['max_input_channels']} canales, "
                  f"{int(d['default_samplerate'])} Hz){marca}")
    print("\nUsa parte del nombre en DISPOSITIVO_OTROS / DISPOSITIVO_MIC del .env")


def buscar_dispositivo(nombre: str) -> int:
    """Devuelve el índice del primer dispositivo de entrada cuyo nombre contiene `nombre`.
    Si `nombre` está vacío, devuelve el micrófono por defecto."""
    sd = _sd()
    if not nombre:
        return sd.default.device[0]
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and nombre.lower() in d["name"].lower():
            return i
    raise RuntimeError(
        f"No encontré un dispositivo de entrada que contenga '{nombre}'. "
        "Revisa la lista con: python main.py --dispositivos"
    )


def a_pcm16(bloque: np.ndarray) -> bytes:
    """float32 [-1, 1] (frames x canales) -> bytes PCM 16-bit little-endian mono."""
    mono = bloque.mean(axis=1) if bloque.ndim == 2 and bloque.shape[1] > 1 else bloque.reshape(-1)
    return (np.clip(mono, -1.0, 1.0) * 32767).astype("<i2").tobytes()


class CapturaAudio:
    """Abre un dispositivo y deja bloques PCM de ~100 ms en una asyncio.Queue."""

    def __init__(self, indice: int, bloque_ms: int = 100):
        sd = _sd()
        info = sd.query_devices(indice)
        self.indice = indice
        self.nombre = info["name"]
        self.frecuencia = int(info["default_samplerate"])
        self.canales = max(1, min(2, int(info["max_input_channels"])))
        self.bloque = int(self.frecuencia * bloque_ms / 1000)
        self.cola: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stream = None

    def _encolar(self, datos: bytes) -> None:
        try:
            self.cola.put_nowait(datos)
        except asyncio.QueueFull:
            pass  # si la red se atrasa, descartamos audio viejo en vez de acumular latencia

    def _callback(self, indata, frames, tiempo, estado) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._encolar, a_pcm16(indata))

    def iniciar(self, loop: asyncio.AbstractEventLoop) -> None:
        sd = _sd()
        self._loop = loop
        self._stream = sd.InputStream(
            device=self.indice, channels=self.canales, samplerate=self.frecuencia,
            blocksize=self.bloque, dtype="float32", callback=self._callback,
        )
        self._stream.start()

    def detener(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
