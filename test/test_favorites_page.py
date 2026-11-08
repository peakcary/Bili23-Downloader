from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator
from PySide6.QtTest import QTest
import pytest


@pytest.fixture
def window(monkeypatch):
    import res.resources_rc  # noqa: F401
    from gui.interface.main_window import MainWindow
    from gui.interface.parse import ParseInterface
    from gui.interface.favorites import FavoritesInterface
    from util.common.config import config
    from util.common.runtime import runtime
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(MainWindow, 'init_utils', lambda self: None)
    monkeypatch.setattr(MainWindow, 'apply_window_state', lambda self, **kw: None)
    monkeypatch.setattr(ParseInterface, 'init_utils', lambda self: None)
    monkeypatch.setattr(FavoritesInterface, 'load', lambda self: None)
    get = config.get
    monkeypatch.setattr(config, 'get', lambda item: True if item is config.is_login else get(item))
    monkeypatch.setattr(runtime.auth, 'is_expired', False)
    translator = QTranslator()
    translator.load('src/res/i18n/bili23.zh_CN.qm')
    app.installTranslator(translator)
    win = MainWindow()
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    yield win
    win.hide()
    win.deleteLater()
    app.removeTranslator(translator)
    QApplication.restoreOverrideCursor()


@pytest.mark.parametrize('width,height', [(950, 600), (1200, 800)])
def test_favorites_stays_inside_main_content_and_preserves_category(window, width, height):
    window.resize(width, height)
    window.show_favorites_page()
    page = window.favorites_interface
    page.content.favorite_widget.update_list([{'title': '默认收藏夹', 'count': 2, 'url': 'https://example.invalid', 'cover': ''}])
    window.show()
    QTest.qWait(350)
    assert window.stackedWidget.currentWidget() is page
    assert not page.isWindow()
    assert not page.content.isWindow()
    assert page.content.width() <= page.width()
    assert page.content.height() <= page.height()
    assert page.rect().contains(page.content.geometry())
    window.grab().save(f'/tmp/bili-favorites-{width}.png')
    page.content.stack_widget.setCurrentWidget(page.content.follow_widget)
    window.switchTo(window.parse_interface)
    window.show_favorites_page()
    assert window.favorites_interface is page
    assert page.content.stack_widget.currentWidget() is page.content.follow_widget


def test_selecting_favorite_returns_to_parser(window, monkeypatch):
    urls = []
    monkeypatch.setattr(window.parse_interface, 'reparse', urls.append)
    window.show_favorites_page()
    window.favorites_interface.content.on_parse_url('bili23://watch_later')
    assert urls == ['bili23://watch_later']
    assert window.stackedWidget.currentWidget() is window.parse_interface
    assert window.current_route_key == 'ParseInterface'


def test_login_required_does_not_create_or_open_favorites(window, monkeypatch):
    from types import SimpleNamespace
    import qfluentwidgets
    from util.common.config import config
    get = config.get
    monkeypatch.setattr(config, 'get', lambda item: False if item is config.is_login else get(item))
    monkeypatch.setattr(qfluentwidgets, 'MessageBox', lambda **kw: SimpleNamespace(
        hideCancelButton=lambda: None, exec=lambda: None))
    window.show_favorites_page()
    assert window.favorites_interface is None
    assert window.stackedWidget.currentWidget() is window.parse_interface
