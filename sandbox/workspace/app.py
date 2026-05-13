import sys
import time
from typing import Callable, Optional, Tuple, List

from PyQt6.QtCore import (
    QObject, pyqtSignal, pyqtSlot, QThread, Qt
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QGroupBox, QPushButton, QDoubleSpinBox, QSpinBox, QLabel, QCheckBox, QFrame,
    QStatusBar
)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.figure import Figure
import os
# os.environ["EPICS_CA_AUTO_ADDR_LIST"] = "NO"
# os.environ["EPICS_CA_ADDR_LIST"] = "localhost"
# os.environ["EPICS_CA_SERVER_PORT"] = "6090"
#os.environ["EPICS_CA_SERVER_PORT"] = "6090"
#os.environ["EPICS_CA_ADDR_LIST"] = ""
#os.environ["EPICS_CA_AUTO_ADDR_LIST"] = ""
#os.environ["EPICS_PVA_SERVER_PORT"] = ""
#os.environ["EPICS_PVA_BROADCAST_PORT"] = "6090"
#os.environ["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"
#os.environ["EPICS_PVA_INTERFACE"] = "172.18.0.3"
qname = "VM-INJ-Q0H07.1:CalcK"
sname = "SIM-INJ-Q0H08.2:SIGMA:X"


# -------------------------------
# Matplotlib Canvas
# -------------------------------
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(constrained_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Live Scan")
        self.ax.set_xlabel(r"K1 [1/m${^2}$]")
        self.ax.set_ylabel(r"$\sigma_{x}$ [$\mu$m]")
        # Prepare an empty line for fast updates
        (self.line,) = self.ax.plot([], [], "o-", lw=1.5, ms=4)
        self.ax.grid(True, alpha=0.3)

    def clear(self):
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw_idle()

    def update_line(self, xs: List[float], ys: List[float], autoscale: bool = True):
        self.line.set_data(xs, ys)
        if autoscale:
            self.ax.relim()
            self.ax.autoscale_view()
        self.draw_idle()


# -------------------------------
# Worker running in a background thread
# -------------------------------
class ScanWorker(QObject):
    """
    Long-running scan worker that emits new data as it arrives.
    Uses:
      - CA (pyepics) for setting qname
      - PVA (p4p) for reading sname
    """
    data_ready = pyqtSignal(float, float)
    status = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        ctx,
        step: float,
        initial_value: float,
        final_value: float,
        data_fn: Optional[Callable[[int, float], Tuple[float, float]]] = None,
        parent=None
    ):
        super().__init__(parent)
        # Only store pure Python state here
        self.ctx = ctx
        self._running = False
        self.step = step
        self.initial_value = initial_value
        self.final_value = final_value
        self._point_index = 0
        self._x = initial_value

        # Optional external data function
        self.data_fn = data_fn

    # -------------------------------
    # Default scan logic (same as your original intent)
    # -------------------------------
    def default_data_fn(self, i: int, x: float) -> Tuple[float, float]:
        """
        Increment qname via CA, then wait until sname changes via PVA.
        """
        x_new = x + self.step

        # ---- CA write ----
        self.pv_k.put(x_new, wait=True)

        # ---- PVA read & wait for change ----
        y0 = self.ctx.get(sname, throw=False)

        while self._running:
            # Keep CA alive
            self.ca.poll(0.01)

            try:
                y1 = self.ctx.get(sname)
                print(y1)
                if y1 != y0:
                    break
            except TimeoutError:
                print("Timeout waiting for PVA value; retrying...")
                time.sleep(0.05)

            time.sleep(0.05)

        print(x_new, y1)
        return x_new, y1

    # -------------------------------
    # Main worker entry point
    # -------------------------------
    @pyqtSlot()
    def run(self):
        """
        Executed inside the QThread.
        All EPICS objects are created here.
        """
        from epics import ca, PV
        ca.create_context()
        self.ca = ca

        # ---- Create PVs in THIS thread ----
        self.pv_k = PV(qname)

        if not self.pv_k.wait_for_connection(timeout=2):
            print("Failed to connect to CA PV")
            self.status.emit("Failed to connect CA PV")
            self.finished.emit()
            return

        # Choose data function
        fn = self.data_fn if self.data_fn is not None else self.default_data_fn

        self._running = True
        self.status.emit("Scan started")

        while self._running and self._x < self.final_value + 0.1:
            print("Scanning at:", self._x)

            # Generate next point
            x_new, y = fn(self._point_index, self._x)

            # Send to GUI
            self.data_ready.emit(x_new, y*1e6)

            # Prepare next step
            self._point_index += 1
            self._x = x_new

        # ---- Graceful shutdown ----
        self._running = False
        self.status.emit("Scan finished")
        self.finished.emit()

    # -------------------------------
    # Stop request from GUI
    # -------------------------------
    @pyqtSlot()
    def request_stop(self):
        self._running = False



# -------------------------------
# Main Window
# -------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Threaded Scan Viewer (PyQt5 + Matplotlib)")
        self.resize(1100, 700)

        # -------- Central Layout --------
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        # Left panel: controls
        controls = self._create_controls_panel()
        root.addWidget(controls, 0)  # smaller stretch on the left

        # Vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # Right panel: plot
        plot_box = QVBoxLayout()
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_box.addWidget(self.toolbar)
        plot_box.addWidget(self.canvas, 1)

        plot_container = QWidget()
        plot_container.setLayout(plot_box)
        root.addWidget(plot_container, 1)  # larger stretch on the right

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Data buffers (display only; logic remains in worker)
        self._xs: List[float] = []
        self._ys: List[float] = []

        # Thread-related members
        self._thread: Optional[QThread] = None
        self._worker: Optional[ScanWorker] = None

    # ------------- UI -------------
    def _create_controls_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Scan Controls & Config")
        form = QFormLayout(group)

        # Config widgets
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setDecimals(4)
        self.step_spin.setRange(0.0001, 1e6)
        self.step_spin.setValue(0.5)
        self.step_spin.setSingleStep(0.1)
        form.addRow("Step size (Δk1):", self.step_spin)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0, 10000)
        self.interval_spin.setValue(24)  # ms
        self.interval_spin.setSuffix(" 1/m^2")
        self.interval_spin.setDecimals(1)
        form.addRow("Initial k1:", self.interval_spin)

        self.maxpts_spin = QDoubleSpinBox()
        self.maxpts_spin.setRange(1, 5_000_000)
        self.maxpts_spin.setValue(32)
        self.maxpts_spin.setSuffix(" 1/m^2")
        self.maxpts_spin.setDecimals(1)
        form.addRow("End k1:", self.maxpts_spin)

        self.autoscale_chk = QCheckBox("Autoscale axes")
        self.autoscale_chk.setChecked(True)
        form.addRow("", self.autoscale_chk)

        # Buttons
        self.btn_start = QPushButton("Start Scan")
        self.btn_stop = QPushButton("Stop")
        self.btn_clear = QPushButton("Clear Plot")

        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_clear.clicked.connect(self.on_clear)

        layout.addWidget(group)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_clear)
        layout.addStretch(1)

        # Footer label (instructions)
        tip = QLabel(
            "Tip: Replace the worker's data_fn with your model's callback or step.\n"
            "All plotting occurs on the GUI thread via Qt signals."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #666;")
        layout.addWidget(tip)

        return panel

    # ------------- Controls -------------
    def on_start(self):
        if self._thread is not None:
            self.status.showMessage("Scan is already running.", 3000)
            return

        # Clear existing data
        self._xs.clear()
        self._ys.clear()
        self.canvas.clear()

        # Read config
        step = float(self.step_spin.value())
        initial_value = int(self.interval_spin.value())
        final_value = int(self.maxpts_spin.value())

        # Create thread and worker
        self._thread = QThread()
        from p4p.client.thread import Context
        self.pva_ctx = Context("pva")
        self._worker = ScanWorker(
            ctx=self.pva_ctx,
            step=step,
            initial_value=initial_value,
            final_value=final_value,
            data_fn=None  # <-- Provide your model function here if desired
        )
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.data_ready.connect(self.on_data_ready)
        self._worker.status.connect(self.status.showMessage)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)

        # Start
        self._thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status.showMessage("Starting scan...")

    @pyqtSlot()
    def on_stop(self):
        if self._worker is not None:
            self._worker.request_stop()
            self.status.showMessage("Stopping scan...")

    def _on_thread_finished(self):
        # Reset thread/worker references
        self._thread = None
        self._worker = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status.showMessage("Scan stopped", 3000)

    def on_clear(self):
        self._xs.clear()
        self._ys.clear()
        self.canvas.clear()
        self.status.showMessage("Plot cleared", 1500)

    # ------------- Data handling & plotting -------------
    @pyqtSlot(float, float)
    def on_data_ready(self, x: float, y: float):
        """
        Runs on the GUI thread (safe to touch matplotlib here).
        """
        self._xs.append(x)
        self._ys.append(y)

        # Update plot
        self.canvas.update_line(self._xs, self._ys, autoscale=self.autoscale_chk.isChecked())

    # ------------- Lifecycle -------------
    def closeEvent(self, event):
        # Ensure worker is stopped before closing
        if self._worker is not None:
            self._worker.request_stop()
            self.status.showMessage("Waiting for worker to finish...")
            # Let the event loop process until thread finishes
            self._thread.wait(3000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
