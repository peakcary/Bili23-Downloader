"""Queue overview and immediate access to task concurrency."""
from PySide6.QtCore import QTimer, Slot, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from qfluentwidgets import BodyLabel, CaptionLabel, SpinBox

from util.common.config import config
from util.common.enum import DownloadStatus
from util.format.units import Units


class DownloadSummary(QWidget):
    def __init__(self, model, schedule, parent=None):
        super().__init__(parent)
        self.model = model
        self.schedule = schedule
        self.status = BodyLabel(self)
        self.status.setWordWrap(True)
        self.parallel_label = BodyLabel(self.tr("Simultaneous downloads"), self)
        self.parallel = SpinBox(self)
        self.parallel.setRange(1, 10)
        self.parallel.setValue(config.get(config.download_parallel))
        self.parallel.setAccessibleName(self.tr("Simultaneous downloads"))
        self.parallel.setFixedWidth(100)
        self.hint = CaptionLabel(self.tr("Tasks share bandwidth. Threads per task are configured in Settings."), self)
        self.hint.setWordWrap(True)
        self.parallel.setToolTip(self.tr("Lowering this limit lets running tasks finish; queued tasks wait."))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.parallel_label)
        row.addWidget(self.parallel)
        row.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 8)
        layout.setSpacing(6)
        layout.addWidget(self.status)
        layout.addLayout(row)
        layout.addWidget(self.hint)
        self.parallel.valueChanged.connect(self.onParallelChanged)
        config.download_parallel.valueChanged.connect(self.syncParallel)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        model.rowsInserted.connect(self.refresh)
        model.rowsRemoved.connect(self.refresh)
        model.modelReset.connect(self.refresh)
        self.refresh()

    @Slot(int)
    def onParallelChanged(self, value):
        config.set(config.download_parallel, value)

    def syncParallel(self, value):
        self.parallel.blockSignals(True)
        self.parallel.setValue(value)
        self.parallel.blockSignals(False)
        self.schedule()

    def refresh(self, *args):
        active = queued = failed = speed = 0
        # Read the source model, so search/filtering cannot hide queue totals.
        for row in range(self.model.rowCount()):
            task = self.model.index(row).data(Qt.ItemDataRole.UserRole)
            state = task.Download.status
            if state == DownloadStatus.DOWNLOADING:
                active += 1
                speed += max(0, task.Download.speed)
            elif state == DownloadStatus.QUEUED:
                queued += 1
            elif state in (DownloadStatus.FAILED, DownloadStatus.FFMPEG_FAILED):
                failed += 1
        self.status.setText(self.tr("Downloading %s · Queued %s · Failed %s · Total speed %s/s") %
                            (active, queued, failed, Units.format_file_size(speed)))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
