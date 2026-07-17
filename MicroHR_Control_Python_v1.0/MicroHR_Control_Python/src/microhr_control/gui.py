from __future__ import annotations

import datetime as dt
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .async_runner import AsyncRunner
from .controller import MicroHRController
from .models import CameraSettings, ScanSettings, Spectrum


class MicroHRApp(tk.Tk):
    def __init__(self, controller: MicroHRController, config: dict[str, Any]):
        super().__init__()
        self.controller = controller
        self.config = config
        self.runner = AsyncRunner()
        self.title("HORIBA MicroHR Control — 0340-0913-MHRA")
        self.geometry("1280x820")
        self.minsize(1000, 700)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Déconnecté")
        self.wavelength_var = tk.StringVar(value="532.0")
        self.grating_var = tk.StringVar(value="1")
        camera_cfg = config.get("camera", {})
        scan_cfg = config.get("scan", {})
        self.exposure_var = tk.StringVar(value=str(camera_cfg.get("exposure_time", 100)))
        self.start_var = tk.StringVar(value=str(scan_cfg.get("start_nm", 500.0)))
        self.stop_var = tk.StringVar(value=str(scan_cfg.get("stop_nm", 600.0)))
        self.step_var = tk.StringVar(value=str(scan_cfg.get("step_nm", 1.0)))
        self.settle_var = tk.StringVar(value=str(scan_cfg.get("settle_time_s", 0.2)))
        self.progress_var = tk.DoubleVar(value=0.0)
        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="État :").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.status_var, width=45).pack(side=tk.LEFT, padx=(4, 20))
        ttk.Button(top, text="Connecter", command=self.connect).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="Déconnecter", command=self.disconnect).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="Initialiser", command=self.initialize).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="État matériel", command=self.refresh_status).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="ARRÊT", command=self.abort).pack(side=tk.RIGHT, padx=3)

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        controls = ttk.Frame(body, padding=8, width=330)
        graph_area = ttk.Frame(body, padding=4)
        body.add(controls, weight=0)
        body.add(graph_area, weight=1)

        move_box = ttk.LabelFrame(controls, text="Monochromateur", padding=8)
        move_box.pack(fill=tk.X, pady=4)
        self._field(move_box, "Longueur d'onde (nm)", self.wavelength_var)
        ttk.Button(move_box, text="Déplacer", command=self.move).pack(fill=tk.X, pady=4)
        self._field(move_box, "Réseau (1–3)", self.grating_var)
        ttk.Button(move_box, text="Sélectionner le réseau", command=self.set_grating).pack(fill=tk.X, pady=4)

        acq_box = ttk.LabelFrame(controls, text="Acquisition caméra", padding=8)
        acq_box.pack(fill=tk.X, pady=4)
        self._field(acq_box, "Exposition (unités timer)", self.exposure_var)
        ttk.Button(acq_box, text="Acquérir", command=self.acquire).pack(fill=tk.X, pady=4)
        ttk.Button(acq_box, text="Acquérir et enregistrer", command=self.acquire_save).pack(fill=tk.X, pady=4)

        scan_box = ttk.LabelFrame(controls, text="Scan spectral", padding=8)
        scan_box.pack(fill=tk.X, pady=4)
        self._field(scan_box, "Début (nm)", self.start_var)
        self._field(scan_box, "Fin (nm)", self.stop_var)
        self._field(scan_box, "Pas (nm)", self.step_var)
        self._field(scan_box, "Stabilisation (s)", self.settle_var)
        ttk.Button(scan_box, text="Lancer le scan", command=self.scan).pack(fill=tk.X, pady=4)
        ttk.Button(scan_box, text="Scanner et enregistrer", command=self.scan_save).pack(fill=tk.X, pady=4)
        ttk.Progressbar(scan_box, variable=self.progress_var, maximum=100).pack(fill=tk.X, pady=6)

        log_box = ttk.LabelFrame(controls, text="Journal", padding=4)
        log_box.pack(fill=tk.BOTH, expand=True, pady=4)
        self.log_text = tk.Text(log_box, height=12, wrap="word", state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax_spectrum = self.figure.add_subplot(211)
        self.ax_scan = self.figure.add_subplot(212)
        self.ax_spectrum.set_title("Dernière acquisition CCD")
        self.ax_spectrum.set_xlabel("Longueur d'onde / pixel")
        self.ax_spectrum.set_ylabel("Intensité")
        self.ax_scan.set_title("Scan")
        self.ax_scan.set_xlabel("Longueur d'onde centrale (nm)")
        self.ax_scan.set_ylabel("Intensité intégrée")
        self.figure.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_area)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def _field(parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable, width=12).pack(side=tk.RIGHT)

    def _submit(
        self,
        coroutine,
        on_success: Callable[[Any], None] | None = None,
        busy_message: str = "Opération en cours…",
    ) -> None:
        self.status_var.set(busy_message)
        future = self.runner.submit(coroutine)

        def poll() -> None:
            if not future.done():
                self.after(80, poll)
                return
            try:
                result = future.result()
            except BaseException as exc:
                self.status_var.set("Erreur")
                self._log(f"ERREUR : {exc}")
                messagebox.showerror("MicroHR", str(exc))
            else:
                self.status_var.set("Prêt")
                if on_success:
                    on_success(result)

        self.after(80, poll)

    def _camera_settings(self) -> CameraSettings:
        cfg = self.config.get("camera", {})
        roi = cfg.get("roi", {})
        return CameraSettings(
            exposure_time=int(self.exposure_var.get()),
            acquisition_count=int(cfg.get("acquisition_count", 1)),
            open_shutter=bool(cfg.get("open_shutter", True)),
            timeout_s=float(cfg.get("timeout_s", 120.0)),
            poll_interval_s=float(cfg.get("poll_interval_s", 0.1)),
            x_origin=int(roi.get("x_origin", 0)),
            y_origin=int(roi.get("y_origin", 0)),
            x_size=int(roi.get("x_size", 1024)),
            y_size=int(roi.get("y_size", 256)),
            x_bin=int(roi.get("x_bin", 1)),
            y_bin=int(roi.get("y_bin", 256)),
            x_axis_conversion=str(cfg.get("x_axis_conversion", "FROM_ICL_SETTINGS_INI")),
        )

    def _scan_settings(self) -> ScanSettings:
        return ScanSettings(
            start_nm=float(self.start_var.get()),
            stop_nm=float(self.stop_var.get()),
            step_nm=float(self.step_var.get()),
            settle_time_s=float(self.settle_var.get()),
            save_each_frame=bool(self.config.get("scan", {}).get("save_each_frame", False)),
        )

    def connect(self) -> None:
        self._submit(self.controller.connect(), self._show_status, "Connexion à ICL…")

    def disconnect(self) -> None:
        self._submit(self.controller.disconnect(), lambda _: self._log("Déconnecté."), "Déconnexion…")

    def initialize(self) -> None:
        self._submit(
            self.controller.initialize(lambda text: self.after(0, self._log, text)),
            lambda _: self._log("Initialisation terminée."),
            "Initialisation mécanique…",
        )

    def refresh_status(self) -> None:
        self._submit(self.controller.status(), self._show_status, "Lecture de l'état…")

    def move(self) -> None:
        target = float(self.wavelength_var.get())
        self._submit(
            self.controller.move_to(target),
            lambda actual: self._log(f"Position : {actual:.4f} nm"),
            f"Déplacement vers {target:.3f} nm…",
        )

    def set_grating(self) -> None:
        number = int(self.grating_var.get())
        self._submit(
            self.controller.select_grating(number),
            lambda _: self._log(f"Réseau {number} sélectionné."),
            f"Changement vers réseau {number}…",
        )

    def acquire(self) -> None:
        self._submit(
            self.controller.acquire(self._camera_settings()),
            self._plot_spectrum,
            "Acquisition CCD…",
        )

    def acquire_save(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Base du fichier d'acquisition",
            defaultextension="",
            initialdir=str(self.controller.output_directory),
            initialfile=f"spectrum_{dt.datetime.now():%Y%m%d_%H%M%S}",
        )
        if path:
            self._submit(
                self.controller.acquire(self._camera_settings(), path),
                self._plot_spectrum,
                "Acquisition et enregistrement…",
            )

    def scan(self) -> None:
        self._start_scan(None)

    def scan_save(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Base du fichier de scan",
            defaultextension="",
            initialdir=str(self.controller.output_directory),
            initialfile=f"scan_{dt.datetime.now():%Y%m%d_%H%M%S}",
        )
        if path:
            self._start_scan(path)

    def _start_scan(self, output: str | None) -> None:
        self.progress_var.set(0)
        def progress(index: int, total: int, wavelength: float, frame: Spectrum) -> None:
            self.after(0, self._scan_progress, index, total, wavelength, frame)

        self._submit(
            self.controller.scan(self._scan_settings(), self._camera_settings(), progress, output),
            self._plot_scan,
            "Scan spectral…",
        )

    def _scan_progress(self, index: int, total: int, wavelength: float, frame: Spectrum) -> None:
        self.progress_var.set(index * 100 / total)
        self.status_var.set(f"Scan {index}/{total} — {wavelength:.3f} nm")
        self._plot_spectrum(frame, redraw=False)
        self.canvas.draw_idle()

    def abort(self) -> None:
        self.runner.submit(self.controller.abort())
        self.status_var.set("Arrêt demandé…")
        self._log("ARRÊT demandé.")

    def _show_status(self, status: dict) -> None:
        self._log(json.dumps(status, indent=2, ensure_ascii=False, default=str))
        wavelength = status.get("wavelength_nm")
        if wavelength is not None:
            self.wavelength_var.set(f"{float(wavelength):.4f}")
        grating = status.get("grating")
        if grating is not None:
            self.grating_var.set(str(grating))

    def _plot_spectrum(self, spectrum: Spectrum, redraw: bool = True) -> None:
        self.ax_spectrum.clear()
        self.ax_spectrum.plot(spectrum.x, spectrum.y)
        self.ax_spectrum.set_title(
            f"CCD — centre {spectrum.center_wavelength_nm:.3f} nm — exposition {spectrum.exposure_time}"
        )
        self.ax_spectrum.set_xlabel("Longueur d'onde / pixel")
        self.ax_spectrum.set_ylabel("Intensité")
        self.ax_spectrum.grid(True, alpha=0.25)
        if redraw:
            self.canvas.draw_idle()
        self._log(f"Acquisition : {spectrum.y.size} points, max={spectrum.y.max():.1f}")

    def _plot_scan(self, result) -> None:
        self.ax_scan.clear()
        self.ax_scan.plot(result.measured_wavelength_nm, result.integrated_intensity, marker=".")
        self.ax_scan.set_title("Scan spectral terminé")
        self.ax_scan.set_xlabel("Longueur d'onde centrale (nm)")
        self.ax_scan.set_ylabel("Intensité intégrée")
        self.ax_scan.grid(True, alpha=0.25)
        self.canvas.draw_idle()
        self.progress_var.set(100)
        self._log(f"Scan terminé : {len(result.frames)} points.")

    def _log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{dt.datetime.now():%H:%M:%S}  {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_close(self) -> None:
        try:
            self.runner.submit(self.controller.disconnect()).result(timeout=5)
        except Exception:
            pass
        self.runner.close()
        self.destroy()
