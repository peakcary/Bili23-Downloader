from PySide6.QtWidgets import QApplication
from util.download.task.info import TaskInfo
from util.common.enum import DownloadStatus


def test_summary_counts_source_queue_and_ignores_stale_speed():
    from gui.component.download_list.summary import DownloadSummary
    from gui.component.download_list.model import DownloadListModel
    app = QApplication.instance() or QApplication([])
    tasks = []
    for state, speed in [(DownloadStatus.DOWNLOADING, 1024), (DownloadStatus.QUEUED, 999),
                         (DownloadStatus.FAILED, 999), (DownloadStatus.PAUSED, 999)]:
        task = TaskInfo()
        task.Download.status, task.Download.speed = state, speed
        tasks.append(task)
    widget = DownloadSummary(DownloadListModel(tasks), lambda: None)
    assert app is not None
    assert 'Downloading 1' in widget.status.text()
    assert 'Queued 1' in widget.status.text()
    assert 'Failed 1' in widget.status.text()
    assert '1 KB/s' in widget.status.text()
    widget.close()


def test_parallel_control_saves_and_syncs(monkeypatch):
    from gui.component.download_list.summary import DownloadSummary
    from gui.component.download_list.model import DownloadListModel
    from util.common.config import config
    app = QApplication.instance() or QApplication([])
    calls = []
    monkeypatch.setattr(config, 'save', lambda: None)
    old = config.get(config.download_parallel)
    widget = DownloadSummary(DownloadListModel([]), lambda: calls.append(True))
    try:
        widget.parallel.setValue(3 if old != 3 else 2)
        assert config.get(config.download_parallel) == widget.parallel.value()
        config.set(config.download_parallel, 4)
        assert widget.parallel.value() == 4
        assert calls
        assert app is not None
        widget.resize(440, 180)
        widget.show()
        app.processEvents()
        widget.grab().save('/tmp/bili23-download-summary.png')
    finally:
        config.set(config.download_parallel, old)
        widget.close()
