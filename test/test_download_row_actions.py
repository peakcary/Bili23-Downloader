from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem, QWidget


def test_more_button_opens_menu_without_canceling_task():
    from gui.component.download_list.item_delegate import DownloadItemDelegate
    from gui.component.download_list.model import DownloadListModel
    from util.download.task.info import TaskInfo
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    delegate = DownloadItemDelegate(parent)
    task = TaskInfo()
    model = DownloadListModel([task])
    index = model.index(0)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 750, 100)
    point = QPointF(delegate.uiRect.getDeleteButtonRect(option).center())
    event = QMouseEvent(QEvent.Type.MouseButtonRelease, point, point,
                        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier)
    opened = []
    delegate.contextMenuRequested.connect(lambda idx, pos: opened.append(idx))
    assert delegate._pressEvent(option, index, event)
    assert opened == [index]
    assert model.rowCount() == 1
    assert app is not None
