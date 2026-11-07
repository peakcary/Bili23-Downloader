import re

from qfluentwidgets import SubtitleLabel, LineEdit, BodyLabel

from gui.component.widget.label import TipBodyLabel
from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory
from util.common.translator import Translator

class BatchSelectDialog(DialogBase):
    def __init__(self, parent = None, available_numbers = None):
        super().__init__(parent)

        self.available_numbers = set(available_numbers) if available_numbers is not None else None
        self.init_UI()

        self.number_list = []

    def init_UI(self):
        self.caption_label = SubtitleLabel(self.tr("Batch Selection"), parent = self)

        self.lines_box = LineEdit(parent = self)
        self.lines_box.setPlaceholderText(self.tr("Enter line numbers (e.g. 1,3,5-10)"))
        self.lines_box.setClearButtonEnabled(True)

        self.tip_lab = TipBodyLabel(Translator.BATCH_SELECT_GUIDE(), parent = self)

        self.viewLayout.addWidget(self.caption_label)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.lines_box)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.tip_lab)
        self.scope_lab = BodyLabel(self.tr("Uses list row numbers, not episode numbers. Existing selections are kept."), self)
        self.scope_lab.setWordWrap(True)
        self.preview_lab = BodyLabel(self)
        self.viewLayout.addWidget(self.scope_lab)
        self.viewLayout.addWidget(self.preview_lab)
        self.lines_box.textChanged.connect(self.update_preview)
        self.update_preview()

        self.widget.setMinimumWidth(500)

    def accept(self):
        self.number_list = self.to_number_list()

        return super().accept()
    
    def to_number_list(self):
        text = self.lines_box.text().strip().replace("，", ",")
        if not text:
            raise ValueError(self.tr("Please enter line numbers"))
        numbers = set()
        for part in text.split(","):
            match = re.fullmatch(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?", part)
            if not match or len(match[1]) > 8 or (match[2] and len(match[2]) > 8):
                raise ValueError(self.tr("Invalid line number range"))
            start, end = int(match[1]), int(match[2] or match[1])
            if start <= 0 or end < start or end - start > 100000:
                raise ValueError(self.tr("Invalid line number range"))
            selected = set(range(start, end + 1))
            if self.available_numbers is not None and not selected <= self.available_numbers:
                raise ValueError(self.tr("Some row numbers are not in the current list"))
            numbers.update(selected)
        return sorted(numbers)

    def update_preview(self):
        try:
            numbers = self.to_number_list()
        except ValueError as error:
            self.preview_lab.setText(str(error))
            self.yesButton.setEnabled(False)
        else:
            self.preview_lab.setText(self.tr("Select {count} rows (duplicates excluded)").format(count=len(numbers)))
            self.yesButton.setEnabled(True)
        self.lines_box.setError(False)

    def validate(self):
        try:
            self.to_number_list()
        except ValueError as error:
            self.lines_box.setFocus()
            self.lines_box.setError(True)
            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", str(error))
            return False
        return True
