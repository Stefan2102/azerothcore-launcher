from __future__ import annotations



from PySide6.QtCore import QSize, Qt, Signal

from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget



from core.service_controller import ServiceId

from ui.icons import make_icon

from ui.logo import render_logo_pixmap





SIDEBAR_WIDTH = 360

SIDEBAR_H_MARGIN = 10

SIDEBAR_V_MARGIN = 12

LOGO_EDGE_PADDING = 20

BUTTON_SPACING = 8

SIDEBAR_BUTTON_HEIGHT = 50

SIDEBAR_ICON_SIZE = 24





# ==========================================

# ACTION BUTTON

# ==========================================





class SideAction(QPushButton):

    def __init__(self, service_id: ServiceId, title: str, icon_kind: str, accent: str, parent: QWidget | None = None) -> None:

        super().__init__(parent)

        self.service_id = service_id

        self._title = title

        self._icon_kind = icon_kind

        self._accent = accent

        self.setObjectName("SideAction")

        self.setProperty("accent", accent)

        self.setProperty("running", False)

        self.setIcon(make_icon(icon_kind, accent))

        self.setIconSize(QSize(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE))

        self.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._refresh_text(False)



    def set_running(self, running: bool) -> None:

        self.setProperty("running", running)

        self._refresh_text(running)

        self.style().unpolish(self)

        self.style().polish(self)



    def _refresh_text(self, running: bool) -> None:

        action = "Stop" if running else "Start"

        self.setText(f"  {action} {self._title}")





def _make_sidebar_button(

    parent: QWidget,

    object_name: str,

    text: str,

    icon_kind: str,

    icon_color: str = "ice",

) -> QPushButton:

    button = QPushButton(text, parent)

    button.setObjectName(object_name)

    button.setIcon(make_icon(icon_kind, icon_color))

    button.setIconSize(QSize(SIDEBAR_ICON_SIZE, SIDEBAR_ICON_SIZE))

    button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)

    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    return button





# ==========================================

# SIDEBAR

# ==========================================





class Sidebar(QFrame):

    service_requested = Signal(object)

    wow_requested = Signal()

    settings_requested = Signal()

    exit_requested = Signal()



    def __init__(self, parent: QWidget | None = None) -> None:

        super().__init__(parent)

        self.setObjectName("Sidebar")

        self.setFixedWidth(SIDEBAR_WIDTH)

        self._buttons: dict[ServiceId, SideAction] = {}

        self._build_ui()



    def set_service_running(self, service_id: ServiceId, running: bool) -> None:

        button = self._buttons.get(service_id)

        if button:

            button.set_running(running)



    def _logo_width(self) -> int:

        return SIDEBAR_WIDTH - (2 * SIDEBAR_H_MARGIN)



    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        layout.setContentsMargins(SIDEBAR_H_MARGIN, 0, SIDEBAR_H_MARGIN, SIDEBAR_V_MARGIN)
        layout.setSpacing(0)

        layout.addSpacing(LOGO_EDGE_PADDING)

        logo = QLabel(self)
        logo.setObjectName("Logo")
        logo_pixmap = render_logo_pixmap(self._logo_width())
        logo.setPixmap(logo_pixmap)
        logo.setScaledContents(False)
        logo.setFixedSize(logo_pixmap.size())
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(LOGO_EDGE_PADDING)

        button_group = QWidget(self)
        button_group.setObjectName("SidebarButtonGroup")
        button_layout = QVBoxLayout(button_group)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(BUTTON_SPACING)

        self._add_service_action(button_layout, ServiceId.MYSQL, "MySQL", "database", "ice")
        self._add_service_action(button_layout, ServiceId.AUTHSERVER, "Authserver", "shield", "ice")
        self._add_service_action(button_layout, ServiceId.WORLDSERVER, "Worldserver", "globe", "ice")
        self._add_service_action(button_layout, ServiceId.OLLAMA, "Ollama", "spark", "ice")

        wow_button = _make_sidebar_button(
            self,
            "WowButton",
            "  Launch World of Warcraft",
            "sword",
            "ice",
        )
        wow_button.clicked.connect(self.wow_requested)
        button_layout.addWidget(wow_button)

        layout.addWidget(button_group)
        layout.addStretch(1)

        footer_group = QWidget(self)
        footer_group.setObjectName("SidebarFooterGroup")
        footer_layout = QVBoxLayout(footer_group)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(BUTTON_SPACING)

        settings_button = _make_sidebar_button(self, "SettingsButton", "  Settings", "settings", "ice")
        settings_button.clicked.connect(self.settings_requested.emit)
        footer_layout.addWidget(settings_button)

        exit_button = _make_sidebar_button(self, "ExitButton", "  Exit", "power", "ice")
        exit_button.clicked.connect(self.exit_requested)
        footer_layout.addWidget(exit_button)

        layout.addWidget(footer_group)



    def _add_service_action(

        self,

        layout: QVBoxLayout,

        service_id: ServiceId,

        title: str,

        icon_kind: str,

        accent: str,

    ) -> None:

        button = SideAction(service_id, title, icon_kind, accent, self)

        button.clicked.connect(lambda checked=False, sid=service_id: self.service_requested.emit(sid))

        self._buttons[service_id] = button

        layout.addWidget(button)

