"""Favorites live inside the main stack, not in a fixed-size popup."""
from PySide6.QtWidgets import QFrame, QVBoxLayout
from gui.component.widget.page_header import PageHeader
from gui.component.widget.flyout import FavoriteFlyoutWidget


class FavoritesInterface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('favorite')
        self.content = FavoriteFlyoutWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(PageHeader(self.tr('Favorites'),
                                    self.tr('Browse your saved content and select an item to parse.'), self))
        layout.addWidget(self.content, 1)

    def load(self):
        self.content.init_flyout()
