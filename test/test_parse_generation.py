"""Paused or superseded parsing must never overwrite a resumed task."""
from threading import Event
import pytest
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication
from util.common._json import dumps, loads
from util.download.task.info import TaskInfo
from util.download.downloader.parse_worker import ParseWorker
from util.download.downloader.downloader import Downloader


@pytest.fixture
def downloader(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(Downloader, 'init_session', lambda self: setattr(self, 'session', None))
    instance = Downloader(TaskInfo())
    instance._parse_generation = 2
    instance._parse_result_pending = True
    yield instance
    assert app is not None
    instance.speed_timer.stop()
    instance._retry_timer.stop()


def test_old_success_and_failure_cannot_overwrite_new_run(downloader, monkeypatch):
    accepted = []
    monkeypatch.setattr(downloader, 'on_parse_finished', lambda data: accepted.append(data))
    monkeypatch.setattr(downloader, 'on_parse_error', lambda data: accepted.append(data))
    downloader.on_parse_result(dumps({'generation': 1}))
    downloader.on_parse_failure(dumps({'generation': 1, 'message': 'old failure'}))
    assert accepted == []
    assert downloader._parse_result_pending
    downloader.on_parse_failure(dumps({'generation': 2, 'message': 'current failure'}))
    downloader.on_parse_failure(dumps({'generation': 2, 'message': 'duplicate'}))
    assert accepted == ['current failure']


def test_worker_snapshot_and_real_queued_success_delivery(downloader, monkeypatch):
    app = QApplication.instance()
    task = downloader.task_info
    task.Download.video_quality_id = 80
    old_stop = Event()
    worker = ParseWorker(task, downloader, stop_event=old_stop, generation=2)
    worker.task_info.Download.video_quality_id = 120
    worker.task_info.File.relative_files.append('video.m4s')
    assert task.Download.video_quality_id == 80
    assert task.File.relative_files == []
    task.File.relative_files.append('cover.jpg')
    received = []
    monkeypatch.setattr(worker, 'get_info', lambda: None)
    monkeypatch.setattr(worker, 'parse_download_info', lambda: {'total_size': 1024})
    monkeypatch.setattr(downloader, 'on_parse_finished', lambda data: received.append(loads(data)))
    worker.run_with_retry()
    app.processEvents()
    assert task.Download.video_quality_id == 120
    assert task.File.relative_files == ['cover.jpg', 'video.m4s']
    assert received == [{'total_size': 1024}]


def test_cancelled_worker_cannot_emit_failure_after_resume(downloader):
    class Receiver(QObject):
        def __init__(self):
            super().__init__()
            self.errors = []

        @Slot(str)
        def on_parse_failure(self, payload):
            self.errors.append(payload)

    receiver = Receiver()
    old_stop = Event()
    worker = ParseWorker(TaskInfo(), receiver, stop_event=old_stop, generation=1)
    old_stop.set()
    downloader._stop_event.clear()  # Resuming a download does not clear old parse cancellation.
    downloader._parse_stop_event = Event()
    worker.on_parse_error('late failure')
    QApplication.instance().processEvents()
    assert receiver.errors == []


def test_start_pause_start_keeps_old_request_cancelled(downloader, monkeypatch):
    from util.common.enum import DownloadType
    from util.download.task.manager import task_manager
    from util.thread.pool import GlobalThreadPoolTask
    workers = []
    downloader.task_info.Download.type = DownloadType.VIDEO
    monkeypatch.setattr(GlobalThreadPoolTask, 'run', lambda worker: workers.append(worker))
    monkeypatch.setattr(task_manager, 'update_async', lambda task: None)
    try:
        downloader.start()
        downloader.pause()
        downloader.start()
        assert len(workers) == 2
        assert workers[0].stop_event.is_set()
        assert not workers[1].stop_event.is_set()
        assert workers[1].generation > workers[0].generation
        downloader.on_parse_failure(dumps({'generation': workers[0].generation, 'message': 'late'}))
        assert downloader._parse_result_pending
    finally:
        for worker in workers:
            worker.on_finished()
