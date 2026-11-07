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
    assert widget.buttons[1].text().endswith('1')
    assert widget.buttons[2].text().endswith('1')
    assert widget.buttons[5].text().endswith('1')
    assert widget.buttons[3].text().endswith('1')
    selected = []
    widget.filterRequested.connect(selected.append)
    widget.buttons[3].click()
    assert selected == [frozenset({DownloadStatus.PAUSED})]
    assert widget.buttons[3].isChecked()
    assert not widget.buttons[0].isChecked()
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


def test_status_chips_filter_queue(monkeypatch):
    from gui.interface.download import DownloadInterface
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(DownloadInterface, 'get_tasks', lambda self: None)
    page = DownloadInterface()
    tasks = []
    for i, state in enumerate([DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.MERGING]):
        task = TaskInfo()
        task.Basic.task_id = str(i)
        task.Download.status = state
        tasks.append(task)
    page.downloading_list_view._source_model.appendRows(tasks)
    from PySide6.QtTest import QTest
    page.queue_summary.buttons[3].click()
    QTest.qWait(100)
    assert page.downloading_list_view._model.rowCount() == 1
    assert page.downloading_list_view.status_filter == frozenset({DownloadStatus.PAUSED})
    page.queue_summary.buttons[0].click()
    QTest.qWait(100)
    assert page.downloading_list_view._model.rowCount() == 3
    assert app is not None
    page.close()
