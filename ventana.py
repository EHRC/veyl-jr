"""Ventana de Veyl Jr: título, iniciar/detener, transcripción en vivo y reuniones guardadas."""
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from config import Config
from motor import AVISO, MotorAudio, MotorDemo
from reuniones import Reunion, hhmmss, listar


class Puente(QObject):
    """Lleva los eventos del hilo de audio al hilo de la ventana."""
    parcial = pyqtSignal(str, str)
    turno = pyqtSignal(str, str)
    estado = pyqtSignal(str)


class Ventana(QWidget):
    def __init__(self, cfg: Config, demo: bool = False):
        super().__init__()
        self.cfg = cfg
        self.demo = demo
        self.motor = None
        self.reunion: Reunion | None = None
        self.avisado = False
        self.puente = Puente()
        self.puente.parcial.connect(self._parcial)
        self.puente.turno.connect(self._turno)
        self.puente.estado.connect(self._estado)

        self.setWindowTitle("Veyl Jr" + (" (demo)" if demo else ""))
        self.resize(900, 600)

        self.titulo = QLineEdit(placeholderText="Título de la reunión (opcional)")
        self.boton = QPushButton("Iniciar")
        self.boton.clicked.connect(self.alternar)
        fila = QHBoxLayout()
        fila.addWidget(self.titulo, 1)
        fila.addWidget(self.boton)

        self.texto = QTextEdit(readOnly=True)
        self.parcial = QLabel("")
        self.parcial.setStyleSheet("color: gray;")
        self.parcial.setWordWrap(True)
        self.estado = QLabel("Listo.")
        self.estado.setWordWrap(True)

        izquierda = QVBoxLayout()
        izquierda.addLayout(fila)
        izquierda.addWidget(self.texto, 1)
        izquierda.addWidget(self.parcial)
        izquierda.addWidget(self.estado)

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self._abrir_item)
        abrir_carpeta = QPushButton("Abrir carpeta")
        abrir_carpeta.clicked.connect(self._abrir_carpeta)
        derecha = QVBoxLayout()
        derecha.addWidget(QLabel("Reuniones guardadas (doble clic para abrir)"))
        derecha.addWidget(self.lista, 1)
        derecha.addWidget(abrir_carpeta)

        raiz = QHBoxLayout(self)
        raiz.addLayout(izquierda, 3)
        raiz.addLayout(derecha, 2)
        self._refrescar_lista()

    # ---------- Grabación ----------

    def alternar(self) -> None:
        if self.motor is None:
            self.iniciar()
        else:
            self.detener()

    def iniciar(self) -> None:
        if not self.demo and not self.cfg.assemblyai_key:
            QMessageBox.warning(self, "Falta la clave",
                                "Falta ASSEMBLYAI_API_KEY: copia .env.example a .env y agrega tu clave.")
            return
        if not self.avisado:
            r = QMessageBox.question(self, "Aviso a los participantes", f"{AVISO}\n\n¿Ya les avisaste?")
            if r != QMessageBox.StandardButton.Yes:
                return
            self.avisado = True

        self.reunion = Reunion(self.cfg.carpeta_reuniones, self.titulo.text())
        self.texto.clear()
        self.parcial.clear()
        emitir = (self.puente.parcial.emit, self.puente.turno.emit, self.puente.estado.emit)
        self.motor = MotorDemo(*emitir) if self.demo else MotorAudio(self.cfg, *emitir)
        self.motor.iniciar()
        self.titulo.setEnabled(False)
        self.boton.setText("Detener y guardar")
        self._estado(f"Grabando: {self.reunion.ruta.name}")

    def detener(self) -> None:
        self.motor.parar()
        QApplication.processEvents()  # entrega las últimas frases que quedaron en cola
        self.motor = None
        ruta = self.reunion.terminar()
        self.reunion = None
        self.titulo.setEnabled(True)
        self.boton.setText("Iniciar")
        self.parcial.clear()
        self._estado(f"Guardada en {ruta}" if ruta else "Sin frases: no se guardó nada.")
        self._refrescar_lista()

    # ---------- Eventos del motor ----------

    def _parcial(self, hablante: str, texto: str) -> None:
        if self.reunion is not None:
            self.parcial.setText(f"{hablante}: {texto}…")

    def _turno(self, hablante: str, texto: str) -> None:
        if self.reunion is None:
            return
        turno = self.reunion.agregar(hablante, texto)
        self.texto.append(f"<b>[{hhmmss(turno.segundo)}] {hablante}:</b> {_escapar(texto)}")
        self.parcial.clear()
        if len(self.reunion.turnos) == 1:
            self._refrescar_lista()  # el archivo aparece con la primera frase

    def _estado(self, mensaje: str) -> None:
        self.estado.setText(mensaje)

    # ---------- Reuniones guardadas ----------

    def _refrescar_lista(self) -> None:
        self.lista.clear()
        for ruta in listar(self.cfg.carpeta_reuniones):
            item = QListWidgetItem(ruta.stem)
            item.setData(Qt.ItemDataRole.UserRole, str(ruta))
            self.lista.addItem(item)

    def _abrir_item(self, item: QListWidgetItem) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(item.data(Qt.ItemDataRole.UserRole)))

    def _abrir_carpeta(self) -> None:
        carpeta = Path(self.cfg.carpeta_reuniones)
        carpeta.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta)))

    def closeEvent(self, evento) -> None:
        if self.motor is not None:
            self.detener()
        evento.accept()


def _escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def abrir(cfg: Config, demo: bool = False) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    ventana = Ventana(cfg, demo=demo)
    ventana.show()
    return app.exec()
