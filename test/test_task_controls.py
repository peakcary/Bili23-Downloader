from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from util.common.enum import DownloadStatus as S
from util.download.task.info import TaskInfo
from gui.component.download_list.model import DownloadListModel
from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager


def test_individual_and_batch_retry_persist_queue_and_reset_budget(monkeypatch):
    app = QApplication.instance() or QApplication([])
    saved, reset = [], []
    tasks = [TaskInfo(), TaskInfo()]
    tasks[0].Download.status = S.FAILED
    tasks[1].Download.status = S.FFMPEG_FAILED
    model = DownloadListModel(tasks)
    monkeypatch.setattr(model, 'manageConcurrentDownloads', lambda: None)
    monkeypatch.setattr(task_manager, 'update_async', lambda task: saved.append(task.Download.status))
    monkeypatch.setattr(downloader_manager, 'get', lambda task, **kw: SimpleNamespace(reset_retry_budget=lambda: reset.append(task)))
    model.togglePauseResume(tasks[0])
    model.batchStart([tasks[1]])
    assert saved == [S.QUEUED, S.FFMPEG_QUEUED]
    assert reset == tasks
    assert app is not None


def test_batch_pause_persists_tasks_without_live_downloader(monkeypatch):
    app = QApplication.instance() or QApplication([])
    task = TaskInfo()
    task.Download.status = S.QUEUED
    model = DownloadListModel([task])
    saved = []
    monkeypatch.setattr(downloader_manager, 'get', lambda *args, **kw: None)
    monkeypatch.setattr(task_manager, 'update_async', lambda task: saved.append(task.Download.status))
    model.batchPause()
    assert task.Download.status == S.PAUSED
    assert saved == [S.PAUSED]
    assert app is not None


def test_single_resume_respects_existing_concurrency_limit(monkeypatch):
    from util.common.config import config
    app = QApplication.instance() or QApplication([])
    running, paused = TaskInfo(), TaskInfo()
    running.Download.status = S.DOWNLOADING
    paused.Download.status = S.PAUSED
    model = DownloadListModel([running, paused])
    get = config.get
    monkeypatch.setattr(config, 'get', lambda item: 1 if item is config.download_parallel else get(item))
    monkeypatch.setattr(task_manager, 'update_async', lambda task: None)
    monkeypatch.setattr(downloader_manager, 'get', lambda task, **kw: None)
    model.togglePauseResume(paused)
    assert paused.Download.status == S.QUEUED
    assert running.Download.status == S.DOWNLOADING
    assert app is not None
