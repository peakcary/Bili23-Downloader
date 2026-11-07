from PySide6.QtWidgets import QWidget
from qfluentwidgets import FlowLayout, CaptionLabel

from gui.component.widget.label import TipCaptionLabel

class DownloadPreviewBar(QWidget):
    """
    使用中性文字和可换行布局预览内容，强调色留给提交操作。
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        self.tip_label = TipCaptionLabel(self.tr("Will download:"), self)

        # 文件类型用文字区分，避免无状态语义的多色标签。
        tag_info = [
            ("video", self.tr("Video")),
            ("audio", self.tr("Audio")),
            ("danmaku", self.tr("Danmaku")),
            ("subtitle", self.tr("Subtitles")),
            ("cover", self.tr("Cover")),
            ("chapter", self.tr("Chapters")),
            ("metadata", self.tr("Metadata"))
        ]

        self.tag_map = {key: CaptionLabel(text, self) for key, text in tag_info}

        # 未选择任何内容时显示占位提示。
        self.empty_tag = CaptionLabel(self.tr("Nothing selected"), self)

        main_layout = FlowLayout(self, needAni=False)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setHorizontalSpacing(12)
        main_layout.setVerticalSpacing(4)
        main_layout.addWidget(self.tip_label)

        for tag in self.tag_map.values():
            main_layout.addWidget(tag)

        main_layout.addWidget(self.empty_tag)


    def update_preview(self, state: dict):
        for key, tag in self.tag_map.items():
            tag.setVisible(state.get(key, False))

        self.empty_tag.setVisible(not any(state.values()))
