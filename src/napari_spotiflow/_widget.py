from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import tifffile
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

SUPPORTED_EXTS = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"}


def _iter_images(folder: Path) -> Iterable[Path]:
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            yield p


def _load_image_2d(path: Path) -> np.ndarray:
    try:
        arr = tifffile.imread(str(path))
    except Exception:
        import imageio.v3 as iio

        arr = iio.imread(str(path))
    arr = np.asarray(arr)

    if arr.ndim < 2:
        raise ValueError(f"Image must be at least 2D: {path.name}")

    while arr.ndim > 2:
        arr = arr.max(axis=0)

    return arr.astype(np.float32)


class SpotiflowWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        self._model = None
        self._model_name = "general"
        self._current_image_layer = None
        self._current_points_layer = None

        self.setLayout(QVBoxLayout())

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Spotiflow model:"))
        self.model_edit = QLineEdit("general")
        model_row.addWidget(self.model_edit)
        self.layout().addLayout(model_row)

        self.layout().addWidget(self._build_single_group())
        self.layout().addWidget(self._build_batch_group())

        self.status_label = QLabel("Ready")
        status_row = QHBoxLayout()
        self._busy_indicator = QProgressBar()
        self._busy_indicator.setRange(0, 0)
        self._busy_indicator.setFixedWidth(80)
        self._busy_indicator.setFixedHeight(10)
        self._busy_indicator.hide()
        status_row.addWidget(self._busy_indicator)
        status_row.addWidget(self.status_label, stretch=1)
        self.layout().addLayout(status_row)

    def _build_single_group(self) -> QGroupBox:
        box = QGroupBox("1) Individual image processing")
        grid = QGridLayout()
        box.setLayout(grid)

        self.single_folder_edit = QLineEdit()
        browse_single_folder_btn = QPushButton("Browse folder")
        browse_single_folder_btn.clicked.connect(self._pick_single_folder)

        self.image_combo = QComboBox()
        self.image_combo.currentIndexChanged.connect(self._load_selected_image)
        run_single_btn = QPushButton("Detect dots (single)")
        run_single_btn.clicked.connect(self._run_single)

        self.single_count_edit = QLineEdit("0")
        self.single_count_edit.setReadOnly(True)

        grid.addWidget(QLabel("Image folder:"), 0, 0)
        grid.addWidget(self.single_folder_edit, 0, 1)
        grid.addWidget(browse_single_folder_btn, 0, 2)

        grid.addWidget(QLabel("Image:"), 1, 0)
        grid.addWidget(self.image_combo, 1, 1, 1, 2)

        grid.addWidget(run_single_btn, 2, 1)

        grid.addWidget(QLabel("Dot count:"), 3, 0)
        grid.addWidget(self.single_count_edit, 3, 1)

        return box

    def _build_batch_group(self) -> QGroupBox:
        box = QGroupBox("2) Batch folder processing")
        grid = QGridLayout()
        box.setLayout(grid)

        self.folder_list = QListWidget()
        self.folder_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        add_folder_btn = QPushButton("Add folder")
        add_folder_btn.clicked.connect(self._add_batch_folder)

        remove_folder_btn = QPushButton("Remove selected")
        remove_folder_btn.clicked.connect(self._remove_selected_batch_folders)

        clear_folders_btn = QPushButton("Clear folders")
        clear_folders_btn.clicked.connect(self.folder_list.clear)

        btn_row = QHBoxLayout()
        btn_row.addWidget(add_folder_btn)
        btn_row.addWidget(remove_folder_btn)
        btn_row.addWidget(clear_folders_btn)

        self.output_excel_edit = QLineEdit()
        self.output_excel_edit.setPlaceholderText("Select output .xlsx path")
        browse_output_btn = QPushButton("Browse output")
        browse_output_btn.clicked.connect(self._pick_output_excel)

        run_batch_btn = QPushButton("Run batch + export Excel")
        run_batch_btn.clicked.connect(self._run_batch)

        grid.addWidget(QLabel("Folders to process:"), 0, 0)
        grid.addWidget(self.folder_list, 1, 0, 1, 3)
        grid.addLayout(btn_row, 2, 0, 1, 3)

        grid.addWidget(QLabel("Excel output:"), 3, 0)
        grid.addWidget(self.output_excel_edit, 3, 1)
        grid.addWidget(browse_output_btn, 3, 2)

        grid.addWidget(run_batch_btn, 4, 1)

        return box

    def _set_busy(self, busy: bool, message: str = ""):
        if busy:
            self._busy_indicator.show()
        else:
            self._busy_indicator.hide()
        if message:
            self.status_label.setText(message)
        QApplication.processEvents()

    def _pick_single_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select image folder")
        if not folder:
            return
        self.single_folder_edit.setText(folder)
        self._refresh_single_images()

    def _refresh_single_images(self):
        self.image_combo.blockSignals(True)
        self.image_combo.clear()

        folder = Path(self.single_folder_edit.text().strip())
        if not folder.exists() or not folder.is_dir():
            self.image_combo.blockSignals(False)
            return

        images = list(_iter_images(folder))
        for p in images:
            self.image_combo.addItem(p.name)

        self.image_combo.blockSignals(False)

        self.status_label.setText(f"Found {len(images)} image(s) in {folder.name}")
        self._load_selected_image()

    def _load_selected_image(self):
        folder = Path(self.single_folder_edit.text().strip())
        image_name = self.image_combo.currentText()
        if not folder.is_dir() or not image_name:
            return

        image_path = folder / image_name
        try:
            self._set_busy(True, f"Loading: {image_name}")
            image = _load_image_2d(image_path)
        except Exception as exc:
            self._set_busy(False, "Error loading image")
            QMessageBox.critical(self, "Load error", str(exc))
            return

        # Replace previous image layer if it exists
        if self._current_image_layer is not None:
            try:
                self.viewer.layers.remove(self._current_image_layer)
            except Exception:
                pass
            self._current_image_layer = None

        if self._current_points_layer is not None:
            try:
                self.viewer.layers.remove(self._current_points_layer)
            except Exception:
                pass
            self._current_points_layer = None

        self.single_count_edit.setText("0")

        self._current_image_layer = self.viewer.add_image(image, name=f"img:{image_name}")
        self._set_busy(False, f"Loaded: {image_name}")

    def _add_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder for batch processing")
        if not folder:
            return

        existing = {self.folder_list.item(i).text() for i in range(self.folder_list.count())}
        if folder not in existing:
            self.folder_list.addItem(folder)

    def _remove_selected_batch_folders(self):
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))

    def _pick_output_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select output Excel file",
            "spotiflow_counts.xlsx",
            "Excel files (*.xlsx)",
        )
        if file_path:
            if not file_path.lower().endswith(".xlsx"):
                file_path += ".xlsx"
            self.output_excel_edit.setText(file_path)

    def _get_model(self):
        model_name = self.model_edit.text().strip() or "general"

        if self._model is not None and model_name == self._model_name:
            return self._model

        # Work around duplicate OpenMP runtimes (libomp/libiomp) that can break
        # Torch/Spotiflow imports on Windows in mixed conda/pip environments.
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

        from spotiflow.model import Spotiflow

        self.status_label.setText(f"Loading Spotiflow model: {model_name}")
        self._model = Spotiflow.from_pretrained(model_name)
        self._model_name = model_name
        return self._model

    def _detect_points(self, image_2d: np.ndarray) -> np.ndarray:
        model = self._get_model()
        points, _details = model.predict(image_2d, subpix=True)
        points = np.asarray(points)
        if points.ndim == 1:
            points = points.reshape(-1, 2)
        return points

    def _run_single(self):
        folder = Path(self.single_folder_edit.text().strip())
        image_name = self.image_combo.currentText()

        if not folder.exists() or not folder.is_dir() or not image_name:
            QMessageBox.warning(self, "Missing input", "Select a valid folder and image.")
            return

        image_path = folder / image_name

        try:
            self._set_busy(True, f"Running Spotiflow on: {image_name}")
            image = _load_image_2d(image_path)
            points = self._detect_points(image)

            self._current_points_layer = self.viewer.add_points(
                points,
                name=f"spots:{image_name}",
                border_color="green",
                face_color="transparent",
                size=10,
            )

            count = int(len(points))
            self.single_count_edit.setText(str(count))
            self.status_label.setText(f"Done: {image_name} -> {count} dots")
            self._set_busy(False, f"Done: {image_name} -> {count} dots")

        except Exception as exc:
            self._set_busy(False, "Error")
            QMessageBox.critical(self, "Detection error", str(exc))

    def _run_batch(self):
        folder_paths = [self.folder_list.item(i).text() for i in range(self.folder_list.count())]
        output_path = self.output_excel_edit.text().strip()

        if not folder_paths:
            QMessageBox.warning(self, "Missing input", "Add at least one folder for batch processing.")
            return
        if not output_path:
            QMessageBox.warning(self, "Missing output", "Select an output Excel file.")
            return

        rows = []
        total = 0
        total_images = 0

        try:
            for folder_text in folder_paths:
                folder = Path(folder_text)
                if not folder.exists() or not folder.is_dir():
                    continue

                images = list(_iter_images(folder))
                total_images += len(images)
                for image_path in images:
                    total += 1
                    self._set_busy(True, f"Processing {total}/{total_images}: {image_path.name}")
                    image = _load_image_2d(image_path)
                    points = self._detect_points(image)
                    count = int(len(points))

                    rows.append(
                        {
                            "image_name": image_path.name,
                            "dot_count": count,
                            "folder": str(folder),
                        }
                    )

            df = pd.DataFrame(rows, columns=["image_name", "dot_count", "folder"])
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(out, index=False)

            self._set_busy(False, f"Batch done: {total} image(s), saved {out.name}")
            QMessageBox.information(
                self,
                "Batch complete",
                f"Processed {total} image(s).\nSaved: {out}",
            )

        except Exception as exc:
            self._set_busy(False, "Error")
            QMessageBox.critical(self, "Batch error", str(exc))
