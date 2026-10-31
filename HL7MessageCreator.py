import html
import os
import random
import re
import sys
from datetime import datetime, timedelta

import pandas as pd
from hl7apy.exceptions import ValidationError
from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QKeySequence, QPainter, QPalette, QTextCharFormat, QTextCursor, QTextFormat
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

BG_COLOR = "#1F2139"
TEXT_COLOR = "#FFFFFF"
PREVIEW_BG = "#1E1E1E"
TITLE_HL7_MSG = "#465BE7"
TITLE_CREATOR = "#7DCAE3"
DITHERED_TEXT = "#808080"
MATCH_BG = "#2C3DAA"
SELECTED_MATCH_BG = "#465BE7"
BUTTON_BG = "#2A2C4A"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = SCRIPT_DIR

ENCOUNTER_OPTIONS = {
    "Emergent": "E",
    "Day Surgery": "DS",
    "Observation": "OBS",
    "Inpatient": "IP",
    "Trauma": "T",
    "Radiology": "Rad",
}
MESSAGE_TYPES = ["Scheduled", "Scheduled & Case Events", "Scheduled & Canceled"]

default_hl7 = r"""
MSH|^~\&|EPIC|NC||NC|{YYYYMMDD}{eventTime}||SIU^{triggerEvent}|{patientMRN}|P|2.5
SCH||{patientMRN}|||||||{duration}|M|^^^{YYYYMMDD}{scheduledTime}
ZCS||{addOn}|ORSCH_S14||||{cptCode}^{procedure}^CPT
PID|1||{patientMRN}^^^MRN^MRN||{patientLastName}^{patientFirstName}||{patientDOB}|{patientGender}|{patientLastName}^{patientFirstName}^^|||||||||{patientMRN}
PV1||{encounterType}|NC-PERIOP^^^NC|||||||{specialty}|||||||||{patientMRN}
RGS|
OBX|1|DTM|{caseEvent}|In|{YYYYMMDD}{eventTime}|||||||||{YYYYMMDD}{eventTime}||||||||||||||||||
AIS|1||{procedureId}^{procedure}|{YYYYMMDD}{scheduledTime}|0|M|{duration}|M||||2
NTE|1||{procedureDescription}|Procedure Description|||
NTE|2||{specialNeeds}|Case Notes|||
AIL|1||^{locationOR}^^{locationDepartment}
AIP|1||{surgeonID}^{primaryLastName}^{primaryFirstName}^W^^^^^EPIC^^^^PROVID|1.1^Primary|{specialty}|{YYYYMMDD}{scheduledTime}|0|M|{duration}|M
AIP|2||{staffID}^{lastName}^{firstName}^^^^^^EPIC^^^^PROVID|4.20^Circulator||{YYYYMMDD}{scheduledTime}|0|M|{duration}|M
AIP|3||{staffID}^{lastName}^{firstName}^^^^^^^EPIC^^^^PROVID|4.150^Scrub||{YYYYMMDD}{scheduledTime}|0|M|{duration}|M
AIP|4||{staffID}^{lastName}^{firstName}^^^^^^^EPIC^^^^PROVID|2.20^ANE CRNA||{YYYYMMDD}{scheduledTime}|0|M|{duration}|M
AIP|5||{staffID}^{lastName}^{firstName}^^^^^^^EPIC^^^^PROVID|2.139^Anesthesiologist||{YYYYMMDD}{scheduledTime}|0|M|{duration}|M
"""

adt_template = r"""
MSH|^~\&|EPIC|NC||NC|{YYYYMMDD}{eventTime}||ADT^A01||P|2.5
EVN|A01|{YYYYMMDD}{eventTime}|
PID|1||{patientMRN}^^^MRN^MRN||{patientLastName}^{patientFirstName}||{patientDOB}|{patientGender}||||||||||{patientMRN}
PV1||{encounterType}|NC-PERIOP^^^NC||||||||||||||||{patientMRN}|||||||||||||||||||||||||{YYYYMMDD}{eventTime}
PV2|||||||
{AL1_segments}
"""

case_events = [
    ("arrive", -60),
    ("in_preop", -45),
    ("out_preop", -15),
    ("planned_preop", -45),
    ("setup", 0),
    ("intraop", 10),
    ("started", 15),
    ("closing", "duration-30"),
    ("complete", "duration-15"),
    ("exiting", "duration-10"),
    ("ordered_pacu", "exiting-5"),
    ("planned_pacu", "exiting-5"),
    ("in_pacu", "exiting+5"),
    ("out_pacu", "in_pacu+60"),
]

base_prompts = [
    {"prompt": "Patient First Name:", "key": "{patientFirstName}"},
    {"prompt": "Patient Last Name:", "key": "{patientLastName}"},
    {"prompt": "Patient Gender (M/F):", "key": "{patientGender}"},
    {"prompt": "Patient DOB (YYYYMMDD):", "key": "{patientDOB}"},
    {"prompt": "Patient MRN:", "key": "{patientMRN}"},
    {"prompt": "Encounter Type:", "key": "{encounterType}"},
    {"prompt": "Scheduled Date (YYYYMMDD):", "key": "{YYYYMMDD}"},
    {"prompt": "Scheduled Time (HHMMSS):", "key": "{scheduledTime}"},
    {"prompt": "Duration (minutes):", "key": "{duration}"},
    {"prompt": "Procedure:", "key": "{procedure}"},
    {"prompt": "Procedure ID:", "key": "{procedureId}"},
    {"prompt": "CPT Code:", "key": "{cptCode}"},
    {"prompt": "Procedure Description:", "key": "{procedureDescription}"},
    {"prompt": "Special Needs:", "key": "{specialNeeds}"},
    {"prompt": "Location Department:", "key": "{locationDepartment}"},
    {"prompt": "Location OR:", "key": "{locationOR}"},
    {"prompt": "Add On (Y/N):", "key": "{addOn}"},
]

procedure_fields = [
    {"prompt": "Procedure:", "key": "{procedure}"},
    {"prompt": "Procedure ID:", "key": "{procedureId}"},
    {"prompt": "Procedure Description:", "key": "{procedureDescription}"},
    {"prompt": "Special Needs:", "key": "{specialNeeds}"},
]

HELP_CONTENT = """
HL7 Message Creator and Editor - User Manual

**Table of Contents**
- [Introduction](#introduction)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Getting Started](#getting-started)
- [Creator Mode](#creator-mode)
  - [Creating a New Patient](#creating-a-new-patient)
  - [Filling Patient Details](#filling-patient-details)
  - [Managing Procedures](#managing-procedures)
  - [Managing Allergies](#managing-allergies)
  - [Assigning Staff and Surgeons](#assigning-staff-and-surgeons)
  - [Generating and Saving Messages](#generating-and-saving-messages)
- [Editor Mode](#editor-mode)
  - [Opening HL7 Files](#opening-hl7-files)
  - [Navigating Messages](#navigating-messages)
  - [Editing Messages](#editing-messages)
  - [Saving Changes](#saving-changes)
- [Tips for Effective Use](#tips-for-effective-use)

**Introduction** #introduction
The HL7 Message Creator and Editor is a user-friendly tool designed to generate and modify HL7 messages for healthcare scheduling and case events. It offers two modes: **Creator Mode** for building new messages and **Editor Mode** for modifying existing ones. This manual provides step-by-step guidance to help new users master the application.

**Keyboard Shortcuts** #keyboard-shortcuts
The following shortcuts enhance your workflow:
- **Ctrl+N**: Create a new patient (Creator Mode only)
- **Ctrl+O**: Open HL7 file(s) (Editor Mode only)
- **Ctrl+S**: Save changes
- **Ctrl+Shift+S**: Save and exit
- **Ctrl+Q**: Quit the application
- **Ctrl+E**: Switch to Editor Mode
- **Ctrl+R**: Switch to Creator Mode

**Getting Started** #getting-started
1. Launch the application to enter **Creator Mode** by default.
2. Use the **File** menu or **View** menu to switch between modes or perform actions like saving or quitting.
3. Ensure required CSV files (`procedures.csv`, `staff_names.csv`, `surgeon_names.csv`, `patient_names.csv`, `allergies.csv`) are in the same directory as the script for data population.
4. Familiarize yourself with the interface: the left panel (Creator Mode) includes a procedure browser, while the right panel displays input fields and a preview area.

**Creator Mode** #creator-mode
Creator Mode allows you to generate HL7 messages for new patients.

*Creating a New Patient* #creating-a-new-patient
- Select **File > New Patient** or press **Ctrl+N** to start.
- A blank patient form appears, ready for data entry.
- Use the **Random Patient** button to auto-fill fields with sample data for testing.

*Filling Patient Details* #filling-patient-details
- Enter patient information such as **First Name**, **Last Name**, **Gender**, **DOB**, and **MRN** in the provided fields.
- Use buttons for convenience:
  - **Random Name**: Populate names from `patient_names.csv`.
  - **Random DOB**: Generate a random date of birth.
  - **Age/Add**: Set DOB based on a specified age (0–85).
  - **Date Buttons**: Set the scheduled date to -1 Day, Today, or +1 Day.
  - **Time Buttons**: Adjust the scheduled time by -1 Hour, Now, or +1 Hour.
- Select an **Encounter Type** (e.g., Inpatient, Emergent) via radio buttons.
- Specify the **Message Type** (Scheduled, Scheduled & Case Events, or Scheduled & Canceled) to define the output messages.

*Managing Procedures* #managing-procedures
- Click **Browse Procedures** to open the procedure browser.
- Search or navigate specialties and categories to select a procedure, which auto-fills fields like **Procedure**, **ID**, **CPT Code**, and **Description**.
- Use **Choose Random** in the browser or **Add Procedure** to include additional procedures.
- Remove the last procedure with **Remove Last Procedure** if needed.

*Managing Allergies* #managing-allergies
- Click **Browse Allergies** to open the allergy browser.
- Select allergies from the list to include in the patient's ADT message.
- The selected allergies will be displayed in the Allergies field.

*Assigning Staff and Surgeons* #assigning-staff-and-surgeons
- Assign a **Primary Surgeon** and fixed roles (Circulator, Scrub, CRNA, Anesthesiologist) using the input fields.
- Click **Random Surgeon** or **Random Staff** to populate from `surgeon_names.csv` or `staff_names.csv`.
- Add extra surgeons or staff with **Add Surgeon** or **Add Staff Member**; remove them with **Remove Last Surgeon** or **Remove Last Staff Member**.
- Enter custom roles for additional staff as needed.

*Generating and Saving Messages* #generating-and-saving-messages
- Click **Create** to generate HL7 messages based on the input data and selected message type.
- Preview the generated message in the text area below the input fields.
- Save messages via **File > Save** (Ctrl+S) or **Save & Exit** (Ctrl+Shift+S), selecting an output directory.
- Messages are saved as `.hl7` files, named with the patient’s name and a sequence number (e.g., `JohnDoe-00.hl7`).

**Editor Mode** #editor-mode
Editor Mode is used to modify existing HL7 messages.

*Opening HL7 Files* #opening-hl7-files
- Switch to Editor Mode via **View > Editor** (Ctrl+E).
- Select **File > Open File(s)** (Ctrl+O) to load `.hl7` files from a directory.
- Files are grouped by patient name, with messages sorted for easy navigation.

*Navigating Messages* #navigating-messages
- Use **Previous** and **Next** to cycle through messages within a patient block.
- Use **Previous Patient** and **Next Patient** to switch between patient blocks.
- The context label displays the current patient and message number.

*Editing Messages* #editing-messages
- **Field-Based Editing**: Modify fields like **Patient MRN**, **Location OR**, or **Location Department** in the input area. Changes are reflected in the preview and highlighted in the message text.
- **Direct Edit Mode**: Click **Direct Edit** to manually edit the message text.
  - Make changes directly in the preview area.
  - Save edits to the current message (**Save to Current**) or all messages in the patient block (**Save to All**).
- Apply field-based changes to the current message or all messages in the block using the **Apply** button and selecting **Current** or **All**.

*Saving Changes* #saving-changes
- Save edited messages via **File > Save** (Ctrl+S) or **Save & Exit** (Ctrl+Shift+S).
- Choose an output directory to store the modified `.hl7` files.
- Validation checks are performed during direct edits, with warnings for any HL7 parsing errors.

**Tips for Effective Use** #tips-for-effective-use
- **Validate Inputs**: Ensure fields like dates (YYYYMMDD) and times (HHMMSS) are correctly formatted to avoid errors.
- **Use Random Features**: Leverage random buttons to quickly populate test data during development.
- **Backup Files**: Save frequently to prevent data loss, as unsaved changes are lost on quit (Ctrl+Q).
- **Procedure Browser**: Use the search function to quickly find procedures by name, CPT code, or specialty.
- **Direct Edit Caution**: Be cautious in Direct Edit Mode, as invalid HL7 syntax may cause parsing errors.
- **CSV Maintenance**: Keep CSV files updated with accurate procedure and staff data for reliable randomization.

For further assistance, contact the application support team or refer to the **Help > About** section for version and author details.
"""

def is_valid_time(time_str):
    if not time_str:
        return False
    try:
        datetime.strptime(time_str, "%H%M%S")
        return True
    except ValueError:
        return False


def cell(value):
    """CSV values as text. Empty cells stay empty instead of becoming 'nan'."""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return "" if value is None else str(value)


class Var(QObject):
    """String value with the same get/set role as a Tk StringVar."""

    changed = pyqtSignal()

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self._value = "" if value is None else str(value)

    def get(self):
        return self._value

    def set(self, value):
        value = "" if value is None else str(value)
        if value == self._value:
            return
        self._value = value
        self.changed.emit()


class ProcedureGroup(QGroupBox):
    """Fieldset around one procedure. The dark Fusion group box border is too faint."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        layout = QVBoxLayout(self)
        # The group box already insets the title. A full line here leaves a blank row under it.
        layout.setContentsMargins(12, 2, 12, 8)

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        title = self.title()
        title_width = metrics.horizontalAdvance(title)
        top = max(metrics.ascent() // 2, 1)
        bounds = self.rect().adjusted(1, top, -2, -2)
        painter.fillRect(self.rect(), QColor(BG_COLOR))
        painter.setPen(QColor(TITLE_HL7_MSG))
        gap_left = bounds.left() + 10
        gap_right = gap_left + title_width + 8
        painter.drawLine(bounds.left(), bounds.top(), gap_left, bounds.top())
        painter.drawLine(gap_right, bounds.top(), bounds.right(), bounds.top())
        painter.drawLine(bounds.right(), bounds.top(), bounds.right(), bounds.bottom())
        painter.drawLine(bounds.left(), bounds.bottom(), bounds.right(), bounds.bottom())
        painter.drawLine(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
        painter.setPen(QColor(TEXT_COLOR))
        painter.drawText(gap_left + 4, bounds.top() + metrics.ascent() // 2, title)


class UpperLineEdit(QLineEdit):
    def __init__(self, uppercase=True, parent=None):
        super().__init__(parent)
        self._uppercase = uppercase
        self._var = None
        self.textEdited.connect(self._on_edited)

    def bind_var(self, var):
        if self._var is not None:
            try:
                self._var.changed.disconnect(self._from_var)
            except TypeError:
                pass
        self._var = var
        self.blockSignals(True)
        self.setText(var.get())
        self.blockSignals(False)
        var.changed.connect(self._from_var)

    def _from_var(self):
        if self._var is None:
            return
        text = self._var.get()
        if text == self.text():
            return
        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

    def _on_edited(self, text):
        if self._uppercase:
            upper = text.upper()
            if upper != text:
                position = self.cursorPosition()
                self.blockSignals(True)
                self.setText(upper)
                self.setCursorPosition(position)
                self.blockSignals(False)
                text = upper
        if self._var is not None:
            self._var.set(text)


def help_html():
    parts = [
        "<html><body style='background:#1E1E1E;color:#FFFFFF;"
        "font-family:Arial;font-size:14px;'>"
    ]
    for line in HELP_CONTENT.splitlines():
        stripped = line.strip()
        link = re.match(r"^- \[(.+?)\]\(#(.+?)\)$", stripped)
        if link:
            parts.append(f"<p style='margin-left:16px'><a href='#{link.group(2)}'>{html.escape(link.group(1))}</a></p>")
            continue
        section = re.match(r"^(.*?)\s+#([a-z0-9-]+)\s*$", stripped)
        if section:
            title = section.group(1).replace("**", "").replace("*", "")
            parts.append(f"<h3 id='{section.group(2)}'>{html.escape(title)}</h3>")
            continue
        if not stripped:
            continue
        text = html.escape(stripped)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        indent = 24 if stripped.startswith("- ") or stripped[:2].rstrip(".").isdigit() else 0
        parts.append(f"<p style='margin-left:{indent}px'>{text}</p>")
    parts.append("</body></html>")
    return "".join(parts)


class HL7MessageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.failed = False
        self.setWindowTitle("HL7 Message Creator")
        self.resize(1770, 1232)
        self.setMinimumSize(800, 600)
        self._loading = False
        self._suspend_preview = False
        self._allow_close = False
        self.mode = "Creator"

        self.patients = []
        self.current_patient_index = -1
        self.current_message_index = -1
        self.procedure_panel_visible = True
        self.procedure_frames = []
        self.patient_blocks = []
        self.edited_messages = {}
        self.last_mrn = 999
        self.matched_procedures = []
        self.current_match_index = -1
        self.autocomplete_suggestion = None
        self.direct_edit_mode = False
        self.message_backups = {}
        self.additional_staff = []
        self.additional_surgeons = []
        self.staff_entries = {}
        self.base_entries = {}
        self.creator_preview_text = None
        self.editor_preview_text = None
        self.allergy_browser_visible = False

        try:
            self.procedures = pd.read_csv(os.path.join(DATA_DIR, "procedures.csv"))
            self.staff_names = pd.read_csv(os.path.join(DATA_DIR, "staff_names.csv"))
            self.surgeon_names = pd.read_csv(os.path.join(DATA_DIR, "surgeon_names.csv"))
            self.patient_names = pd.read_csv(os.path.join(DATA_DIR, "patient_names.csv"))
            self.allergies = pd.read_csv(os.path.join(DATA_DIR, "allergies.csv"))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load CSV files: {exc}")
            self.failed = True
            return

        self._build_menu()
        central = QWidget()
        self.setCentralWidget(central)
        self.root_layout = QVBoxLayout(central)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.mode_host = QWidget()
        self.mode_layout = QVBoxLayout(self.mode_host)
        self.mode_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.addWidget(self.mode_host, 1)
        self._highlight_token = None
        self._highlight_proc_id = None
        self._highlight_staff_id = None
        self._highlight_staff_part = None
        self._shown_highlight_line = None
        self._extra_spans = []
        self._extra_lines = set()
        self.set_mode("Creator")

    def _var(self, value=""):
        var = Var(value, self)
        var.changed.connect(self.creator_update_preview)
        return var

    def _button(self, text, slot):
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    def _radio(self, text):
        button = QRadioButton(text)
        button.setStyleSheet(
            f"QRadioButton {{ color: {TEXT_COLOR}; background: transparent; }}"
            "QRadioButton::indicator {"
            "width: 8px; height: 8px; border-radius: 4px;"
            f"border: 1px solid {TITLE_HL7_MSG}; background: {PREVIEW_BG};"
            "}"
            "QRadioButton::indicator:checked {"
            f"border: 1px solid {TITLE_HL7_MSG}; background: {TITLE_HL7_MSG};"
            "}"
        )
        return button

    def _message_view(self):
        # NoWrap: HL7 lines stay intact, and a width change does not reflow the text.
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return view

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        self.action_new = file_menu.addAction("New Patient")
        self.action_new.setShortcut(QKeySequence("Ctrl+N"))
        self.action_new.triggered.connect(self.create_new_patient)
        self.action_open = file_menu.addAction("Open File(s)")
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_open.triggered.connect(self.open_files)
        action_save = file_menu.addAction("Save")
        action_save.setShortcut(QKeySequence("Ctrl+S"))
        action_save.triggered.connect(self.save_files)
        action_save_exit = file_menu.addAction("Save && Exit")
        action_save_exit.setShortcut(QKeySequence("Ctrl+Shift+S"))
        action_save_exit.triggered.connect(self.save_and_exit)
        action_quit = file_menu.addAction("Quit")
        action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        action_quit.triggered.connect(self.quit)

        view_menu = menu.addMenu("View")
        action_creator = view_menu.addAction("Creator")
        action_creator.setShortcut(QKeySequence("Ctrl+R"))
        action_creator.triggered.connect(lambda: self.set_mode("Creator"))
        action_editor = view_menu.addAction("Editor")
        action_editor.setShortcut(QKeySequence("Ctrl+E"))
        action_editor.triggered.connect(lambda: self.set_mode("Editor"))

        help_menu = menu.addMenu("Help")
        help_menu.addAction("Help", self.open_help)
        help_menu.addAction("About", self.show_about)

    def _clear_mode(self):
        self.creator_preview_text = None
        self.editor_preview_text = None
        while self.mode_layout.count():
            item = self.mode_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def set_mode(self, mode):
        self.mode = mode
        self._clear_mode()
        if mode == "Creator":
            self.setWindowTitle("HL7 Message Creator")
            self.setup_creator()
        else:
            self.setWindowTitle("HL7 Message Editor")
            self.setup_editor()

    def _current_patient(self):
        if 0 <= self.current_patient_index < len(self.patients):
            return self.patients[self.current_patient_index]
        return None

    def open_help(self):
        window = QMainWindow(self)
        window.setWindowTitle("Help - User Manual")
        window.resize(860, 700)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(help_html())
        window.setCentralWidget(browser)
        window.show()
        self._help_window = window

    def show_about(self):
        QMessageBox.information(self, "About", "HL7 Message Creator\nVersion: 1.0\nAuthor: J.M.Thomas")

    def open_files(self):
        if self.mode != "Editor":
            QMessageBox.warning(self, "Invalid Mode", "File opening is only available in Editor mode.")
            return
        files, _selected = QFileDialog.getOpenFileNames(
            self, "Select HL7 Files", DATA_DIR, "HL7 Files (*.hl7)"
        )
        if not files:
            return
        self.patient_blocks = []
        patient_groups = {}
        for file_path in files:
            patient_name = os.path.basename(file_path).split("-")[0]
            patient_groups.setdefault(patient_name, []).append(file_path)
        for patient_name, patient_files in patient_groups.items():
            patient_files.sort()
            messages = []
            for file_path in patient_files:
                with open(file_path, "r", encoding="utf-8") as handle:
                    message_text = handle.read()
                messages.append({
                    "file_path": file_path,
                    "message_text": message_text,
                    "parsed_values": self.parse_hl7_message(message_text),
                })
            self.patient_blocks.append({"patient_name": patient_name, "messages": messages})
        self.current_patient_index = 0
        self.current_message_index = 0
        self.editor_load_message()

    def save_files(self):
        if self.mode == "Creator":
            self.creator_save_files()
        elif self.mode == "Editor":
            self.editor_save_files()

    def creator_save_files(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", DATA_DIR)
        if not out_dir:
            return
        total_messages = 0
        total_patients = 0
        for patient in self.patients:
            if patient["messages"]:
                total_patients += 1
                total_messages += len(patient["messages"])
                first = patient["base_vars"]["{patientFirstName}"].get() or "First"
                last = patient["base_vars"]["{patientLastName}"].get() or "Last"
                base_name = f"{first}{last}"
                for msg, idx in patient["messages"]:
                    with open(os.path.join(out_dir, f"{base_name}-{idx}.hl7"), "w", encoding="utf-8") as handle:
                        handle.write(msg)
        QMessageBox.information(
            self, "Save Complete",
            f"Saved {total_messages} messages for {total_patients} patients to {out_dir}",
        )

    def editor_save_files(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", DATA_DIR)
        if not out_dir:
            return
        total_messages = 0
        for patient_block in self.patient_blocks:
            for message in patient_block["messages"]:
                file_path = message["file_path"]
                edited_message = self.edited_messages.get(file_path, message["message_text"])
                file_name = os.path.basename(file_path)
                with open(os.path.join(out_dir, file_name), "w", encoding="utf-8") as handle:
                    handle.write(edited_message)
                total_messages += 1
        QMessageBox.information(self, "Save Complete", f"Saved {total_messages} edited messages to {out_dir}")

    def save_and_exit(self):
        self.save_files()
        self.quit()

    def quit(self):
        answer = QMessageBox.question(
            self, "Confirm Quit", "Unsaved changes will be lost. Quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._allow_close = True
            self.close()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        answer = QMessageBox.question(
            self, "Confirm Quit", "Unsaved changes will be lost. Quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._allow_close = True
            event.accept()
        else:
            event.ignore()

    def set_today_date(self):
        patient = self._current_patient()
        if patient:
            self._set_highlight(token="{YYYYMMDD}")
            patient["base_vars"]["{YYYYMMDD}"].set(datetime.now().strftime("%Y%m%d"))

    def adjust_date(self, days):
        patient = self._current_patient()
        if not patient:
            return
        self._set_highlight(token="{YYYYMMDD}")
        date_str = patient["base_vars"]["{YYYYMMDD}"].get()
        if date_str == "{YYYYMMDD}" or not date_str:
            return
        try:
            date = datetime.strptime(date_str, "%Y%m%d")
            patient["base_vars"]["{YYYYMMDD}"].set((date + timedelta(days=days)).strftime("%Y%m%d"))
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Date must be in YYYYMMDD format.")

    def set_now_time(self):
        patient = self._current_patient()
        if patient:
            self._set_highlight(token="{scheduledTime}")
            patient["base_vars"]["{scheduledTime}"].set(datetime.now().strftime("%H%M%S"))
            self.update_time_button_states()

    def adjust_time(self, hours):
        patient = self._current_patient()
        if not patient:
            return
        self._set_highlight(token="{scheduledTime}")
        time_str = patient["base_vars"]["{scheduledTime}"].get()
        if time_str == "{scheduledTime}" or not time_str:
            return
        try:
            time = datetime.strptime(time_str, "%H%M%S")
            new_time = time + timedelta(hours=hours)
            if 0 <= new_time.hour <= 23:
                patient["base_vars"]["{scheduledTime}"].set(new_time.strftime("%H%M%S"))
                self.update_time_button_states()
            else:
                QMessageBox.warning(self, "Time Limit", "Time must be between 00:00:00 and 23:59:59.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Time must be in HHMMSS format.")

    def update_time_button_states(self):
        if not hasattr(self, "time_minus_button"):
            return
        patient = self._current_patient()
        if not patient:
            return
        time_str = patient["base_vars"]["{scheduledTime}"].get()
        minus_ok = True
        plus_ok = True
        if time_str and time_str != "{scheduledTime}":
            try:
                time = datetime.strptime(time_str, "%H%M%S")
                minus_ok = time.hour != 0
                plus_ok = time.hour != 23
            except ValueError:
                pass
        self.time_minus_button.setEnabled(minus_ok)
        self.time_plus_button.setEnabled(plus_ok)

    def random_dob(self):
        patient = self._current_patient()
        if not patient:
            return
        start_date = datetime(1940, 1, 1)
        end_date = datetime(2025, 12, 31)
        days = (end_date - start_date).days
        random_date = start_date + timedelta(days=random.randint(0, days))
        self._set_highlight(token="{patientDOB}")
        patient["base_vars"]["{patientDOB}"].set(random_date.strftime("%Y%m%d"))
        self.update_dob_age()

    def set_dob_by_age(self):
        patient = self._current_patient()
        if not patient:
            return
        try:
            age = int(self.dob_age_var.get())
            if not 0 <= age <= 85:
                raise ValueError("Age out of range")
            birth_year = datetime.now().year - age
            dob = datetime(birth_year, random.randint(1, 12), random.randint(1, 28))
            self._set_highlight(token="{patientDOB}")
            patient["base_vars"]["{patientDOB}"].set(dob.strftime("%Y%m%d"))
            self.update_dob_age()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Enter a numeric age between 0 and 85.")

    def update_dob_age(self):
        patient = self._current_patient()
        if not patient or not hasattr(self, "dob_age_var"):
            return
        dob_str = patient["base_vars"]["{patientDOB}"].get()
        if dob_str == "{patientDOB}" or not dob_str:
            self.dob_age_var.set("")
            return
        try:
            dob = datetime.strptime(dob_str, "%Y%m%d")
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            self.dob_age_var.set(str(age))
        except ValueError:
            self.dob_age_var.set("")

    def setup_creator(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        title = QHBoxLayout()
        title.addStretch(1)
        title.addWidget(self._title("HL7 Message", TITLE_HL7_MSG))
        title.addWidget(self._title(" Creator", TITLE_CREATOR))
        title.addStretch(1)
        page_layout.addLayout(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.procedure_frame = QWidget()
        self.procedure_frame.setMinimumWidth(300)
        self.procedure_layout = QVBoxLayout(self.procedure_frame)
        self.procedure_layout.setContentsMargins(0, 0, 0, 0)
        self.setup_procedure_browser()
        splitter.addWidget(self.procedure_frame)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.creator_preview_text = self._message_view()
        self.creator_preview_text.setFixedHeight(320)
        right_layout.addWidget(self.creator_preview_text)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form = QWidget()
        self.creator_form_layout = QVBoxLayout(form)
        scroll.setWidget(form)
        right_layout.addWidget(scroll, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([350, 1400])
        page_layout.addWidget(splitter, 1)
        self.mode_layout.addWidget(page)

        top = QHBoxLayout()
        self.creator_prev_button = self._button("Previous", self.creator_prev_patient)
        self.creator_next_button = self._button("Next", self.creator_next_patient)
        self.creator_new_patient_button = self._button("New Patient", self.create_new_patient)
        top.addWidget(self.creator_prev_button)
        top.addWidget(self.creator_next_button)
        top.addWidget(self.creator_new_patient_button)
        top.addStretch(1)
        self.message_type_group = QButtonGroup(page)
        self.message_type_group.setExclusive(True)
        for option in MESSAGE_TYPES:
            button = self._radio(option)
            button.setProperty("value", option)
            button.toggled.connect(lambda checked, b=button: self._on_message_type(b, checked))
            self.message_type_group.addButton(button)
            top.addWidget(button)
        self.creator_form_layout.addLayout(top)

        self.base_prompts_host = QWidget()
        self.base_prompts_layout = QVBoxLayout(self.base_prompts_host)
        self.base_prompts_layout.setContentsMargins(0, 0, 0, 0)
        self.creator_form_layout.addWidget(self.base_prompts_host)
        self.base_entries = {}
        self.staff_entries = {}
        self.additional_staff = []
        self.additional_surgeons = []
        self.setup_base_prompts()

        self.procedures_host = QWidget()
        self.procedures_layout = QVBoxLayout(self.procedures_host)
        self.procedures_layout.setContentsMargins(0, 0, 0, 0)
        self.creator_form_layout.addWidget(self.procedures_host)
        self.procedure_frames = []

        buttons = QGridLayout()
        for index, (text, slot) in enumerate((
            ("Add Surgeon", self.add_surgeon),
            ("Remove Last Surgeon", self.remove_last_surgeon),
            ("Random Surgeon", self.random_surgeon),
            ("Add Staff Member", self.add_staff_member),
            ("Remove Last Staff Member", self.remove_last_staff_member),
            ("Random Staff", self.random_staff),
            ("Browse Procedures", self.toggle_procedure_browser),
            ("Add Procedure", self.add_procedure),
            ("Remove Last Procedure", self.remove_last_procedure),
            ("Random Patient", self.random_patient_full),
            ("Clear All", self.clear_all),
        )):
            buttons.addWidget(self._button(text, slot), index // 4, index % 4)
        self.creator_form_layout.addLayout(buttons)

        self.create_button = self._button("Create", self.create_patient)
        create_font = self.create_button.font()
        create_font.setPointSize(14)
        self.create_button.setFont(create_font)
        create_row = QHBoxLayout()
        create_row.addStretch(1)
        create_row.addWidget(self.create_button)
        create_row.addStretch(1)
        self.creator_form_layout.addLayout(create_row)
        self.creator_form_layout.addStretch(1)

        self.creator_update_button_states()
        if self._current_patient():
            self.creator_load_patient()

    def _title(self, text, color):
        label = QLabel(text)
        label.setFont(QFont("Georgia", 20))
        label.setStyleSheet(f"color: {color}; background: transparent;")
        return label

    def setup_procedure_browser(self):
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_entry = UpperLineEdit()
        self.search_entry.setPlaceholderText("Name or CPT")
        self.search_entry.setClearButtonEnabled(True)
        self.search_entry.textChanged.connect(self.filter_procedures)
        self.search_entry.installEventFilter(self)
        search_row.addWidget(self.search_entry, 1)
        self.procedure_layout.addLayout(search_row)

        controls = QHBoxLayout()
        controls.addWidget(self._button("Collapse All", self.collapse_all_procedures))
        controls.addWidget(self._button("Expand All", self.expand_all_procedures))
        controls.addStretch(1)
        self.procedure_layout.addLayout(controls)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.itemDoubleClicked.connect(lambda *_args: self.select_procedure())
        self.tree.itemSelectionChanged.connect(self.update_add_button_state)
        self.tree.installEventFilter(self)
        self.procedure_layout.addWidget(self.tree, 1)

        actions = QHBoxLayout()
        self.add_procedure_button = self._button("Add Selected Procedure", self.add_selected_procedure)
        self.add_procedure_button.setEnabled(False)
        actions.addWidget(self.add_procedure_button)
        actions.addWidget(self._button("Choose Random", self.choose_random_procedure))
        actions.addWidget(self._button("Close", self.toggle_procedure_browser))
        actions.addStretch(1)
        self.procedure_layout.addLayout(actions)

        self.allergy_browser_frame = QWidget()
        allergy_layout = QVBoxLayout(self.allergy_browser_frame)
        allergy_layout.setContentsMargins(0, 0, 0, 0)
        allergy_search = QHBoxLayout()
        allergy_search.addWidget(QLabel("Search Allergies:"))
        self.allergy_search_entry = UpperLineEdit()
        self.allergy_search_entry.textEdited.connect(lambda _text: self.filter_allergies())
        allergy_search.addWidget(self.allergy_search_entry, 1)
        allergy_layout.addLayout(allergy_search)
        self.allergy_tree = QTreeWidget()
        self.allergy_tree.setHeaderHidden(True)
        self.allergy_tree.setUniformRowHeights(True)
        self.allergy_tree.setAnimated(False)
        self.allergy_tree.setMaximumHeight(220)
        self.allergy_tree.itemDoubleClicked.connect(lambda *_args: self.select_allergy())
        allergy_layout.addWidget(self.allergy_tree)
        allergy_buttons = QHBoxLayout()
        allergy_buttons.addWidget(self._button("Add Selected Allergy", self.add_selected_allergy))
        allergy_buttons.addWidget(self._button("Close", self.toggle_allergy_browser))
        allergy_buttons.addStretch(1)
        allergy_layout.addLayout(allergy_buttons)
        self.procedure_layout.addWidget(self.allergy_browser_frame)
        self.allergy_browser_frame.hide()
        self.allergy_browser_visible = False
        self.populate_procedure_tree()
        self.populate_allergy_tree()

    def collapse_all_procedures(self):
        self.tree.collapseAll()

    def expand_all_procedures(self):
        self.tree.expandAll()

    def _proc_item(self, parent, text, values=None):
        item = QTreeWidgetItem(parent, [text])
        if values is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, values)
        return item

    def populate_procedure_tree(self, filter_text=""):
        self.matched_procedures = []
        self.current_match_index = -1
        self.autocomplete_suggestion = None
        self.tree.clear()
        search_words = filter_text.lower().split() if filter_text else []
        for spec in self.procedures["specialty"].unique():
            spec_item = self._proc_item(self.tree, cell(spec))
            categories = self.procedures[self.procedures["specialty"] == spec]["category"].unique()
            for cat in categories:
                cat_item = self._proc_item(spec_item, cell(cat))
                procs = self.procedures[(self.procedures["specialty"] == spec) & (self.procedures["category"] == cat)]
                for _, proc in procs.iterrows():
                    proc_text = f"{cell(proc['name'])} (CPT: {cell(proc['cpt'])})"
                    name_lower = cell(proc["name"]).lower()
                    cpt_lower = cell(proc["cpt"]).lower()
                    if not search_words or any(word in name_lower or word in cpt_lower for word in search_words):
                        values = (
                            cell(proc["name"]), cell(proc["id"]), cell(proc["description"]),
                            cell(proc["special_needs"]), cell(proc["cpt"]), cell(spec),
                        )
                        proc_item = self._proc_item(cat_item, proc_text, values)
                        if search_words:
                            self.matched_procedures.append(proc_item)
                            spec_item.setExpanded(True)
                            cat_item.setExpanded(True)
        if self.matched_procedures:
            self.current_match_index = 0
            self.tree.setCurrentItem(self.matched_procedures[0])
            self.tree.scrollToItem(self.matched_procedures[0])
            self.highlight_matches()
            if len(self.matched_procedures) == 1:
                self.autocomplete_suggestion = self.matched_procedures[0].text(0).split(" (CPT")[0]
        self.update_add_button_state()

    def filter_procedures(self):
        self.populate_procedure_tree(self.search_entry.text())

    def highlight_matches(self):
        for item in self.matched_procedures:
            item.setBackground(0, QColor(MATCH_BG))
            item.setForeground(0, QColor(TEXT_COLOR))
        if 0 <= self.current_match_index < len(self.matched_procedures):
            current = self.matched_procedures[self.current_match_index]
            current.setBackground(0, QColor(SELECTED_MATCH_BG))
            self.tree.setCurrentItem(current)

    def navigate_matches(self, key):
        if not self.matched_procedures:
            return
        if key == Qt.Key.Key_Up and self.current_match_index > 0:
            self.current_match_index -= 1
        elif key == Qt.Key.Key_Down and self.current_match_index < len(self.matched_procedures) - 1:
            self.current_match_index += 1
        current = self.matched_procedures[self.current_match_index]
        self.tree.setCurrentItem(current)
        self.tree.scrollToItem(current)
        self.highlight_matches()

    def autocomplete_search(self):
        if not (self.autocomplete_suggestion and len(self.matched_procedures) == 1):
            return False
        current_text = self.search_entry.text()
        suggestion = self.autocomplete_suggestion.upper()
        if current_text.upper() != suggestion:
            self.search_entry.blockSignals(True)
            self.search_entry.setText(suggestion)
            self.search_entry.setSelection(len(current_text), len(suggestion))
            self.search_entry.blockSignals(False)
            self.search_entry.setStyleSheet(f"color: {DITHERED_TEXT};")
            QTimer.singleShot(100, lambda: self.search_entry.setStyleSheet(""))
            self.filter_procedures()
            self.tree.setFocus()
            self.tree.setCurrentItem(self.matched_procedures[0])
        return True

    def _selected_procedure_values(self):
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def select_procedure(self):
        values = self._selected_procedure_values()
        if values:
            self.apply_procedure_selection(*values)

    def add_selected_procedure(self):
        values = self._selected_procedure_values()
        if values:
            self.apply_procedure_selection(*values)

    def apply_procedure_selection(self, proc_name, proc_id, proc_desc, proc_needs, proc_cpt, proc_specialty):
        patient = self._current_patient()
        if not patient:
            return
        if not patient["base_vars"]["{procedure}"].get() and not patient["procedures"]:
            self._set_highlight(token="{procedure}")
            patient["base_vars"]["{procedure}"].set(proc_name)
            patient["base_vars"]["{procedureId}"].set(proc_id)
            patient["base_vars"]["{procedureDescription}"].set(proc_desc)
            patient["base_vars"]["{specialNeeds}"].set(proc_needs)
            patient["base_vars"]["{cptCode}"].set(proc_cpt)
            patient["procedure_specialty"].set(proc_specialty)
            return
        else:
            new_proc = {
                "{procedure}": self._var(proc_name),
                "{procedureId}": self._var(proc_id),
                "{procedureDescription}": self._var(proc_desc),
                "{specialNeeds}": self._var(proc_needs),
            }
            patient["procedures"].append(new_proc)
            self.add_procedure_fields(new_proc)
            self._set_highlight(token="{procedure}", proc_id=id(new_proc))
        self.creator_update_preview()

    def choose_random_procedure(self):
        patient = self._current_patient()
        if not patient:
            return
        proc = self.procedures.sample(1).iloc[0]
        if patient["procedures"]:
            last_proc = patient["procedures"][-1]
            self._set_highlight(token="{procedure}", proc_id=id(last_proc))
            for key, column in (
                ("{procedure}", "name"),
                ("{procedureId}", "id"),
                ("{procedureDescription}", "description"),
                ("{specialNeeds}", "special_needs"),
            ):
                last_proc[key].set(cell(proc[column]))
        else:
            self._set_highlight(token="{procedure}")
            for key, column in (
                ("{procedure}", "name"),
                ("{procedureId}", "id"),
                ("{procedureDescription}", "description"),
                ("{specialNeeds}", "special_needs"),
                ("{cptCode}", "cpt"),
            ):
                patient["base_vars"][key].set(cell(proc[column]))
            patient["procedure_specialty"].set(cell(proc["specialty"]))

    def toggle_procedure_browser(self):
        self.procedure_panel_visible = not self.procedure_panel_visible
        self.procedure_frame.setVisible(self.procedure_panel_visible)

    def toggle_allergy_browser(self):
        self.allergy_browser_visible = not self.allergy_browser_visible
        self.allergy_browser_frame.setVisible(self.allergy_browser_visible)

    def update_add_button_state(self):
        if not hasattr(self, "add_procedure_button"):
            return
        selected = self._selected_procedure_values()
        self.add_procedure_button.setEnabled(bool(selected) and self._current_patient() is not None)

    def _field_row(self, label_text):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setMinimumWidth(240)
        layout.addWidget(label)
        return row, layout

    def _on_encounter(self, button, checked):
        if not checked or self._loading:
            return
        self._set_highlight(token="{encounterType}")
        patient = self._current_patient()
        if patient:
            patient["base_vars"]["{encounterType}"].set(button.property("code"))

    def _on_message_type(self, button, checked):
        if not checked or self._loading:
            return
        self._set_highlight(token="{triggerEvent}")
        patient = self._current_patient()
        if patient:
            patient["message_type"].set(button.property("value"))

    def _sync_checks(self, group, prop, value):
        for button in group.buttons():
            button.blockSignals(True)
            button.setChecked(button.property(prop) == value)
            button.blockSignals(False)

    def setup_base_prompts(self):
        self.encounter_group = QButtonGroup(self.base_prompts_host)
        self.encounter_group.setExclusive(True)
        self.dob_age_var = Var("", self)
        self.age_entry = UpperLineEdit()
        self.age_entry.setMaximumWidth(70)
        self.age_entry.bind_var(self.dob_age_var)

        procedure_box = None
        procedure_layout = None
        first_procedure_keys = (
            "{procedure}", "{procedureId}", "{cptCode}", "{procedureDescription}", "{specialNeeds}",
        )
        for prompt in base_prompts:
            row, layout = self._field_row(prompt["prompt"])
            if prompt["key"] == "{encounterType}":
                for option, code in ENCOUNTER_OPTIONS.items():
                    button = self._radio(option)
                    button.setProperty("code", code)
                    button.toggled.connect(lambda checked, b=button: self._on_encounter(b, checked))
                    self.encounter_group.addButton(button)
                    layout.addWidget(button)
                layout.addStretch(1)
            else:
                entry = UpperLineEdit()
                self._track_field(entry, token=prompt["key"])
                layout.addWidget(entry, 1)
                self.base_entries[prompt["key"]] = entry
            if prompt["key"] == "{YYYYMMDD}":
                layout.addWidget(self._button("-1 Day", lambda: self.adjust_date(-1)))
                layout.addWidget(self._button("Today", self.set_today_date))
                layout.addWidget(self._button("+1 Day", lambda: self.adjust_date(1)))
            elif prompt["key"] == "{scheduledTime}":
                self.time_minus_button = self._button("-1 Hour", lambda: self.adjust_time(-1))
                self.time_plus_button = self._button("+1 Hour", lambda: self.adjust_time(1))
                layout.addWidget(self.time_minus_button)
                layout.addWidget(self._button("Now", self.set_now_time))
                layout.addWidget(self.time_plus_button)
            elif prompt["key"] == "{patientDOB}":
                layout.addWidget(self._button("Random DOB", self.random_dob))
                layout.addWidget(QLabel("Age:"))
                layout.addWidget(self.age_entry)
                layout.addWidget(self._button("Add", self.set_dob_by_age))
            elif prompt["key"] == "{patientLastName}":
                layout.addWidget(self._button("Random Name", self.random_patient))
            if prompt["key"] in first_procedure_keys:
                if procedure_box is None:
                    procedure_box = ProcedureGroup("Procedure 1")
                    procedure_layout = procedure_box.layout()
                    self.base_prompts_layout.addWidget(procedure_box)
                procedure_layout.addWidget(row)
            else:
                self.base_prompts_layout.addWidget(row)

        allergies_row, allergies_layout = self._field_row("Allergies:")
        self.allergies_display = QLabel("No Known Medical Allergies")
        self.allergies_display.setStyleSheet(f"background-color: {PREVIEW_BG}; padding: 4px;")
        self.allergies_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        allergies_layout.addWidget(self.allergies_display, 1)
        allergies_layout.addWidget(self._button("Browse Allergies", self.toggle_allergy_browser))
        self.base_prompts_layout.addWidget(allergies_row)

        self.staff_group = QWidget()
        self.staff_layout = QVBoxLayout(self.staff_group)
        self.staff_layout.setContentsMargins(0, 8, 0, 0)
        self.base_prompts_layout.addWidget(self.staff_group)
        self.fixed_roles = [
            {"role": "Primary Surgeon", "code": "1.1^Primary"},
            {"role": "Circulator", "code": "4.20^Circulator"},
            {"role": "Scrub", "code": "4.150^Scrub"},
            {"role": "CRNA", "code": "2.20^ANE CRNA"},
            {"role": "Anesthesiologist", "code": "2.139^Anesthesiologist"},
        ]
        for role_info in self.fixed_roles:
            role = role_info["role"]
            last_var = self._var("")
            first_var = self._var("")
            id_var = self._var("{surgeonID}" if role == "Primary Surgeon" else "{staffID}")
            self.staff_entries[role] = {"lastName": last_var, "firstName": first_var, "id": id_var}
            self.staff_layout.addWidget(self._name_row(f"{role}:", last_var, first_var, staff=self.staff_entries[role]))

    def _track_field(self, edit, token=None, proc=None, staff=None, part=None):
        if token:
            edit.setProperty("hl7_token", token)
        if proc is not None:
            edit.setProperty("hl7_proc", id(proc))
        if staff is not None:
            edit.setProperty("hl7_staff", id(staff))
            edit.setProperty("hl7_part", part)
        edit.installEventFilter(self)

    def _set_highlight(self, token=None, proc_id=None, staff_id=None, part=None):
        target = (token, proc_id, staff_id, part)
        current = (
            self._highlight_token, self._highlight_proc_id,
            self._highlight_staff_id, self._highlight_staff_part,
        )
        if target != current:
            self._shown_highlight_line = None
        self._highlight_token = token
        self._highlight_proc_id = proc_id
        self._highlight_staff_id = staff_id
        self._highlight_staff_part = part

    def _name_row(self, role_text, last_var, first_var, role_var=None, staff=None):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        if role_var is None:
            label = QLabel(role_text)
            label.setMinimumWidth(160)
            layout.addWidget(label)
        else:
            role_edit = UpperLineEdit()
            role_edit.setMaximumWidth(170)
            role_edit.bind_var(role_var)
            self._track_field(role_edit, staff=staff, part="role")
            layout.addWidget(role_edit)
            layout.addWidget(QLabel(":"))
        layout.addWidget(QLabel("Last:"))
        last_edit = UpperLineEdit()
        last_edit.bind_var(last_var)
        self._track_field(last_edit, staff=staff, part="lastName")
        layout.addWidget(last_edit)
        layout.addWidget(QLabel("First:"))
        first_edit = UpperLineEdit()
        first_edit.bind_var(first_var)
        self._track_field(first_edit, staff=staff, part="firstName")
        layout.addWidget(first_edit)
        return row

    def random_patient(self):
        patient = self._current_patient()
        if not patient:
            return
        name = self.patient_names.sample(1).iloc[0]
        self._set_highlight(token="{patientLastName}")
        patient["base_vars"]["{patientFirstName}"].set(cell(name["First Name"]))
        patient["base_vars"]["{patientLastName}"].set(cell(name["Last Name"]))

    def random_surgeon(self):
        patient = self._current_patient()
        if not patient:
            return
        surgeon = self.surgeon_names.sample(1).iloc[0]
        self._set_highlight(staff_id=id(self.staff_entries["Primary Surgeon"]), part="lastName")
        self.staff_entries["Primary Surgeon"]["firstName"].set(cell(surgeon["First Name"]))
        self.staff_entries["Primary Surgeon"]["lastName"].set(cell(surgeon["Last Name"]))
        self.staff_entries["Primary Surgeon"]["id"].set(cell(surgeon["ID"]))
        for additional in patient["additional_surgeons"]:
            extra = self.surgeon_names.sample(1).iloc[0]
            additional["firstName"].set(cell(extra["First Name"]))
            additional["lastName"].set(cell(extra["Last Name"]))
            additional["id"].set(cell(extra["ID"]))

    def random_staff(self):
        patient = self._current_patient()
        if not patient:
            return
        total_roles = 4 + len(patient["staff_members"])
        replace = total_roles > len(self.staff_names)
        if replace:
            QMessageBox.warning(self, "Insufficient Staff", "Not enough unique staff members for all roles. Using duplicates.")
        unique_staff = self.staff_names.sample(total_roles, replace=replace)
        self._set_highlight(staff_id=id(self.staff_entries["Circulator"]), part="lastName")
        for index, role in enumerate(["Circulator", "Scrub", "CRNA", "Anesthesiologist"]):
            staff = unique_staff.iloc[index]
            self.staff_entries[role]["firstName"].set(cell(staff["First Name"]))
            self.staff_entries[role]["lastName"].set(cell(staff["Last Name"]))
            self.staff_entries[role]["id"].set(cell(staff["ID"]))
        for index, staff_member in enumerate(patient["staff_members"]):
            staff = unique_staff.iloc[4 + index]
            staff_member["firstName"].set(cell(staff["First Name"]))
            staff_member["lastName"].set(cell(staff["Last Name"]))
            staff_member["id"].set(cell(staff["ID"]))

    def add_surgeon(self):
        patient = self._current_patient()
        if not patient:
            return
        surgeon = {
            "role": self._var("Assistant Surgeon"),
            "lastName": self._var(""),
            "firstName": self._var(""),
            "id": self._var("{staffID}"),
        }
        patient["additional_surgeons"].append(surgeon)
        self.add_surgeon_fields(surgeon)

    def remove_last_surgeon(self):
        patient = self._current_patient()
        if not patient:
            return
        if patient["additional_surgeons"]:
            patient["additional_surgeons"].pop()
            row = self.additional_surgeons.pop()
            row["frame"].setParent(None)
            row["frame"].deleteLater()
        else:
            self.staff_entries["Primary Surgeon"]["lastName"].set("")
            self.staff_entries["Primary Surgeon"]["firstName"].set("")
            self.staff_entries["Primary Surgeon"]["id"].set("{surgeonID}")
        self.creator_update_preview()

    def add_staff_member(self):
        patient = self._current_patient()
        if not patient:
            return
        staff = {
            "role": self._var("Staff"),
            "lastName": self._var(""),
            "firstName": self._var(""),
            "id": self._var("{staffID}"),
        }
        patient["staff_members"].append(staff)
        self.add_staff_fields(staff)

    def remove_last_staff_member(self):
        patient = self._current_patient()
        if not patient:
            return
        if patient["staff_members"]:
            patient["staff_members"].pop()
            row = self.additional_staff.pop()
            row["frame"].setParent(None)
            row["frame"].deleteLater()
            self.creator_update_preview()
            return
        for role in ["Circulator", "Scrub", "CRNA", "Anesthesiologist"]:
            if self.staff_entries[role]["lastName"].get() or self.staff_entries[role]["firstName"].get():
                self.staff_entries[role]["lastName"].set("")
                self.staff_entries[role]["firstName"].set("")
                self.staff_entries[role]["id"].set("{staffID}")
                return
        if self.staff_entries["Primary Surgeon"]["lastName"].get() or self.staff_entries["Primary Surgeon"]["firstName"].get():
            self.staff_entries["Primary Surgeon"]["lastName"].set("")
            self.staff_entries["Primary Surgeon"]["firstName"].set("")
            self.staff_entries["Primary Surgeon"]["id"].set("{surgeonID}")

    def random_patient_full(self):
        patient = self._current_patient()
        if not patient:
            return
        self._suspend_preview = True
        try:
            name = self.patient_names.sample(1).iloc[0]
            first_name = cell(name["First Name"])
            last_name = cell(name["Last Name"])
            patient["base_vars"]["{patientFirstName}"].set(first_name)
            patient["base_vars"]["{patientLastName}"].set(last_name)
            gender = "F" if first_name.lower()[-1:] in ["a", "e", "i"] else "M"
            patient["base_vars"]["{patientGender}"].set(gender)
            self.random_dob()
            self.last_mrn += 1
            patient["base_vars"]["{patientMRN}"].set(str(self.last_mrn))
            patient["base_vars"]["{duration}"].set(str(random.randint(60, 120)))
            proc = self.procedures.sample(1).iloc[0]
            patient["base_vars"]["{procedure}"].set(cell(proc["name"]))
            patient["base_vars"]["{procedureId}"].set(cell(proc["id"]))
            patient["base_vars"]["{procedureDescription}"].set(cell(proc["description"]))
            patient["base_vars"]["{specialNeeds}"].set(cell(proc["special_needs"]))
            patient["base_vars"]["{cptCode}"].set(cell(proc["cpt"]))
            patient["procedure_specialty"].set(cell(proc["specialty"]))
            surgeon = self.surgeon_names.sample(1).iloc[0]
            self.staff_entries["Primary Surgeon"]["firstName"].set(cell(surgeon["First Name"]))
            self.staff_entries["Primary Surgeon"]["lastName"].set(cell(surgeon["Last Name"]))
            self.staff_entries["Primary Surgeon"]["id"].set(cell(surgeon["ID"]))
            self.random_staff()
            patient["base_vars"]["{YYYYMMDD}"].set(datetime.now().strftime("%Y%m%d"))
            patient["base_vars"]["{scheduledTime}"].set(datetime.now().strftime("%H%M%S"))
            self.update_time_button_states()
        finally:
            self._suspend_preview = False
            self._set_highlight()
            self.creator_update_preview()

    def _discard_row(self, row):
        row["frame"].setParent(None)
        row["frame"].deleteLater()

    def clear_all(self):
        patient = self._current_patient()
        if not patient:
            return
        self._suspend_preview = True
        try:
            for var in patient["base_vars"].values():
                var.set("")
            patient["base_vars"]["{encounterType}"].set("IP")
            patient["message_type"].set("Scheduled & Case Events")
            for role, fields in self.staff_entries.items():
                fields["lastName"].set("")
                fields["firstName"].set("")
                fields["id"].set("{surgeonID}" if role == "Primary Surgeon" else "{staffID}")
            for item in self.additional_staff + self.additional_surgeons:
                self._discard_row(item)
            self.additional_staff = []
            self.additional_surgeons = []
            for frame in self.procedure_frames:
                frame.setParent(None)
                frame.deleteLater()
            self.procedure_frames = []
            patient["procedures"] = []
            patient["staff_members"] = []
            patient["additional_surgeons"] = []
            patient["allergies"] = []
            self._sync_checks(self.encounter_group, "code", "IP")
            self._sync_checks(self.message_type_group, "value", "Scheduled & Case Events")
            self.update_allergies_display()
        finally:
            self._suspend_preview = False
            self._set_highlight()
            self.creator_update_preview()

    def add_staff_fields(self, staff):
        row = self._name_row("", staff["lastName"], staff["firstName"], staff["role"], staff=staff)
        self.staff_layout.addWidget(row)
        self.additional_staff.append({"frame": row, "vars": staff})

    def add_surgeon_fields(self, surgeon):
        row = self._name_row("", surgeon["lastName"], surgeon["firstName"], surgeon["role"], staff=surgeon)
        insert_at = self.staff_layout.count() - len(self.additional_staff)
        self.staff_layout.insertWidget(insert_at, row)
        self.additional_surgeons.append({"frame": row, "vars": surgeon})

    def creator_update_button_states(self):
        if not hasattr(self, "creator_prev_button"):
            return
        total = len(self.patients)
        index = self.current_patient_index
        self.creator_prev_button.setEnabled(not (total <= 1 or index <= 0))
        self.creator_next_button.setEnabled(not (total <= 1 or index >= total - 1))
        self.creator_new_patient_button.setEnabled(True)

    def create_new_patient(self):
        if self.mode != "Creator":
            QMessageBox.warning(self, "Invalid Mode", "New Patient is only available in Creator mode.")
            return
        patient = {
            "base_vars": {
                prompt["key"]: self._var("IP" if prompt["key"] == "{encounterType}" else "")
                for prompt in base_prompts
            },
            "procedures": [],
            "staff_members": [],
            "additional_surgeons": [],
            "allergies": [],
            "messages": [],
            "procedure_specialty": self._var("GEN"),
            "message_type": self._var("Scheduled & Case Events"),
        }
        self.patients.append(patient)
        self.current_patient_index = len(self.patients) - 1
        self.creator_load_patient()

    def creator_load_patient(self):
        patient = self.patients[self.current_patient_index]
        self._loading = True
        try:
            for key, entry in self.base_entries.items():
                entry.bind_var(patient["base_vars"][key])
            self._sync_checks(self.encounter_group, "code", patient["base_vars"]["{encounterType}"].get())
            self._sync_checks(self.message_type_group, "value", patient["message_type"].get())
            for role, fields in self.staff_entries.items():
                fields["lastName"].set("")
                fields["firstName"].set("")
                fields["id"].set("{surgeonID}" if role == "Primary Surgeon" else "{staffID}")
            for item in self.additional_staff + self.additional_surgeons:
                self._discard_row(item)
            self.additional_staff = []
            self.additional_surgeons = []
            for staff in patient["staff_members"]:
                self.add_staff_fields(staff)
            for surgeon in patient["additional_surgeons"]:
                self.add_surgeon_fields(surgeon)
            for frame in self.procedure_frames:
                frame.setParent(None)
                frame.deleteLater()
            self.procedure_frames = []
            for proc in patient["procedures"]:
                self.add_procedure_fields(proc)
            self.update_allergies_display()
            self.update_dob_age()
            self.update_time_button_states()
        finally:
            self._loading = False
        self.creator_update_preview()
        self.creator_update_button_states()

    def add_procedure(self):
        patient = self._current_patient()
        if not patient:
            return
        proc = {field["key"]: self._var("") for field in procedure_fields}
        patient["procedures"].append(proc)
        self.add_procedure_fields(proc)
        self._set_highlight(token="{procedure}", proc_id=id(proc))
        self.creator_update_preview()

    def remove_last_procedure(self):
        patient = self._current_patient()
        if not patient:
            return
        if patient["procedures"]:
            patient["procedures"].pop()
            if self.procedure_frames:
                frame = self.procedure_frames.pop()
                frame.setParent(None)
                frame.deleteLater()
        else:
            for key in ("{procedure}", "{procedureDescription}", "{specialNeeds}", "{procedureId}", "{cptCode}"):
                patient["base_vars"][key].set("")
        self.creator_update_preview()

    def add_procedure_fields(self, proc):
        number = len(self.procedure_frames) + 2
        frame = ProcedureGroup(f"Procedure {number}")
        layout = frame.layout()
        for field in procedure_fields:
            row, row_layout = self._field_row(field["prompt"])
            entry = UpperLineEdit()
            entry.bind_var(proc[field["key"]])
            self._track_field(entry, token=field["key"], proc=proc)
            row_layout.addWidget(entry, 1)
            layout.addWidget(row)
        self.procedures_layout.addWidget(frame)
        self.procedure_frames.append(frame)

    def populate_allergy_tree(self, filter_text=""):
        if not hasattr(self, "allergy_tree"):
            return
        self.allergy_tree.clear()
        search_words = filter_text.lower().split() if filter_text else []
        for _, allergy in self.allergies.iterrows():
            text = f"{cell(allergy['allergy_name'])} (ID: {cell(allergy['allergy_id'])})"
            if not search_words or any(word in text.lower() for word in search_words):
                item = QTreeWidgetItem([text])
                item.setData(0, Qt.ItemDataRole.UserRole, (
                    cell(allergy["allergy_id"]), cell(allergy["allergy_name"]),
                    cell(allergy["reaction"]), cell(allergy["severity"]),
                ))
                self.allergy_tree.addTopLevelItem(item)

    def filter_allergies(self):
        self.populate_allergy_tree(self.allergy_search_entry.text())

    def _selected_allergy(self):
        item = self.allergy_tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def select_allergy(self):
        self._add_allergy_values(self._selected_allergy())

    def add_selected_allergy(self):
        self._add_allergy_values(self._selected_allergy())

    def _add_allergy_values(self, values):
        patient = self._current_patient()
        if not patient or not values:
            return
        patient["allergies"].append({
            "allergyID": values[0],
            "allergyName": values[1],
            "allergyReaction": values[2],
            "allergySeverity": values[3],
        })
        self.update_allergies_display()

    def update_allergies_display(self):
        patient = self._current_patient()
        if not patient or not hasattr(self, "allergies_display"):
            return
        if patient["allergies"]:
            text = ", ".join(allergy["allergyName"] for allergy in patient["allergies"])
        else:
            text = "No Known Medical Allergies"
        self.allergies_display.setText(text)

    def creator_update_preview(self):
        if self._suspend_preview or self.mode != "Creator" or self.creator_preview_text is None:
            return
        patient = self._current_patient()
        if not patient or not self.staff_entries:
            return
        template = self.add_staff_segment(self.build_template(patient))
        message_type = patient["message_type"].get()
        if message_type == "Scheduled & Case Events":
            preview_template = template
            trigger_event = "S14"
            spans = list(self._extra_spans)
            skip_lines = set(self._extra_lines)
        else:
            preview_template, spans, skip_lines = self._strip_obx(template, self._extra_spans, self._extra_lines)
            trigger_event = "S12" if message_type == "Scheduled" else "S15"
        base_values = {key: var.get() for key, var in patient["base_vars"].items()}
        base_values["{specialty}"] = patient["procedure_specialty"].get()
        replacements = {key: value for key, value in base_values.items() if value}
        replacements["{triggerEvent}"] = trigger_event
        active_token = self._highlight_token if not self._highlight_proc_id and not self._highlight_staff_id else None
        highlight = [active_token] if active_token else []
        preview_text, token_spans, edits = self._fill_text(preview_template, replacements, highlight, skip_lines)
        spans = self._retarget_spans(spans, edits)
        spans.extend(token_spans)
        al1_segments = self._al1_segments(patient)
        adt_source = adt_template.replace("{AL1_segments}", "\n".join(al1_segments))
        adt_replacements = dict(replacements)
        adt_replacements["{eventTime}"] = base_values.get("{scheduledTime}", "")
        adt_highlight = list(highlight)
        if active_token == "{scheduledTime}":
            adt_highlight.append("{eventTime}")
        adt_preview, adt_spans, _adt_edits = self._fill_text(
            adt_source, adt_replacements, adt_highlight, allow_empty=("{eventTime}",),
        )
        line_offset = len(preview_text.splitlines()) + 1
        spans.extend((line + line_offset, start, end) for line, start, end in adt_spans)
        editor = self.creator_preview_text
        v_value = editor.verticalScrollBar().value()
        h_value = editor.horizontalScrollBar().value()
        editor.setPlainText(preview_text + "\n\n" + adt_preview)
        self._apply_preview_highlight(editor, spans, v_value, h_value)

    def _fill_text(self, text, replacements, highlight_tokens, skip_lines=(), allow_empty=()):
        highlight_tokens = set(highlight_tokens or ())
        allow_empty = set(allow_empty or ())
        skip_lines = set(skip_lines or ())
        active_keys = {key for key, value in replacements.items() if value or key in allow_empty}
        tokens = sorted(active_keys | highlight_tokens, key=len, reverse=True)
        spans = []
        edits = []
        lines_out = []
        for line_index, line in enumerate(text.splitlines()):
            pieces = []
            position = 0
            index = 0
            while index < len(line):
                token = next((item for item in tokens if line.startswith(item, index)), None)
                if token is None:
                    pieces.append(line[index])
                    position += 1
                    index += 1
                    continue
                if token in active_keys:
                    value = replacements[token]
                    edits.append((line_index, index, len(token), len(value)))
                else:
                    value = token
                if token in highlight_tokens and line_index not in skip_lines and value:
                    spans.append((line_index, position, position + len(value)))
                pieces.append(value)
                position += len(value)
                index += len(token)
            lines_out.append("".join(pieces))
        if text.endswith("\n"):
            lines_out.append("")
        return "\n".join(lines_out), spans, edits

    def _retarget_spans(self, spans, edits):
        by_line = {}
        for line, start, old_len, new_len in edits:
            by_line.setdefault(line, []).append((start, old_len, new_len))
        adjusted = []
        for line, start, end in spans:
            shift = 0
            moved = (start, end)
            consumed = False
            for src_start, old_len, new_len in by_line.get(line, []):
                src_end = src_start + old_len
                if src_end <= start:
                    shift += new_len - old_len
                elif src_start >= end:
                    break
                elif start == src_start and end == src_end:
                    moved = (src_start + shift, src_start + shift + new_len)
                    consumed = True
                    break
            if not consumed:
                moved = (start + shift, end + shift)
            if moved[1] > moved[0]:
                adjusted.append((line, moved[0], moved[1]))
        return adjusted

    def _strip_obx(self, template, spans, extra_lines):
        lines = template.splitlines()
        kept = []
        remap = {}
        for old_index, line in enumerate(lines):
            if line.startswith("OBX"):
                continue
            remap[old_index] = len(kept)
            kept.append(line)
        new_spans = [(remap[line], start, end) for line, start, end in spans if line in remap]
        new_lines = {remap[line] for line in extra_lines if line in remap}
        return "\n".join(kept), new_spans, new_lines

    def _apply_preview_highlight(self, editor, spans, v_value, h_value):
        by_line = {}
        for line, start, end in spans:
            if end > start:
                by_line.setdefault(line, []).append((start, end))
        selections = []
        document = editor.document()
        for line in sorted(by_line):
            block = document.findBlockByLineNumber(line)
            if not block.isValid():
                continue
            row = QTextEdit.ExtraSelection()
            row.cursor = QTextCursor(block)
            row.format.setBackground(QColor(MATCH_BG))
            row.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selections.append(row)
            text_len = len(block.text())
            for start, end in by_line[line]:
                start = min(max(start, 0), text_len)
                end = min(max(end, start), text_len)
                if end <= start:
                    continue
                value = QTextEdit.ExtraSelection()
                cursor = QTextCursor(block)
                cursor.setPosition(block.position() + start)
                cursor.setPosition(block.position() + end, QTextCursor.MoveMode.KeepAnchor)
                value.cursor = cursor
                value.format.setBackground(QColor("#F5D76E"))
                value.format.setForeground(QColor("#1E1E1E"))
                selections.append(value)
        editor.setExtraSelections(selections)
        first_line = min(by_line) if by_line else None
        if first_line is not None and first_line != self._shown_highlight_line:
            self._shown_highlight_line = first_line
            block = document.findBlockByLineNumber(first_line)
            if block.isValid():
                editor.setTextCursor(QTextCursor(block))
                editor.ensureCursorVisible()
            return
        editor.verticalScrollBar().setValue(v_value)
        editor.horizontalScrollBar().setValue(h_value)

    def _shift_marks(self, insert_idx, count):
        if count <= 0:
            return
        self._extra_spans = [
            (line + count if line >= insert_idx else line, start, end)
            for line, start, end in self._extra_spans
        ]
        self._extra_lines = {line + count if line >= insert_idx else line for line in self._extra_lines}

    def _remap_marks(self, remap):
        self._extra_spans = [
            (remap[line], start, end) for line, start, end in self._extra_spans if line in remap
        ]
        self._extra_lines = {remap[line] for line in self._extra_lines if line in remap}

    def _marked_line(self, pieces, staff):
        chunks = []
        spans = []
        position = 0
        active = staff is not None and id(staff) == self._highlight_staff_id
        wanted = self._highlight_staff_part
        for text, part in pieces:
            if active and part == wanted and text:
                spans.append((position, position + len(text)))
            chunks.append(text)
            position += len(text)
        return "".join(chunks), spans

    def _al1_segments(self, patient):
        if not patient["allergies"]:
            return ["AL1|1||NKA^No Known Allergies||"]
        segments = []
        for index, allergy in enumerate(patient["allergies"], start=1):
            reaction = allergy["allergyReaction"] or ""
            severity = allergy["allergySeverity"] or ""
            segments.append(f"AL1|{index}||{allergy['allergyID']}^{allergy['allergyName']}|{severity}|{reaction}|")
        return segments

    def build_template(self, patient):
        self._extra_spans = []
        self._extra_lines = set()
        template = default_hl7
        for index, proc in enumerate(patient["procedures"], start=2):
            proc_values = {key: var.get() for key, var in proc.items() if var.get()}
            template = self.add_procedure_segments(template, index, proc_values, proc)
        return template

    def _substitute_proc_line(self, line, proc_values, highlight_token):
        tokens = sorted(set(proc_values) | ({highlight_token} if highlight_token else set()), key=len, reverse=True)
        pieces = []
        spans = []
        index = 0
        position = 0
        while index < len(line):
            token = next((item for item in tokens if line.startswith(item, index)), None)
            if token is None:
                pieces.append(line[index])
                index += 1
                position += 1
                continue
            value = proc_values[token] if token in proc_values and proc_values[token] else token
            if highlight_token and token == highlight_token and value:
                spans.append((position, position + len(value)))
            pieces.append(value)
            position += len(value)
            index += len(token)
        return "".join(pieces), spans

    def add_procedure_segments(self, template, proc_num, proc_values, proc=None):
        lines = template.splitlines()
        start_idx = next(i for i, line in enumerate(lines) if line.startswith("AIS|1|"))
        end_idx = next(i for i, line in enumerate(lines) if line.startswith("NTE|2|")) + 1
        proc_block = lines[start_idx:end_idx]
        new_block = []
        block_spans = []
        nte_count = 2 * (proc_num - 1)
        highlight_token = self._highlight_token if proc is not None and id(proc) == self._highlight_proc_id else None
        for line in proc_block:
            if line.startswith("AIS|1|"):
                new_line = line.replace("AIS|1|", f"AIS|{proc_num}|", 1)
            elif line.startswith("NTE|1|"):
                nte_count += 1
                new_line = line.replace("NTE|1|", f"NTE|{nte_count}|", 1)
            elif line.startswith("NTE|2|"):
                nte_count += 1
                new_line = line.replace("NTE|2|", f"NTE|{nte_count}|", 1)
            else:
                new_line = line
            new_line, spans = self._substitute_proc_line(new_line, proc_values, highlight_token)
            new_block.append(new_line)
            block_spans.append(spans)
        insert_idx = next(i for i, line in enumerate(lines) if line.startswith("NTE|2|")) + 1
        self._shift_marks(insert_idx, len(new_block))
        self._extra_lines.update(range(insert_idx, insert_idx + len(new_block)))
        for offset, spans in enumerate(block_spans):
            for start, end in spans:
                self._extra_spans.append((insert_idx + offset, start, end))
        lines[insert_idx:insert_idx] = new_block
        return "\n".join(lines)

    def add_staff_segment(self, template):
        raw_lines = template.splitlines()
        lines = []
        remap = {}
        for old_index, line in enumerate(raw_lines):
            if line.startswith("AIP|"):
                continue
            remap[old_index] = len(lines)
            lines.append(line)
        self._remap_marks(remap)
        insert_idx = next(i for i, line in enumerate(lines) if line.startswith("AIL|")) + 1
        patient = self.patients[self.current_patient_index]
        specialty = patient["procedure_specialty"].get() if patient["base_vars"]["{procedure}"].get() else "GEN"
        primary = self.staff_entries["Primary Surgeon"]
        primary_last = primary["lastName"].get() or "{primaryLastName}"
        primary_first = primary["firstName"].get() or "{primaryFirstName}"
        surgeon_id = primary["id"].get() or "{surgeonID}"
        tail = "|{YYYYMMDD}{scheduledTime}|0|S|{duration}|S"
        built = [self._marked_line([
            (f"AIP|1||{surgeon_id}^", None),
            (primary_last, "lastName"),
            ("^", None),
            (primary_first, "firstName"),
            (f"^W^^^^^EPIC^^^^PROVID|1.1^Primary Surgeon|{specialty}{tail}", None),
        ], primary)]
        for index, surgeon in enumerate(patient["additional_surgeons"], start=2):
            last_name = surgeon["lastName"].get() or "{lastName}"
            first_name = surgeon["firstName"].get() or "{firstName}"
            staff_id = surgeon["id"].get() or "{staffID}"
            built.append(self._marked_line([
                (f"AIP|{index}||{staff_id}^", None),
                (last_name, "lastName"),
                ("^", None),
                (first_name, "firstName"),
                (f"^W^^^^^EPIC^^^^PROVID|1.{index}^Assistant Surgeon|{specialty}{tail}", None),
            ], surgeon))
        aip_count = len(patient["additional_surgeons"]) + 1
        for role in ["Circulator", "Scrub", "CRNA", "Anesthesiologist"]:
            aip_count += 1
            person = self.staff_entries[role]
            last_name = person["lastName"].get() or "{lastName}"
            first_name = person["firstName"].get() or "{firstName}"
            staff_id = person["id"].get() or "{staffID}"
            role_info = next(item for item in self.fixed_roles if item["role"] == role)
            built.append(self._marked_line([
                (f"AIP|{aip_count}||{staff_id}^", None),
                (last_name, "lastName"),
                ("^", None),
                (first_name, "firstName"),
                (f"^W^^^^^EPIC^^^^PROVID|{role_info['code']}|GEN{tail}", None),
            ], person))
        for staff in patient["staff_members"]:
            aip_count += 1
            role = staff["role"].get() or "Staff"
            last_name = staff["lastName"].get() or "{lastName}"
            first_name = staff["firstName"].get() or "{firstName}"
            staff_id = staff["id"].get() or "{staffID}"
            built.append(self._marked_line([
                (f"AIP|{aip_count}||{staff_id}^", None),
                (last_name, "lastName"),
                ("^", None),
                (first_name, "firstName"),
                ("^L^^^^^^EPIC^^^^PROVID|", None),
                (role, "role"),
                (f"|{tail}", None),
            ], staff))
        self._shift_marks(insert_idx, len(built))
        for offset, (_line, spans) in enumerate(built):
            for start, end in spans:
                self._extra_spans.append((insert_idx + offset, start, end))
        lines[insert_idx:insert_idx] = [line for line, _spans in built]
        return "\n".join(lines)

    def fill_template(self, template, replacements):
        for key, val in replacements.items():
            if val and val != key:
                template = template.replace(key, val)
        return template

    def build_event_messages(self, template, base_values, duration_min):
        message_type = self.patients[self.current_patient_index]["message_type"].get()
        s12_template = "\n".join(line for line in template.splitlines() if not line.startswith("OBX"))
        event_template = template
        scheduled_time = base_values.get("{scheduledTime}", "{scheduledTime}")
        valid_time = is_valid_time(scheduled_time)
        messages = []

        if message_type == "Scheduled":
            replacements = base_values.copy()
            replacements["{triggerEvent}"] = "S12"
            replacements["{eventTime}"] = scheduled_time if valid_time else "{eventTime}"
            messages.append((self.fill_template(s12_template, replacements), "00"))
        elif message_type == "Scheduled & Case Events":
            replacements = base_values.copy()
            replacements["{triggerEvent}"] = "S12"
            replacements["{eventTime}"] = scheduled_time if valid_time else "{eventTime}"
            messages.append((self.fill_template(s12_template, replacements), "00"))
            if valid_time:
                base_dt = datetime.strptime("19700101" + scheduled_time, "%Y%m%d%H%M%S")
                event_dts = {}
                for event_name, offset in case_events:
                    if isinstance(offset, str):
                        if offset.startswith("duration"):
                            parts = offset.split("-")
                            minutes = duration_min - int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
                        else:
                            match = re.match(r"(\w+)([+-]\d+)", offset)
                            if match:
                                base_event, delta_str = match.groups()
                                delta = int(delta_str)
                                if base_event in event_dts:
                                    event_dts[event_name] = event_dts[base_event] + timedelta(minutes=delta + random.randint(-2, 2))
                                    continue
                            minutes = 0
                    else:
                        minutes = offset
                    event_dts[event_name] = base_dt + timedelta(minutes=minutes + random.randint(-2, 2))
                for index, (event_name, _) in enumerate(case_events):
                    event_replacements = base_values.copy()
                    event_replacements["{triggerEvent}"] = "S14"
                    event_replacements["{caseEvent}"] = event_name
                    event_replacements["{eventTime}"] = event_dts[event_name].strftime("%H%M%S")
                    messages.append((self.fill_template(event_template, event_replacements), f"{index + 1:02}"))
            else:
                for index, (event_name, _) in enumerate(case_events):
                    event_replacements = base_values.copy()
                    event_replacements["{triggerEvent}"] = "S14"
                    event_replacements["{caseEvent}"] = event_name
                    event_replacements["{eventTime}"] = "{eventTime}"
                    messages.append((self.fill_template(event_template, event_replacements), f"{index + 1:02}"))
        elif message_type == "Scheduled & Canceled":
            replacements = base_values.copy()
            replacements["{eventTime}"] = scheduled_time if valid_time else "{eventTime}"
            replacements["{triggerEvent}"] = "S12"
            messages.append((self.fill_template(s12_template, replacements), "00"))
            replacements["{triggerEvent}"] = "S15"
            messages.append((self.fill_template(s12_template, replacements), "15"))
        return messages

    def create_patient(self):
        patient = self._current_patient()
        if not patient:
            return
        template = self.add_staff_segment(self.build_template(patient))
        base_values = {key: var.get() for key, var in patient["base_vars"].items()}
        base_values["{specialty}"] = patient["procedure_specialty"].get()
        duration = base_values.get("{duration}", "")
        duration_min = int(duration) if duration.isdigit() else random.randint(60, 120)
        patient["messages"] = self.build_event_messages(template, base_values, duration_min)
        adt_message = adt_template.replace("{AL1_segments}", "\n".join(self._al1_segments(patient)))
        for key, val in base_values.items():
            if val:
                adt_message = adt_message.replace(key, val)
        adt_message = adt_message.replace("{eventTime}", base_values.get("{scheduledTime}", "{eventTime}"))
        patient["messages"].append((adt_message, "ADT"))
        QMessageBox.information(self, "Success", "Patient messages generated. Edit fields as needed.")

    def creator_prev_patient(self):
        if self.current_patient_index > 0:
            self.current_patient_index -= 1
            self.creator_load_patient()

    def creator_next_patient(self):
        if self.current_patient_index < len(self.patients) - 1:
            self.current_patient_index += 1
            self.creator_load_patient()

    def setup_editor(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QHBoxLayout()
        title.addStretch(1)
        title.addWidget(self._title("HL7 Message", TITLE_HL7_MSG))
        title.addWidget(self._title(" Editor", TITLE_CREATOR))
        title.addStretch(1)
        layout.addLayout(title)

        self.editor_context_label = QLabel("")
        layout.addWidget(self.editor_context_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form = QWidget()
        form_layout = QVBoxLayout(form)
        self.editor_base_entries = {}
        for prompt in base_prompts:
            row, row_layout = self._field_row(prompt["prompt"])
            entry = UpperLineEdit()
            key = prompt["key"]
            entry.textEdited.connect(lambda _text, k=key: self.editor_update_preview_from_input(k))
            entry.installEventFilter(self)
            entry.setProperty("editor_key", key)
            row_layout.addWidget(entry, 1)
            self.editor_base_entries[key] = entry
            form_layout.addWidget(row)
        scroll.setWidget(form)
        scroll.setMaximumHeight(260)
        layout.addWidget(scroll)

        apply_row = QHBoxLayout()
        self.apply_mode = QComboBox()
        self.apply_mode.addItems(["Current", "All"])
        apply_row.addWidget(self.apply_mode)
        apply_row.addWidget(self._button("Apply", self.editor_apply_changes))
        apply_row.addStretch(1)
        layout.addLayout(apply_row)

        self.editor_preview_text = self._message_view()
        layout.addWidget(self.editor_preview_text, 1)

        edit_row = QHBoxLayout()
        edit_row.addStretch(1)
        self.save_all_button = self._button("Save to All", self.save_direct_edit_all)
        self.save_current_button = self._button("Save to Current", self.save_direct_edit_current)
        self.direct_edit_button = self._button("Direct Edit", self.toggle_direct_edit)
        self.save_all_button.setEnabled(False)
        self.save_current_button.setEnabled(False)
        edit_row.addWidget(self.save_all_button)
        edit_row.addWidget(self.save_current_button)
        edit_row.addWidget(self.direct_edit_button)
        layout.addLayout(edit_row)

        nav = QHBoxLayout()
        nav.addWidget(self._button("Previous", self.editor_prev_message))
        nav.addWidget(self._button("Next", self.editor_next_message))
        nav.addWidget(self._button("Previous Patient", self.editor_prev_patient))
        nav.addWidget(self._button("Next Patient", self.editor_next_patient))
        nav.addStretch(1)
        layout.addLayout(nav)

        self.direct_edit_mode = False
        self.message_backups = {}
        self.current_patient_index = -1
        self.current_message_index = -1
        self.mode_layout.addWidget(page)
        self.editor_load_message()

    def parse_hl7_message(self, message_text):
        parsed_values = {}
        for line in message_text.splitlines():
            if line.startswith("AIL"):
                parts = line.split("|")
                if len(parts) > 3:
                    location_parts = parts[3].split("^")
                    if len(location_parts) >= 4:
                        parsed_values["{locationOR}"] = location_parts[1]
                        parsed_values["{locationDepartment}"] = location_parts[3]
            elif line.startswith("PID"):
                parts = line.split("|")
                if len(parts) > 3:
                    parsed_values["{patientMRN}"] = parts[3].split("^")[0]
        return parsed_values

    def editor_load_message(self):
        if self.editor_preview_text is None:
            return
        block_ok = 0 <= self.current_patient_index < len(self.patient_blocks)
        message_ok = block_ok and 0 <= self.current_message_index < len(self.patient_blocks[self.current_patient_index]["messages"])
        self.editor_preview_text.setReadOnly(False)
        if message_ok:
            block = self.patient_blocks[self.current_patient_index]
            message = block["messages"][self.current_message_index]
            self.editor_context_label.setText(
                f"Patient: {block['patient_name']}, Message {self.current_message_index + 1} of {len(block['messages'])}"
            )
            self.editor_preview_text.setPlainText(message["message_text"])
            parsed_values = message["parsed_values"]
            for key, entry in self.editor_base_entries.items():
                value = parsed_values.get(key, "")
                entry.blockSignals(True)
                entry.setText("" if value == key else value)
                entry.blockSignals(False)
        else:
            self.editor_context_label.setText("No messages loaded")
            self.editor_preview_text.setPlainText("No patient blocks found.\n")
        self.editor_preview_text.setReadOnly(not self.direct_edit_mode)

    def editor_update_preview_from_input(self, key):
        if self.editor_preview_text is None:
            return
        value = self.editor_base_entries[key].text()
        message_text = self.editor_preview_text.toPlainText().strip().replace(key, value)
        self.editor_preview_text.setReadOnly(False)
        self.editor_preview_text.setPlainText(message_text)
        self.editor_preview_text.setReadOnly(not self.direct_edit_mode)
        self.editor_highlight_field(key)

    def editor_highlight_field(self, key):
        if self.editor_preview_text is None:
            return
        self.editor_preview_text.setExtraSelections([])
        message = self.editor_preview_text.toPlainText().strip()
        field_map = {
            "{locationDepartment}": ("AIL", 3, 2),
            "{locationOR}": ("AIL", 3, 1),
            "{patientMRN}": ("PID", 3, 1),
        }
        if key not in field_map:
            return
        segment, field_idx, component_idx = field_map[key]
        for line_index, line in enumerate(message.splitlines()):
            if not line.startswith(segment):
                continue
            parts = line.split("|")
            if len(parts) <= field_idx:
                continue
            components = parts[field_idx].split("^")
            if len(components) < component_idx:
                continue
            value = components[component_idx - 1]
            start_idx = line.find(value)
            if start_idx < 0 or not value:
                break
            block = self.editor_preview_text.document().findBlockByLineNumber(line_index)
            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start_idx)
            cursor.setPosition(block.position() + start_idx + len(value), QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(QColor("yellow"))
            selection.format.setForeground(QColor("black"))
            self.editor_preview_text.setExtraSelections([selection])
            break

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusIn and isinstance(obj, QLineEdit):
            if obj.property("editor_key"):
                self.editor_highlight_field(obj.property("editor_key"))
            else:
                token = obj.property("hl7_token")
                proc_id = obj.property("hl7_proc")
                staff_id = obj.property("hl7_staff")
                if token or proc_id or staff_id:
                    self._set_highlight(
                        token=token or None,
                        proc_id=proc_id or None,
                        staff_id=staff_id or None,
                        part=obj.property("hl7_part") or None,
                    )
                    self.creator_update_preview()
        if event.type() == QEvent.Type.KeyPress and obj is getattr(self, "search_entry", None) and event.key() == Qt.Key.Key_Tab:
            if self.autocomplete_search():
                return True
        if event.type() == QEvent.Type.KeyPress and obj is getattr(self, "tree", None):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self.navigate_matches(event.key())
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.add_selected_procedure()
                return True
        return super().eventFilter(obj, event)

    def editor_apply_changes(self):
        if self.apply_mode.currentText() == "Current":
            self.apply_to_current_message()
        else:
            self.apply_to_all_messages()

    def _current_editor_message(self):
        if 0 <= self.current_patient_index < len(self.patient_blocks):
            messages = self.patient_blocks[self.current_patient_index]["messages"]
            if 0 <= self.current_message_index < len(messages):
                return messages[self.current_message_index]
        return None

    def apply_to_current_message(self):
        message = self._current_editor_message()
        if message is None:
            QMessageBox.warning(self, "No Message", "No message selected")
            return
        self.message_backups[message["file_path"]] = message["message_text"]
        updated_text = self.editor_preview_text.toPlainText().strip()
        self.edited_messages[message["file_path"]] = updated_text
        message["message_text"] = updated_text
        QMessageBox.information(self, "Applied", "Changes applied to current message")

    def apply_to_all_messages(self):
        if not (0 <= self.current_patient_index < len(self.patient_blocks)):
            QMessageBox.warning(self, "No Patient Block", "No patient block selected")
            return
        patient_block = self.patient_blocks[self.current_patient_index]
        updated_text = self.editor_preview_text.toPlainText().strip()
        for message in patient_block["messages"]:
            self.message_backups[message["file_path"]] = message["message_text"]
            self.edited_messages[message["file_path"]] = updated_text
            message["message_text"] = updated_text
        QMessageBox.information(
            self, "Applied",
            f"Changes applied to all {len(patient_block['messages'])} messages in this patient block",
        )

    def toggle_direct_edit(self):
        self.direct_edit_mode = not self.direct_edit_mode
        self.editor_preview_text.setReadOnly(not self.direct_edit_mode)
        self.save_current_button.setEnabled(self.direct_edit_mode)
        self.save_all_button.setEnabled(self.direct_edit_mode)
        self.direct_edit_button.setText("Exit Direct Edit" if self.direct_edit_mode else "Direct Edit")

    def save_direct_edit_current(self):
        message = self._current_editor_message()
        if message is None:
            return
        updated_text = self.editor_preview_text.toPlainText().strip()
        try:
            self.message_backups[message["file_path"]] = message["message_text"]
            self.edited_messages[message["file_path"]] = updated_text
            message["message_text"] = updated_text
            QMessageBox.information(self, "Saved", "Direct edits saved to current message")
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", f"Invalid HL7 message: {exc}")

    def save_direct_edit_all(self):
        if not (0 <= self.current_patient_index < len(self.patient_blocks)):
            QMessageBox.warning(self, "No Patient Block", "No patient block selected")
            return
        patient_block = self.patient_blocks[self.current_patient_index]
        updated_text = self.editor_preview_text.toPlainText().strip()
        try:
            for message in patient_block["messages"]:
                self.message_backups[message["file_path"]] = message["message_text"]
                self.edited_messages[message["file_path"]] = updated_text
                message["message_text"] = updated_text
            QMessageBox.information(
                self, "Saved",
                f"Direct edits saved to all {len(patient_block['messages'])} messages in this patient block",
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", f"Invalid HL7 message: {exc}")

    def editor_prev_message(self):
        if self.current_patient_index >= 0 and self.current_message_index > 0:
            self.current_message_index -= 1
            self.editor_load_message()

    def editor_next_message(self):
        if self.current_patient_index >= 0 and self.current_message_index < len(self.patient_blocks[self.current_patient_index]["messages"]) - 1:
            self.current_message_index += 1
            self.editor_load_message()

    def editor_prev_patient(self):
        if self.current_patient_index > 0:
            self.current_patient_index -= 1
            self.current_message_index = 0
            self.editor_load_message()

    def editor_next_patient(self):
        if self.current_patient_index < len(self.patient_blocks) - 1:
            self.current_patient_index += 1
            self.current_message_index = 0
            self.editor_load_message()


def main():
    if sys.platform == "win32":
        # WSL draws this app at 100% scale. Windows display scaling otherwise
        # enlarges the whole window, which is why the fonts look bigger there.
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_FONT_DPI"] = "96"
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Arial", 12))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_COLOR))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.Base, QColor(PREVIEW_BG))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#B0B0B8"))
    palette.setColor(QPalette.ColorRole.Button, QColor(BUTTON_BG))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_COLOR))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(SELECTED_MATCH_BG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT_COLOR))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(DITHERED_TEXT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(DITHERED_TEXT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(DITHERED_TEXT))
    app.setPalette(palette)
    window = HL7MessageApp()
    if window.failed:
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
