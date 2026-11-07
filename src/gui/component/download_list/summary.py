"""Queue overview and immediate access to task concurrency."""
from PySide6.QtCore import QTimer, Slot, Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from qfluentwidgets import BodyLabel, SpinBox, TogglePushButton, FlowLayout

from util.common.config import config
from util.common.enum import DownloadStatus
from util.format.units import Units


class DownloadSummary(QWidget):
    filterRequested = Signal(object)

    def __init__(self, model, schedule, parent=None):
        super().__init__(parent)
        self.model = model
        self.schedule = schedule
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status = BodyLabel(self)
        self.parallel_label = BodyLabel(self.tr("Simultaneous downloads"), self)
        self.parallel = SpinBox(self)
        self.parallel.setRange(1, 10)
        self.parallel.setValue(config.get(config.download_parallel))
        self.parallel.setAccessibleName(self.tr("Simultaneous downloads"))
        self.parallel.setFixedWidth(120)
        self.parallel.setToolTip(self.tr("Tasks share bandwidth. Threads per task are configured in Settings.") + "\n" +
                                 self.tr("Lowering this limit lets running tasks finish; queued tasks wait."))
        self.groups = [
            (self.tr("All"), frozenset()),
            (self.tr("Downloading"), frozenset({DownloadStatus.DOWNLOADING})),
            (self.tr("Queued"), frozenset({DownloadStatus.QUEUED})),
            (self.tr("Paused"), frozenset({DownloadStatus.PAUSED})),
            (self.tr("Processing"), frozenset({DownloadStatus.PARSING, DownloadStatus.MERGING,
                DownloadStatus.CONVERTING, DownloadStatus.FFMPEG_QUEUED, DownloadStatus.ADDITIONAL_PROCESSING})),
            (self.tr("Failed"), frozenset({DownloadStatus.FAILED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.INVALID})),
        ]
        self.active_filter = frozenset()
        self.buttons = []
        chips = QWidget(self)
        flow = FlowLayout(chips, needAni=False)
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setHorizontalSpacing(8)
        flow.setVerticalSpacing(6)
        for label, states in self.groups:
            button = TogglePushButton(label, chips)
            button.clicked.connect(lambda checked=False, values=states: self.chooseFilter(values))
            flow.addWidget(button)
            self.buttons.append(button)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.status)
        row.addStretch()
        row.addWidget(self.parallel_label)
        row.addWidget(self.parallel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(10)
        layout.addLayout(row)
        layout.addWidget(chips)
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

    def chooseFilter(self, states):
        self.active_filter = frozenset(states)
        self.filterRequested.emit(self.active_filter)
        self.refresh()

    def syncFilter(self, states):
        self.active_filter = frozenset(states)
        self.refresh()

    def refresh(self, *args):
        counts = {state: 0 for state in DownloadStatus}
        speed = 0
        for row in range(self.model.rowCount()):
            task = self.model.index(row).data(Qt.ItemDataRole.UserRole)
            state = task.Download.status
            counts[state] = counts.get(state, 0) + 1
            if state == DownloadStatus.DOWNLOADING:
                speed += max(0, task.Download.speed)
        self.status.setText(self.tr("Total speed %s/s") % Units.format_file_size(speed))
        for button, (label, states) in zip(self.buttons, self.groups):
            count = sum(counts.get(state, 0) for state in states) if states else self.model.rowCount()
            button.setText(f"{label}  {count}")
            button.setChecked(states == self.active_filter)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
