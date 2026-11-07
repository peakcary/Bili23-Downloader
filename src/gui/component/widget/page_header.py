"""Shared page heading: one title and a restrained supporting line."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from qfluentwidgets import SubtitleLabel, CaptionLabel


class PageHeader(QWidget):
    def __init__(self, title, description, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.title = SubtitleLabel(title, self)
        self.description = CaptionLabel(description, self)
        self.description.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addWidget(self.description)
