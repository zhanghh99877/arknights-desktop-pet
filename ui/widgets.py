"""共享输入控件：禁用滚轮改值的下拉框 / 数字框。

滚轮事件交给外层滚动区，避免滚动页面时误改选项。
"""

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox


class NoWheelComboBox(QComboBox):
    """下拉框不吃滚轮：事件交给外层滚动区，避免滚动页面时误改选项。

    minimumContentsLength 让最小宽度跟内容解耦（动画名很长也不会把
    表单撑出横向溢出），空间不足时自动省略显示。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumContentsLength(8)
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)

    def wheelEvent(self, e):
        e.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """同上：数字框也不吃滚轮。"""

    def wheelEvent(self, e):
        e.ignore()
