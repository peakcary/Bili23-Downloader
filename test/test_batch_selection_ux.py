import pytest
from PySide6.QtWidgets import QApplication, QWidget


@pytest.mark.parametrize('text, expected', [('1， 3, 5-7, 3', [1, 3, 5, 6, 7]), (' 2 - 4 ', [2, 3, 4])])
def test_range_preview_deduplicates(text, expected):
    from gui.dialog.misc.batch_select import BatchSelectDialog
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    dialog = BatchSelectDialog(parent, range(1, 11))
    dialog.lines_box.setText(text)
    assert dialog.to_number_list() == expected
    assert dialog.yesButton.isEnabled()
    assert str(len(expected)) in dialog.preview_lab.text()
    assert app is not None
    parent.close()


@pytest.mark.parametrize('text', ['', '1-2-3', '0', '3-1', '11', '1,', '1-99999999999999999', '-2'])
def test_invalid_ranges_disable_submission(text):
    from gui.dialog.misc.batch_select import BatchSelectDialog
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    dialog = BatchSelectDialog(parent, range(1, 11))
    dialog.lines_box.setText(text)
    assert not dialog.yesButton.isEnabled()
    with pytest.raises(ValueError):
        dialog.to_number_list()
    assert app is not None
    parent.close()


def test_batch_scope_tracks_filtered_rows(monkeypatch):
    from PySide6.QtTest import QTest
    from gui.interface.download import DownloadInterface
    from util.download.task.info import TaskInfo
    from util.common.enum import DownloadStatus
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(DownloadInterface, 'get_tasks', lambda self: None)
    page = DownloadInterface()
    view = page.downloading_list_view
    view.setAutoManageConcurrentTasks(False)
    tasks = []
    for i, state in enumerate([DownloadStatus.PAUSED, DownloadStatus.FAILED]):
        task = TaskInfo()
        task.Basic.task_id = f'ux-{i}'
        task.Download.status = state
        tasks.append(task)
    view.addTask(tasks)
    QTest.qWait(100)
    assert '(2)' in page.top_stacked_widget.start_all_btn.text()
    view.setStatusFilter({DownloadStatus.PAUSED})
    QTest.qWait(100)
    assert '(1)' in page.top_stacked_widget.start_all_btn.text()
    view.setStatusFilter({DownloadStatus.DOWNLOADING})
    QTest.qWait(100)
    assert not page.top_stacked_widget.start_all_btn.isEnabled()
    assert not page.top_stacked_widget.clear_all_btn.isEnabled()
    assert app is not None
    page.close()
