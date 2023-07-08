#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib
import sys

from PyQt6.QtCore import QEvent, QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from video2x import Interpolator, Upscaler, Video2X


class VideoUpscaleWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def upscale(
        self,
        input_path,
        output_path,
        width,
        height,
        noise,
        processes,
        threshold,
        algorithm,
    ):
        try:
            # setup video2x object
            video2x = Video2X(progress_callback=self.report_progress)

            # run upscale
            video2x.upscale(
                input_path,
                output_path,
                width,
                height,
                noise,
                processes,
                threshold,
                algorithm,
            )
            self.finished.emit()
        except Exception as error:
            self.error.emit(str(error))

    def interpolate(self, input_path, output_path, processes, threshold, algorithm):
        try:
            # setup video2x object
            video2x = Video2X(progress_callback=self.report_progress)

            # run interpolate
            video2x.interpolate(
                input_path,
                output_path,
                processes,
                threshold,
                algorithm,
            )
            self.finished.emit()
        except Exception as error:
            self.error.emit(str(error))

    def report_progress(self, current: int, total: int) -> None:
        self.progress.emit(current, total)


class AdvancedSettingsWidget(QWidget):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent
        self.resize(700, 0)

        main_layout = QVBoxLayout()

        # output group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        output_line_layout = QHBoxLayout()
        self.output = QLineEdit(self)
        self.output.setPlaceholderText("leave empty to use the input file's directory")
        choose_file_button = QPushButton("Choose Directory", self)
        choose_file_button.clicked.connect(lambda: self.choose_directory(self.output))
        output_line_layout.addWidget(self.output)
        output_line_layout.addWidget(choose_file_button)
        self.output_format_string = QLineEdit(self)
        self.output_format_string.setText(
            "{filename}_{action}_{algorithm}_{settings}.{suffix}"
        )
        self.output_file_suffix = QLineEdit(self)
        self.output_file_suffix.setText("mp4")
        output_layout.addRow("Output Directory", output_line_layout)
        output_layout.addRow("Output Format String", self.output_format_string)
        output_layout.addRow("Output File Suffix", self.output_file_suffix)
        output_group.setLayout(output_layout)

        # algorithm settings group
        settings_group = QGroupBox("Algorithm Settings")
        settings_layout = QFormLayout()
        self.processes_spinbox = QSpinBox(self)
        self.processes_spinbox.setMinimum(1)
        self.processes_spinbox.setValue(1)
        self.processes_spinbox.setSingleStep(1)
        self.upscaling_threshold = QDoubleSpinBox(self)
        self.upscaling_threshold.setMinimum(0)
        self.upscaling_threshold.setMaximum(100)
        self.upscaling_threshold.setValue(0)
        self.interpolation_threshold = QDoubleSpinBox(self)
        self.interpolation_threshold.setMinimum(0)
        self.interpolation_threshold.setMaximum(100)
        self.interpolation_threshold.setValue(5)
        settings_layout.addRow("Processes", self.processes_spinbox)
        settings_layout.addRow("Upscaling Threshold", self.upscaling_threshold)
        settings_layout.addRow("Interpolation Threshold", self.interpolation_threshold)
        settings_group.setLayout(settings_layout)

        main_layout.addWidget(output_group)
        main_layout.addWidget(settings_group)
        self.close_button = QPushButton("Close")
        main_layout.addWidget(self.close_button)
        self.setLayout(main_layout)

        # connect to the slot
        self.close_button.clicked.connect(self.on_close_clicked)

    def on_close_clicked(self):
        self.hide()

    def choose_directory(self, line_edit):
        directory = QFileDialog.getExistingDirectory(
            self, "Choose Directory", "", QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            line_edit.setText(directory)


class FileListItem(QListWidgetItem):
    def __init__(self):
        super().__init__()


class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(580, 0)
        self.setMinimumHeight(200)
        self.setAcceptDrops(True)
        self.empty_label = QLabel(
            "Drag files here or use the button below to select files.",
            self,
        )
        self.empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.update_empty_label()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        self.add_files_to_list([url.toLocalFile() for url in urls])
        event.acceptProposedAction()

    def update_empty_label(self):
        if self.count() == 0:
            self.empty_label.show()
        else:
            self.empty_label.hide()

    def choose_files(self):
        files_chosen, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", "", "All Files (*);;Text Files (*.txt)"
        )
        self.add_files_to_list(files_chosen)

    def add_files_to_list(self, file_paths):
        for file_path in file_paths:
            for i in range(self.count()):
                if self.item(i).file_path == file_path:
                    break
            else:
                list_item = FileListItem()
                list_item.file_path = file_path

                widget = QWidget()
                layout = QHBoxLayout()
                file_label = QLabel(file_path)
                file_label.setWordWrap(True)

                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(
                    lambda checked, item=list_item: self.delete_item(item)
                )
                delete_button.setFixedWidth(delete_button.sizeHint().width())

                layout.addWidget(file_label, 1)
                layout.addWidget(delete_button, 0)

                widget.setLayout(layout)

                list_item.setSizeHint(widget.sizeHint())
                self.addItem(list_item)
                self.setItemWidget(list_item, widget)
        self.update_empty_label()

    def delete_item(self, item):
        self.takeItem(self.row(item))
        self.update_empty_label()


class Video2XQt6(QWidget):
    def __init__(self):
        super().__init__()

        # set default size
        self.resize(580, 0)

        # set up the layouts
        main_layout = QVBoxLayout()

        # input group
        self.input = FileListWidget(self)

        self.choose_files_button = QPushButton("Choose Files", self)
        self.choose_files_button.clicked.connect(self.input.choose_files)

        # settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()
        self.action_combo = QComboBox(self)
        self.action_combo.addItems(["Upscale", "Interpolate"])
        self.action_combo.currentIndexChanged.connect(self.update_action)
        self.algorithm_combo = QComboBox(self)
        self.algorithm_combo.addItems(Upscaler.ALGORITHM_CLASSES.keys())

        self.width_label = QLabel("Width (0=Auto)", self)
        self.height_label = QLabel("Height (0=Auto)", self)
        self.noise_label = QLabel("Noise", self)
        self.framerate_label = QLabel("Framerate", self)

        self.width_spinbox = QSpinBox(self)
        self.width_spinbox.setRange(0, 10000)
        self.width_spinbox.setValue(0)
        self.height_spinbox = QSpinBox(self)
        self.height_spinbox.setRange(0, 10000)
        self.height_spinbox.setValue(2160)
        self.noise_spinbox = QSpinBox(self)
        self.framerate_spinbox = QDoubleSpinBox(self)
        self.framerate_spinbox.setRange(0.01, 1000)
        self.framerate_spinbox.setSingleStep(1.0)
        self.framerate_spinbox.setValue(120)

        settings_layout.addRow("Action", self.action_combo)
        settings_layout.addRow("Algorithm", self.algorithm_combo)
        settings_layout.addRow(self.width_label, self.width_spinbox)
        settings_layout.addRow(self.height_label, self.height_spinbox)
        settings_layout.addRow(self.noise_label, self.noise_spinbox)
        settings_layout.addRow(self.framerate_label, self.framerate_spinbox)
        settings_group.setLayout(settings_layout)

        # progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # start button and checkbox
        start_layout = QHBoxLayout()
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.start_processing)
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_upscale)
        self.stop_button.hide()
        self.advanced_settings_button = QPushButton("Advanced Settings", self)
        self.advanced_settings_button.clicked.connect(self.show_advanced_settings)
        self.advanced_settings_widget = AdvancedSettingsWidget(self)
        start_layout.addWidget(self.start_button)
        start_layout.addWidget(self.stop_button)
        start_layout.addWidget(self.advanced_settings_button)

        main_layout.addWidget(self.input)
        main_layout.addWidget(self.choose_files_button)
        main_layout.addWidget(settings_group)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(start_layout)
        self.setLayout(main_layout)
        self.setWindowTitle("Video2X Qt6")

        self.installEventFilter(self)
        self.update_action()

        # initialize attributes
        self.video2x_thread = None

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyRelease:
            key = event.key()
            modifiers = event.modifiers()

            # Ctrl+Q or Ctrl+W to quit
            if (
                key in (Qt.Key.Key_W, Qt.Key.Key_Q)
            ) and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.close()
                return True

        return super().eventFilter(source, event)

    def update_action(self):
        action = self.action_combo.currentText()

        self.algorithm_combo.clear()

        # Show everything
        self.width_label.show()
        self.height_label.show()
        self.noise_label.show()
        self.framerate_label.show()

        self.width_spinbox.show()
        self.height_spinbox.show()
        self.noise_spinbox.show()
        self.framerate_spinbox.show()

        if action == "Upscale":
            self.algorithm_combo.addItems(Upscaler.ALGORITHM_CLASSES.keys())

            # hide things not needed for Upscale
            self.framerate_label.hide()
            self.framerate_spinbox.hide()
        elif action == "Interpolate":
            self.algorithm_combo.addItems(Interpolator.ALGORITHM_CLASSES.keys())

            # hide things not needed for Interpolate
            self.width_label.hide()
            self.height_label.hide()
            self.noise_label.hide()

            self.width_spinbox.hide()
            self.height_spinbox.hide()
            self.noise_spinbox.hide()

        self.algorithm_combo.setCurrentIndex(0)

    def show_advanced_settings(self):
        self.advanced_settings_widget.show()

    def choose_file(self, target_input):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*);;Text Files (*.txt)"
        )
        if file_name:
            target_input.setText(file_name)

    def start_processing(self):
        if self.input.count() == 0:
            QMessageBox.critical(self, "Error", "No input file specified.")
            return

        for i in range(self.input.count()):
            input_path = pathlib.Path(self.input.item(i).file_path)
            width = self.width_spinbox.value()
            height = self.height_spinbox.value()
            action = self.action_combo.currentText()
            noise = self.noise_spinbox.value()
            processes = self.advanced_settings_widget.processes_spinbox.value()
            upscale_threshold = (
                self.advanced_settings_widget.upscaling_threshold.value()
            )
            interpolation_threshold = (
                self.advanced_settings_widget.interpolation_threshold.value()
            )
            algorithm = self.algorithm_combo.currentText()

            if action == "Upscale":
                settings_string = f"{width}x{height}_{noise}"
            else:
                settings_string = ""

            output_file = pathlib.Path(
                self.advanced_settings_widget.output_format_string.text().format(
                    filename=input_path.stem,
                    action=action.lower(),
                    algorithm=algorithm,
                    settings=settings_string,
                    suffix=self.advanced_settings_widget.output_file_suffix.text(),
                )
            )

            if self.advanced_settings_widget.output.text() == "":
                output_path = input_path.parent / output_file
            else:
                output_path = (
                    pathlib.Path(self.advanced_settings_widget.output.text())
                    / output_file
                )

            if input_path.is_file() is False:
                QMessageBox.critical(
                    self, "Error", "Specified input file does not exist."
                )
                return

            if output_path.is_file() is True:
                reply = QMessageBox.question(
                    self,
                    "Overwrite?",
                    "The specified output file already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes,
                    QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.No:
                    return

            self.start_button.setText("Pause")
            self.stop_button.show()

            # set up worker and thread
            self.video2x_thread = QThread()
            self.worker = VideoUpscaleWorker()
            self.worker.moveToThread(self.video2x_thread)
            self.worker.finished.connect(self.upscale_finish)
            self.worker.progress.connect(self.update_progress)
            self.worker.error.connect(self.handle_error)

            if action == "Upscale":
                self.video2x_thread.started.connect(
                    lambda: self.worker.upscale(
                        input_path,
                        output_path,
                        width,
                        height,
                        noise,
                        processes,
                        upscale_threshold,
                        algorithm,
                    )
                )
            elif action == "Interpolate":
                self.video2x_thread.started.connect(
                    lambda: self.worker.interpolate(
                        input_path,
                        output_path,
                        processes,
                        interpolation_threshold,
                        algorithm,
                    )
                )
            else:
                raise ValueError(f"Invalid action: {action}")

            self.video2x_thread.finished.connect(self.video2x_thread.deleteLater)

            # start the thread
            self.video2x_thread.start()

    def stop_upscale(self):
        if self.video2x_thread is not None:
            self.video2x_thread.quit()
            self.video2x_thread.wait()
            self.stop_button.hide()

    def upscale_finish(self):
        self.start_button.setText("Start")

        QMessageBox.information(self, "Finished", "Video processing completed.")

        self.video2x_thread.quit()
        self.video2x_thread.wait()
        self.stop_button.hide()

    def update_progress(self, current: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def handle_error(self, message: str):
        QMessageBox.critical(self, "Error", message)

        self.start_button.setText("Start")
        self.video2x_thread.quit()
        self.video2x_thread.wait()
        self.stop_button.hide()


def main():
    app = QApplication(sys.argv)
    window = Video2XQt6()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
