# CLAUDE.md — Veyl Jr

Instrucciones para Claude (o cualquier agente) que trabaje en este repo. Es **público**: todo lo que se sube lo ve cualquiera.

## Qué es

Versión pública y simple de Veyl: transcribe reuniones en vivo y las guarda en Markdown en el computador del usuario.

```
BlackHole (Otros) + micrófono (Yo) → AssemblyAI streaming → fin de frase → reuniones.Reunion → .md local
```

| Archivo | Responsabilidad |
| --- | --- |
| `main.py` | Modos (`--consola`, `--demo`, `--dispositivos`) y modo consola. |
| `ventana.py` | Ventana PyQt6: título, iniciar/detener, transcripción en vivo, lista de reuniones. `Puente` lleva los eventos del hilo de audio a Qt. |
| `motor.py` | `MotorAudio` (captura + STT en un hilo con asyncio), `MotorDemo` (frases de ejemplo) y el texto del aviso. |
| `reuniones.py` | `Reunion`: un `.md` por reunión, reescrito de forma atómica tras cada frase. `listar`. |
| `audio.py`, `stt.py` | Captura con sounddevice y WebSocket v3 de AssemblyAI (copiados de Veyl, sin palabras clave dinámicas). |
| `config.py` | Lee el `.env` junto al código. |

## Reglas que no se negocian

- **Nada de RAG, embeddings, índices ni llamadas a LLM.** Eso es de Veyl (privado). Si una mejora lo necesita, no va aquí.
- **Nada de material de clientes o de la empresa, rutas personales ni claves** en el código, la documentación ni los commits.
- **Las reuniones solo se guardan en el computador del usuario.** Nunca audio. Nunca subir transcripciones a ningún servicio fuera de AssemblyAI (que transcribe en vivo).
- **El aviso a los participantes (Ley 21.719) se mantiene** antes de la primera grabación.
- Antes de cada commit: `python pruebas/test_reuniones.py` y `python main.py --demo`.
