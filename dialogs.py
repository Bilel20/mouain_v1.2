# -*- coding: utf-8 -*-
"""Extracted module dialogs."""
import re
from datetime import datetime, time

import pandas as pd

from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QAbstractItemView,
    QComboBox, QFormLayout, QGridLayout, QGroupBox,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QListWidget,
    QListWidgetItem,
)

from app_config import ACTIVITIES_BY_MAJAL, DETAIL_KEYS_BY_NAMAT
from widgets import CustomCalendarWidget

from app_config import DB_PATH, set_dialog_button_action_types
from completion import AutoCompletionTextEdit
from database import Database
class YearImportDialog(QDialog):
    def __init__(self, db, default_year_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("تحديد السنة الدراسية للاستيراد")
        self.setMinimumWidth(380)
        self.db = db
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_years = QComboBox()
        self.combo_years.setEditable(True)
        self.load_existing_years()
        if default_year_name:
            self.combo_years.setCurrentText(default_year_name)
            
        form.addRow("السنة الدراسية المستهدفة:", self.combo_years)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("متابعة الاستيراد", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_existing_years(self):
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("SELECT id, nom_annee FROM ann_scolaire")
                rows = cursor.fetchall()
                for row in rows:
                    self.combo_years.addItem(row[1], row[0])
        except Exception as e:
            print(f"Error loading years: {e}")

    def get_selected_year_name(self):
        return self.combo_years.currentText().strip()


class SchoolYearSelectionDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setObjectName("schoolYearExportDialog")
        self.setWindowTitle("اختيار السنة الدراسية للتصدير")
        self.setMinimumWidth(350)
        self.db = db
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_years = QComboBox()
        self.load_years()
        
        form.addRow("السنة الدراسية:", self.combo_years)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        export_button = buttons.addButton("تصدير", QDialogButtonBox.AcceptRole)
        export_button.setProperty("actionType", "export")
        cancel_button = buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        cancel_button.setProperty("actionType", "cancel")
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_years(self):
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("SELECT id, nom_annee FROM ann_scolaire")
                rows = cursor.fetchall()
                for row in rows:
                    self.combo_years.addItem(row[1], row[0])
        except Exception as e:
            print(f"Error loading years: {e}")

    def get_selected_year_info(self):
        year_id = self.combo_years.currentData()
        year_name = self.combo_years.currentText()
        return year_id, year_name


class LessonEntryDialog(QDialog):
    def __init__(self, title, df_history, weekday_num=None, default_values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.df_history = df_history
        self.weekday_num = weekday_num
        self.is_updating = False
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.combo_classe = QComboBox()
        self.combo_classe.setEditable(True)
        classes = sorted(df_history['classe'].dropna().unique().tolist()) if df_history is not None and not df_history.empty else []
        self.combo_classe.addItems(classes)
        
        self.combo_majal = QComboBox()
        self.combo_majal.setEditable(True)
        
        self.combo_heure = QComboBox()
        self.combo_heure.setEditable(True)
        self.load_day_specific_heures()

        self.combo_time = QComboBox()
        self.combo_time.setEditable(True)
        self.combo_time.addItems(["30 دقيقة", "45 دقيقة", "60 دقيقة", "90 دقيقة", "120 دقيقة"])
        
        self.spin_wehda = QSpinBox()
        self.spin_wehda.setRange(1, 999)
        self.spin_wehda.setValue(1)
        
        self.spin_hessa = QSpinBox()
        self.spin_hessa.setRange(1, 999)
        self.spin_hessa.setValue(1)
        
        self.combo_namat = QComboBox()
        self.combo_namat.addItems(["منهجي", "إدماج", "تقييم", "دعم وعلاج"])
        self.combo_namat.setCurrentText("منهجي")
        
        form.addRow("القسم", self.combo_classe)
        form.addRow("المجال", self.combo_majal)
        form.addRow("التوقيت (مثال: 08:00-09:00)", self.combo_heure)
        form.addRow("مدة الحصة", self.combo_time)
        form.addRow("الوحدة", self.spin_wehda)
        form.addRow("الحصة", self.spin_hessa)
        form.addRow("نمط التعلم", self.combo_namat)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.combo_classe.currentTextChanged.connect(self.on_classe_changed)
        self.combo_majal.currentTextChanged.connect(self.on_majal_changed)
        self.combo_heure.currentTextChanged.connect(self.on_heure_changed)
        
        if default_values:
            if default_values[0]:
                self.combo_classe.setCurrentText(str(default_values[0]))
            if default_values[1]:
                self.combo_majal.setCurrentText(str(default_values[1]))
            if default_values[2]:
                self.combo_heure.setCurrentText(str(default_values[2]))
            if default_values[3]:
                self.combo_time.setCurrentText(str(default_values[3]))
            if default_values[4]:
                self.spin_wehda.setValue(int(default_values[4] or 1))
            if default_values[5]:
                self.spin_hessa.setValue(int(default_values[5] or 1))
            if default_values[6]:
                self.combo_namat.setCurrentText(str(default_values[6]))
        elif classes:
            self.on_classe_changed(self.combo_classe.currentText())

    def load_day_specific_heures(self):
        if self.df_history is None or self.df_history.empty or self.weekday_num is None:
            return
        try:
            df = self.df_history.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['wd'] = df['date'].dt.dayofweek
            df_day = df[df['wd'] == self.weekday_num]
            if not df_day.empty and 'heure' in df_day.columns:
                heures = sorted(df_day['heure'].dropna().unique().tolist())
                self.combo_heure.clear()
                self.combo_heure.addItems(heures)
        except Exception as e:
            print(f"Error loading day specific heures: {e}")

    def on_classe_changed(self, classe_text):
        if self.is_updating or self.df_history is None or self.df_history.empty:
            return
        self.is_updating = True
        try:
            df = self.df_history.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['wd'] = df['date'].dt.dayofweek
            df_sub = df[(df['classe'] == classe_text) & (df['wd'] == self.weekday_num)]
            if df_sub.empty:
                df_sub = df[df['classe'] == classe_text]

            if not df_sub.empty:
                majals = sorted(df_sub['majal'].dropna().unique().tolist())
                self.combo_majal.clear()
                self.combo_majal.addItems(majals)

                heures = sorted(df_sub['heure'].dropna().unique().tolist())
                if heures:
                    self.combo_heure.clear()
                    self.combo_heure.addItems(heures)

                times = sorted(df_sub['time'].dropna().unique().tolist())
                if times:
                    self.combo_time.clear()
                    self.combo_time.addItems(times)
        except Exception as e:
            print(f"Error in on_classe_changed: {e}")
        finally:
            self.is_updating = False

    def on_majal_changed(self, majal_text):
        if self.is_updating or not majal_text.strip() or self.df_history is None or self.df_history.empty:
            return
        self.is_updating = True
        try:
            df = self.df_history.copy()
            classe_text = self.combo_classe.currentText().strip()
            df_sub = df[(df['majal'] == majal_text) & (df['classe'] == classe_text)]
            if df_sub.empty:
                df_sub = df[df['majal'] == majal_text]

            if not df_sub.empty:
                heures = sorted(df_sub['heure'].dropna().unique().tolist())
                if heures:
                    self.combo_heure.clear()
                    self.combo_heure.addItems(heures)
                    mode_heure = df_sub['heure'].mode()
                    if not mode_heure.empty:
                        self.combo_heure.setCurrentText(str(mode_heure.iloc[0]))
        except Exception as e:
            print(f"Error in on_majal_changed: {e}")
        finally:
            self.is_updating = False

    def on_heure_changed(self, heure_text):
        if self.is_updating or not heure_text.strip():
            return
        cleaned_text = heure_text.replace(" ", "").replace("ـ", "-")
        if "-" in cleaned_text:
            parts = cleaned_text.split("-")
            if len(parts) == 2:
                try:
                    t1 = datetime.strptime(parts[0].strip(), "%H:%M")
                    t2 = datetime.strptime(parts[1].strip(), "%H:%M")
                    if t2 >= t1:
                        diff_minutes = int((t2 - t1).total_seconds() / 60)
                        self.combo_time.setCurrentText(f"{diff_minutes} دقيقة")
                except ValueError:
                    pass

        if self.df_history is None or self.df_history.empty:
            return
        self.is_updating = True
        try:
            df = self.df_history.copy()
            classe_text = self.combo_classe.currentText().strip()
            df_sub = df[(df['heure'] == heure_text) & (df['classe'] == classe_text)]
            if df_sub.empty:
                df_sub = df[df['heure'] == heure_text]

            if not df_sub.empty:
                mode_majal = df_sub['majal'].mode()
                if not mode_majal.empty:
                    suggested_majal = str(mode_majal.iloc[0])
                    if self.combo_majal.findText(suggested_majal) >= 0:
                        self.combo_majal.setCurrentText(suggested_majal)
        except Exception as e:
            print(f"Error in on_heure_changed: {e}")
        finally:
            self.is_updating = False

    def validate_and_accept(self):
        heure_text = self.combo_heure.currentText().strip().replace(" ", "").replace("ـ", "-")
        if "-" in heure_text:
            parts = heure_text.split("-")
            if len(parts) == 2:
                try:
                    t1 = datetime.strptime(parts[0].strip(), "%H:%M").time()
                    t2 = datetime.strptime(parts[1].strip(), "%H:%M").time()
                    work_start = time(7, 0)
                    work_end = time(17, 0)
                    if not (work_start <= t1 <= work_end and work_start <= t2 <= work_end):
                        QMessageBox.warning(self, "توقيت غير مقبول", "أوقات العمل الرسمية بين 07:00 و 17:00.")
                        return
                    if t2 <= t1:
                        QMessageBox.warning(self, "خطأ في التوقيت", "وقت النهاية يجب أن يكون بعد وقت البداية.")
                        return
                except ValueError:
                    QMessageBox.warning(self, "توقيت غير صالح", "صيغة التوقيت غير مقبولة (مثال: 08:00-09:30).")
                    return
        self.accept()

    def values(self):
        return [
            self.combo_classe.currentText().strip(),
            self.combo_majal.currentText().strip(),
            self.combo_heure.currentText().strip(),
            self.combo_time.currentText().strip(),
            self.spin_wehda.value(),
            self.spin_hessa.value(),
            self.combo_namat.currentText().strip()
        ]


class BulkLessonEntryDialog(QDialog):
    def __init__(self, lessons, number_defaults, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة كل الحصص")
        self.setObjectName("bulkLessonEntryDialog")
        self.setMinimumSize(1280, 520)
        self.setLayoutDirection(Qt.RightToLeft)

        def lesson_sort_key(lesson):
            hour_text = str(lesson[2] or "").strip().replace("ـ", "-").replace(" ", "")
            start_text = hour_text.split("-", 1)[0]
            try:
                return 0, datetime.strptime(start_text, "%H:%M").time(), hour_text
            except ValueError:
                return 1, time.max, hour_text

        self.lessons = sorted(lessons, key=lesson_sort_key)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)
        info_label = QLabel("أدخل رقم الوحدة والحصة واختر نمط التعلم لكل حصة:")
        info_label.setObjectName("bulkLessonInfo")
        layout.addWidget(info_label)

        self.table = QTableWidget(len(self.lessons), 7)
        self.table.setHorizontalHeaderLabels([
            "القسم", "المجال", "ساعة التدريس", "التوقيت",
            "عدد الوحدة", "عدد الحصة", "نمط التعلم"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setMinimumWidth(1230)
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.SelectedClicked
        )

        self.row_inputs = []
        learning_modes = ["منهجي", "إدماج", "تقييم", "دعم وعلاج"]
        next_numbers = dict(number_defaults)
        for row, lesson in enumerate(self.lessons):
            for column, value in enumerate(lesson):
                item = QTableWidgetItem(str(value or ""))
                item.setTextAlignment(Qt.AlignCenter)
                if column >= 4:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)

            default_unit, default_lesson = number_defaults.get(
                (str(lesson[0] or "").strip(), str(lesson[1] or "").strip()),
                (1, row + 1)
            )
            key = (str(lesson[0] or "").strip(), str(lesson[1] or "").strip())
            default_unit, default_lesson = next_numbers.get(key, (default_unit, default_lesson))
            self.table.setItem(
                row, 4, QTableWidgetItem(str(default_unit))
            )
            self.table.setItem(
                row, 5, QTableWidgetItem(str(default_lesson))
            )
            mode_combo = QComboBox()
            mode_combo.addItems(learning_modes)
            mode_combo.setMinimumWidth(160)
            self.table.setCellWidget(row, 6, mode_combo)
            self.row_inputs.append(mode_combo)
            increment = 2 if (
                "اللغة العربية" in key[1]
                and re.search(r"\b120\b", str(lesson[3] or ""))
            ) else 1
            next_numbers[key] = (default_unit, default_lesson + increment)

        layout.addWidget(self.table)
        buttons = QDialogButtonBox()
        save_button = buttons.addButton("إضافة الحصص", QDialogButtonBox.AcceptRole)
        save_button.setObjectName("bulkSaveButton")
        cancel_button = buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        cancel_button.setObjectName("bulkCancelButton")
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        for row in range(self.table.rowCount()):
            for column in (4, 5):
                item = self.table.item(row, column)
                try:
                    value = int(item.text().strip()) if item else 0
                except ValueError:
                    value = 0
                if not 1 <= value <= 999:
                    QMessageBox.warning(
                        self, "قيمة غير صالحة",
                        "يجب أن يكون عدد الوحدة وعدد الحصة رقماً بين 1 و999."
                    )
                    self.table.setCurrentCell(row, column)
                    return
        self.accept()

    def values(self):
        return [
            (
                str(lesson[0] or "").strip(),
                str(lesson[1] or "").strip(),
                str(lesson[2] or "").strip(),
                str(lesson[3] or "").strip(),
                int(self.table.item(row, 4).text().strip()),
                int(self.table.item(row, 5).text().strip()),
                mode_combo.currentText()
            )
            for row, (lesson, mode_combo)
            in enumerate(zip(self.lessons, self.row_inputs))
        ]


class EntryDialog(QDialog):
    def __init__(self, title, fields, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        if len(fields) > 10:
            self.setMinimumSize(1100, 650)
            self.resize(1250, 850)
        else:
            self.setMinimumWidth(480)
        self.widgets = []
        layout = QVBoxLayout(self)
        use_three_columns = len(fields) > 10
        form = QGridLayout() if use_three_columns else QFormLayout()
        if use_three_columns:
            for grid_column in range(3):
                form.setColumnStretch(grid_column, 1)
        row = 0
        column = 0
        
        for label, kind, default in fields:
            if kind in ("int", "nonnegative_int"):
                w = QSpinBox()
                w.setRange(0 if kind == "nonnegative_int" else 1, 999)
                initial_value = default if default is not None else (
                    0 if kind == "nonnegative_int" else 1
                )
                w.setValue(int(initial_value))
            elif kind in ["multiline", "plaintext"]:
                w = QTextEdit()
                w.setAcceptRichText(False)
                w.setPlainText(str(default or ""))
                w.setMinimumHeight(100)
                w.setAlignment(Qt.AlignCenter)
            elif kind == "date":
                w = QLineEdit(str(default or ""))
                w.setPlaceholderText("YYYY-MM-DD")
            else:
                w = QLineEdit(str(default or ""))

            if isinstance(w, QLineEdit):
                w.setAlignment(Qt.AlignCenter)
            elif isinstance(w, QSpinBox):
                w.lineEdit().setAlignment(Qt.AlignCenter)

            self.widgets.append(w)
            if use_three_columns:
                if kind == "plaintext" and column:
                    row += 1
                    column = 0

                label_widget = QLabel(label)
                label_widget.setAlignment(Qt.AlignCenter)
                cell = QWidget()
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.addWidget(label_widget)
                cell_layout.addWidget(w)
                if kind == "plaintext":
                    form.addWidget(cell, row, 0, 1, 3)
                    row += 1
                    column = 0
                else:
                    form.addWidget(cell, row, column)
                    column += 1
                    if column == 3:
                        row += 1
                        column = 0
            else:
                form.addRow(label, w)
            
        if values:
            for w, value in zip(self.widgets, values):
                if isinstance(w, QSpinBox):
                    w.setValue(int(
                        value if value is not None else
                        (0 if w.minimum() == 0 else 1)
                    ))
                elif isinstance(w, QTextEdit):
                    w.setPlainText(str(value or ""))
                else:
                    w.setText(str(value or ""))
                    
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        result = []
        for w in self.widgets:
            if isinstance(w, QSpinBox):
                result.append(w.value())
            elif isinstance(w, QTextEdit):
                result.append(w.toPlainText().strip())
            else:
                result.append(w.text().strip())
        return result


class DaySelectionDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اختيار يوم للتصدير")
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.db = db
        
        layout = QVBoxLayout(self)
        info_label = QLabel("اختر اليوم المطلوب تصديره من التقويم أدناه:")
        info_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 11px;")
        layout.addWidget(info_label)
        
        self.calendar = CustomCalendarWidget(self.db, self)
        layout.addWidget(self.calendar)
        self.calendar.setLocale(QLocale(QLocale.Arabic, QLocale.Tunisia))
        
        buttons = QDialogButtonBox()
        self.export_btn = buttons.addButton("تصدير الملف", QDialogButtonBox.AcceptRole)
        self.export_btn.setProperty("actionType", "export")
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_date_str(self):
        return self.calendar.selectedDate().toString("yyyy-MM-dd")


class ActivityEntryDialog(QDialog):
    def __init__(self, title, majal, db, weekday, values=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.majal = majal or ""
        self.weekday = weekday
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        form = QFormLayout()
        layout = QVBoxLayout(self)

        self.title_combo = QComboBox()
        self.title_combo.setEditable(True)
        self.title_combo.addItems(ACTIVITIES_BY_MAJAL.get(self.majal, []))
        self.title_combo.setCurrentText(values[0] if values else "")
        
        self.time_combo = QComboBox()
        self.time_combo.setEditable(True)
        self.time_combo.addItems(["5 دقائق", "10 دقائق", "15 دقيقة", "20 دقيقة",
                                  "30 دقيقة", "45 دقيقة", "60 دقيقة"])
        form.addRow("عنوان النشاط", self.title_combo)
        form.addRow("المدة", self.time_combo)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.title_combo.currentTextChanged.connect(self.update_duration_suggestion)
        if values:
            self.time_combo.setCurrentText(str(values[1] or ""))

    def update_duration_suggestion(self, activity_title):
        if not activity_title.strip():
            return
        try:
            with self.db.connect() as con:
                df = pd.read_sql_query("""
                    SELECT n.time, d.date
                    FROM nachat n
                    JOIN hessa h ON h.id = n.hessa_id
                    JOIN day_data d ON d.id = h.day_data_id
                    WHERE n.title = ? AND h.majal = ?
                      AND COALESCE(n.time, '') <> ''
                """, con, params=(activity_title.strip(), self.majal))
            if df.empty:
                return
            dates = pd.to_datetime(df["date"], errors="coerce")
            df = df.loc[dates.dt.dayofweek == self.weekday].copy()
            if df.empty:
                return
            modes = df["time"].astype(str).mode()
            if not modes.empty:
                suggestion = modes.iloc[0]
                old = self.time_combo.currentText()
                if not old or old not in df["time"].astype(str).unique():
                    self.time_combo.setCurrentText(suggestion)
        except Exception as exc:
            print(f"Activity duration prediction error: {exc}")

    def values(self):
        return [self.title_combo.currentText().strip(), self.time_combo.currentText().strip()]


class DetailEntryDialog(QDialog):
    def __init__(self, title, namat, activity_title, db, current_count=0, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(540)
        self.db = db
        self.namat = namat or ""
        self.activity_title = activity_title or ""
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_combo = QComboBox()
        self.key_combo.addItems(DETAIL_KEYS_BY_NAMAT.get(self.namat, []))
        
        if not values and self.activity_title:
            predicted_key = self.db.predict_next_detail_key(self.activity_title, self.namat, current_count)
            if predicted_key:
                idx = self.key_combo.findText(predicted_key)
                if idx >= 0:
                    self.key_combo.setCurrentIndex(idx)

        self.value_edit = AutoCompletionTextEdit(self.db, self.key_combo, self.activity_title)
        self.value_edit.setPlaceholderText("اكتب قيمة الخاصية؛ ستظهر اقتراحات مشابهة من السجل السابق…")
        font_metrics = self.value_edit.fontMetrics()
        self.value_edit.setFixedHeight(font_metrics.lineSpacing() * 5 + 12)

        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(130)
        self.suggestions_list.setToolTip("اختر اقتراحاً لإدراجه في خانة القيمة")
        self.suggestions_list.hide()
        self.value_edit.textChanged.connect(self.refresh_smart_suggestions)
        self.value_edit.suggestions_ready.connect(self.show_smart_suggestions)
        self.suggestions_list.itemClicked.connect(self.apply_smart_suggestion)
        self.key_combo.currentTextChanged.connect(self.refresh_smart_suggestions)
        self.key_combo.currentTextChanged.connect(self.value_edit.refresh_for_key_change)

        form.addRow("اسم الخاصية", self.key_combo)
        form.addRow("القيمة", self.value_edit)
        form.addRow("اقتراحات ذكية", self.suggestions_list)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        buttons.addButton("حفظ", QDialogButtonBox.AcceptRole)
        buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if values:
            old_key, old_value = values
            index = self.key_combo.findText(str(old_key or ""))
            if index >= 0:
                self.key_combo.setCurrentIndex(index)
            self.value_edit.setPlainText(str(old_value or ""))

    def refresh_smart_suggestions(self, *_args):
        query = self.value_edit.toPlainText().strip()
        self.suggestions_list.clear()
        if len(query) < 2:
            self.suggestions_list.hide()
        else:
            self.suggestions_list.hide()

    def show_smart_suggestions(self, suggestions):
        self.suggestions_list.clear()
        for value, score in suggestions:
            item = QListWidgetItem(value)
            item.setToolTip(f"درجة التشابه النصي: {score:.0%}")
            self.suggestions_list.addItem(item)
        self.suggestions_list.setVisible(self.suggestions_list.count() > 0)

    def apply_smart_suggestion(self, item):
        if item is None:
            return
        self.value_edit.setPlainText(item.text())
        self.value_edit.moveCursor(QTextCursor.End)
        self.value_edit.setFocus()
        self.suggestions_list.hide()

    def values(self):
        return [self.key_combo.currentText().strip(), self.value_edit.toPlainText().strip()]


class CompetenceManagerDialog(QDialog):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إدارة كفايات المجالات والمواد الدراسية")
        # ⬅️ زيادة عرض وارتفاع النافذة لتكون أوسع وأكثر راحة
        self.resize(1200, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        
        self.db = db if db else Database(DB_PATH)
        
        self.selected_level_id = None
        self.selected_majal_id = None
        self.selected_competence_majal_id = None
        self.copied_majal_data = None

        self.init_ui()
        self.load_levels_and_majals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title_label = QLabel("🎯 لوحة إدارة كفايات المجالات والمواد الدراسية")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E40AF; padding: 5px;")
        main_layout.addWidget(title_label)

        filters_box = QGroupBox("فلترة واختيار المستوى والمجال")
        filters_layout = QHBoxLayout(filters_box)

        self.combo_level = QComboBox()
        self.combo_level.currentIndexChanged.connect(self.on_filter_changed)

        self.combo_majal = QComboBox()
        self.combo_majal.currentIndexChanged.connect(self.on_filter_changed)

        filters_layout.addWidget(QLabel("المستوى الدراسي:"))
        filters_layout.addWidget(self.combo_level, 1)
        filters_layout.addWidget(QLabel("المجال:"))
        filters_layout.addWidget(self.combo_majal, 1)

        main_layout.addWidget(filters_box)

        splitter = QSplitter(Qt.Horizontal)

        # جدول كفاية المجال
        majal_widget = QWidget()
        majal_layout = QVBoxLayout(majal_widget)
        majal_layout.addWidget(QLabel("<b>1. كفاية المجال </b>"))
        
        majal_btns_layout = QHBoxLayout()
        for text, slot, act_type in [
            ("＋ إضافة", self.add_competence_majal, "add"), 
            ("✎ تعديل", self.edit_competence_majal, "edit"), 
            ("－ حذف", self.delete_competence_majal, "delete"),
            ("📋 نسخ الكل", self.copy_majal_with_matieres, "copy_paste"),
            ("📌 لصق وتحديث", self.paste_majal_with_matieres, "copy_paste")
        ]:
            b = QPushButton(text)
            b.setMinimumWidth(110)  # ⬅️ زيادة عرض الأزرار
            b.setProperty("actionType", act_type)
            b.clicked.connect(slot)
            majal_btns_layout.addWidget(b)
        majal_layout.addLayout(majal_btns_layout)

        self.tbl_competence_majal = self.create_clean_table(["كفاية المجال"])
        self.tbl_competence_majal.itemSelectionChanged.connect(self.on_competence_majal_selected)
        majal_layout.addWidget(self.tbl_competence_majal)
        splitter.addWidget(majal_widget)

        # جدول كفايات المواد
        matiere_widget = QWidget()
        matiere_layout = QVBoxLayout(matiere_widget)
        matiere_layout.addWidget(QLabel("<b>2. كفايات المواد المرتبطة بكفاية المجال المختارة</b>"))
        
        matiere_btns_layout = QHBoxLayout()
        for text, slot, act_type in [
            ("＋ إضافة مادة/كفاية", self.add_competence_matiere, "add"), 
            ("✎ تعديل", self.edit_competence_matiere, "edit"), 
            ("－ حذف", self.delete_competence_matiere, "delete")
        ]:
            b = QPushButton(text)
            b.setMinimumWidth(130)  # ⬅️ زيادة عرض الأزرار
            b.setProperty("actionType", act_type)
            b.clicked.connect(slot)
            matiere_btns_layout.addWidget(b)
        matiere_layout.addLayout(matiere_btns_layout)

        self.tbl_competence_matiere = self.create_clean_table(["المادة", "كفاية المادة"])
        matiere_layout.addWidget(self.tbl_competence_matiere)
        splitter.addWidget(matiere_widget)

        splitter.setSizes([520, 580])
        main_layout.addWidget(splitter, 1)

        close_btn = QPushButton("إغلاق")
        close_btn.setProperty("actionType", "close")
        close_btn.clicked.connect(self.accept)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    def create_clean_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def load_levels_and_majals(self):
        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                self.combo_level.blockSignals(True)
                self.combo_level.clear()
                for lid, lname in cursor.execute("SELECT id, name FROM level").fetchall():
                    self.combo_level.addItem(lname, lid)
                self.combo_level.blockSignals(False)

                self.combo_majal.blockSignals(True)
                self.combo_majal.clear()
                for mid, mname in cursor.execute("SELECT id, name FROM majal").fetchall():
                    self.combo_majal.addItem(mname, mid)
                self.combo_majal.blockSignals(False)

            self.on_filter_changed()
        except Exception as e:
            print(f"Error loading filters in manager: {e}")

    def on_filter_changed(self):
        self.selected_level_id = self.combo_level.currentData()
        self.selected_majal_id = self.combo_majal.currentData()
        self.load_competence_majal_data()

    def load_competence_majal_data(self):
        self.tbl_competence_majal.setUpdatesEnabled(False)
        self.tbl_competence_matiere.setUpdatesEnabled(False)
        try:
            self.tbl_competence_majal.setRowCount(0)
            self.tbl_competence_matiere.setRowCount(0)
            if not self.selected_level_id or not self.selected_majal_id:
                return

            with self.db.connect() as con:
                rows = con.execute(
                    """SELECT id, competence FROM competence_majal
                       WHERE id_majal = ? AND id_level = ? ORDER BY id""",
                    (self.selected_majal_id, self.selected_level_id),
                ).fetchall()

            for rec_id, competence in rows:
                row_index = self.tbl_competence_majal.rowCount()
                self.tbl_competence_majal.insertRow(row_index)
                item = QTableWidgetItem(competence)
                item.setData(Qt.UserRole, rec_id)
                self.tbl_competence_majal.setItem(row_index, 0, item)

            if self.tbl_competence_majal.rowCount() > 0:
                self.tbl_competence_majal.selectRow(0)
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر تحميل كفايات المجال: {exc}")
        finally:
            self.tbl_competence_majal.setUpdatesEnabled(True)
            self.tbl_competence_matiere.setUpdatesEnabled(True)

    def on_competence_majal_selected(self):
        row = self.tbl_competence_majal.currentRow()
        if row < 0:
            self.selected_competence_majal_id = None
            self.tbl_competence_matiere.setRowCount(0)
            return
        
        item = self.tbl_competence_majal.item(row, 0)
        self.selected_competence_majal_id = item.data(Qt.UserRole)
        self.load_competence_matiere_data()

    def load_competence_matiere_data(self):
        self.tbl_competence_matiere.setRowCount(0)
        if not self.selected_competence_majal_id:
            return

        try:
            with self.db.connect() as con:
                for row in con.execute("""
                    SELECT id, matiere, competence FROM competence_matiere 
                    WHERE id_competence_majal = ?
                """, (self.selected_competence_majal_id,)).fetchall():
                    r = self.tbl_competence_matiere.rowCount()
                    self.tbl_competence_matiere.insertRow(r)
                    
                    item_matiere = QTableWidgetItem(row[1])
                    item_matiere.setData(Qt.UserRole, row[0])
                    item_comp = QTableWidgetItem(row[2])
                    
                    self.tbl_competence_matiere.setItem(r, 0, item_matiere)
                    self.tbl_competence_matiere.setItem(r, 1, item_comp)
        except Exception as e:
            print(f"Error loading competence_matiere: {e}")

    def copy_majal_with_matieres(self):
        if not self.selected_competence_majal_id:
            if self.tbl_competence_majal.rowCount() > 0:
                self.tbl_competence_majal.selectRow(0)
            else:
                QMessageBox.warning(self, "تنبيه", "لا توجد كفاية مجال مسجلة في هذا المستوى والمجال لنسخها.")
                return

        row = self.tbl_competence_majal.currentRow()
        item = self.tbl_competence_majal.item(row, 0)
        majal_competence_text = item.text()

        matieres_list = []
        try:
            with self.db.connect() as con:
                for r in con.execute("""
                    SELECT matiere, competence FROM competence_matiere 
                    WHERE id_competence_majal = ?
                """, (self.selected_competence_majal_id,)).fetchall():
                    matieres_list.append({"matiere": r[0], "competence": r[1]})

            self.copied_majal_data = {
                "competence": majal_competence_text,
                "matieres": matieres_list
            }
            QMessageBox.information(self, "نجاح النسخ", f"تم نسخ كفاية المجال مع {len(matieres_list)} من كفايات المواد التابعة لها بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء نسخ البيانات:\n{e}")

    def paste_majal_with_matieres(self):
        if not self.copied_majal_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات منسوخة حالياً في الذاكرة.")
            return
        if not self.selected_level_id or not self.selected_majal_id:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار المستوى والمجال المستهدف للصق فيه.")
            return

        try:
            with self.db.connect() as con:
                cursor = con.cursor()
                cursor.execute("""
                    SELECT id FROM competence_majal 
                    WHERE id_majal = ? AND id_level = ?
                """, (self.selected_majal_id, self.selected_level_id))
                existing_row = cursor.fetchone()

                if existing_row:
                    majal_id = existing_row[0]
                    cursor.execute("""
                        UPDATE competence_majal 
                        SET competence = ? 
                        WHERE id = ?
                    """, (self.copied_majal_data["competence"], majal_id))
                    
                    cursor.execute("""
                        DELETE FROM competence_matiere 
                        WHERE id_competence_majal = ?
                    """, (majal_id,))
                else:
                    cursor.execute("""
                        INSERT INTO competence_majal (competence, id_majal, id_level) 
                        VALUES (?, ?, ?)
                    """, (self.copied_majal_data["competence"], self.selected_majal_id, self.selected_level_id))
                    majal_id = cursor.lastrowid

                for mat in self.copied_majal_data["matieres"]:
                    cursor.execute("""
                        INSERT INTO competence_matiere (matiere, competence, id_competence_majal) 
                        VALUES (?, ?, ?)
                    """, (mat["matiere"], mat["competence"], majal_id))

                con.commit()

            self.load_competence_majal_data()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء عملية اللصق:\n{e}")

    def add_competence_majal(self):
        if not self.selected_level_id or not self.selected_majal_id:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد المستوى والمجال أولاً.")
            return

        # ⬅️ استخدام الحقل المتعدد الأسطر (multiline)
        fields = [("نص كفاية المجال:", "multiline", "")]
        dlg = EntryDialog("إضافة كفاية مجال جديدة", fields, parent=self)
        if dlg.exec():
            vals = dlg.values()
            if not vals[0]:
                return
            try:
                with self.db.connect() as con:
                    con.execute("""
                        INSERT INTO competence_majal (competence, id_majal, id_level) 
                        VALUES (?, ?, ?)
                    """, (vals[0], self.selected_majal_id, self.selected_level_id))
                    con.commit()
                self.load_competence_majal_data()
                # تم إزالة رسالة النجاح المنبثقة بناءً على طلبك
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الإضافة (قد تكون موجودة مسبقاً):\n{e}")

    def edit_competence_majal(self):
        row = self.tbl_competence_majal.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد كفاية المجال للتعديل.")
            return
        
        item = self.tbl_competence_majal.item(row, 0)
        rec_id = item.data(Qt.UserRole)
        current_text = item.text()

        # ⬅️ استخدام الحقل المتعدد الأسطر (multiline)
        fields = [("تعديل نص كفاية المجال:", "multiline", current_text)]
        dlg = EntryDialog("تعديل كفاية المجال", fields, parent=self)
        if dlg.exec():
            vals = dlg.values()
            if not vals[0]:
                return
            try:
                with self.db.connect() as con:
                    con.execute("UPDATE competence_majal SET competence = ? WHERE id = ?", (vals[0], rec_id))
                    con.commit()
                self.load_competence_majal_data()
                # تم إزالة رسالة النجاح المنبثقة
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التحديث:\n{e}")

    def delete_competence_majal(self):
        row = self.tbl_competence_majal.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد كفاية المجال للحذف.")
            return
        
        item = self.tbl_competence_majal.item(row, 0)
        rec_id = item.data(Qt.UserRole)

        if QMessageBox.question(self, "تأكيد الحذف", "حذف كفاية المجال سيؤدي لحذف كافة كفايات المواد والمكونات التابعة لها. هل أنت متأكد؟", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                with self.db.connect() as con:
                    con.execute("DELETE FROM competence_majal WHERE id = ?", (rec_id,))
                    con.commit()
                self.load_competence_majal_data()
                self.tbl_competence_matiere.setRowCount(0)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف:\n{e}")

    def add_competence_matiere(self):
        if not self.selected_competence_majal_id:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد كفاية المجال أولاً.")
            return

        # ⬅️ استخدام الحقل المتعدد الأسطر (multiline) لكفاية المادة
        fields = [
            ("اسم المادة:", "line", ""),
            ("نص كفاية المادة:", "multiline", "")
        ]
        dlg = EntryDialog("إضافة كفاية ومادة جديدة", fields, parent=self)
        if dlg.exec():
            vals = dlg.values()
            matiere, competence = vals[0], vals[1]
            if not matiere or not competence:
                QMessageBox.warning(self, "بيانات ناقصة", "اسم المادة وكفاية المادة حقلان أساسيان.")
                return
            try:
                with self.db.connect() as con:
                    con.execute("""
                        INSERT INTO competence_matiere (matiere, competence, id_competence_majal) 
                        VALUES (?, ?, ?)
                    """, (matiere, competence, self.selected_competence_majal_id))
                    con.commit()
                self.load_competence_matiere_data()
                # تم إزالة رسالة النجاح المنبثقة
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الإضافة (قد تكون المادة مسجلة مسبقاً بنفس السياق):\n{e}")

    def edit_competence_matiere(self):
        row = self.tbl_competence_matiere.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد السطر المراد تعديله.")
            return
        
        item_matiere = self.tbl_competence_matiere.item(row, 0)
        item_comp = self.tbl_competence_matiere.item(row, 1)
        rec_id = item_matiere.data(Qt.UserRole)
        
        # ⬅️ استخدام الحقل المتعدد الأسطر (multiline) لكفاية المادة
        fields = [
            ("اسم المادة:", "line", item_matiere.text()),
            ("نص كفاية المادة:", "multiline", item_comp.text())
        ]
        dlg = EntryDialog("تعديل المادة وكفايتها", fields, parent=self)
        if dlg.exec():
            vals = dlg.values()
            matiere, competence = vals[0], vals[1]
            if not matiere or not competence:
                QMessageBox.warning(self, "بيانات ناقصة", "جميع الحقول مطلوبة.")
                return
            try:
                with self.db.connect() as con:
                    con.execute("""
                        UPDATE competence_matiere 
                        SET matiere = ?, competence = ? 
                        WHERE id = ?
                    """, (matiere, competence, rec_id))
                    con.commit()
                self.load_competence_matiere_data()
                # تم إزالة رسالة النجاح المنبثقة
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التحديث:\n{e}")

    def delete_competence_matiere(self):
        row = self.tbl_competence_matiere.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد المادة المراد حذفها.")
            return
        
        item = self.tbl_competence_matiere.item(row, 0)
        rec_id = item.data(Qt.UserRole)

        if QMessageBox.question(self, "تأكيد الحذف", "هل أنت متأكد من حذف هذه المادة وكفايتها؟", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                with self.db.connect() as con:
                    con.execute("DELETE FROM competence_matiere WHERE id = ?", (rec_id,))
                    con.commit()
                self.load_competence_matiere_data()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر الحذف:\n{e}")


class TimetableDialog(QDialog):
    """جدول الأوقات الأسبوعي: يُملأ آليًا بأكثر حصة تكرّرت في كل يوم وساعة (باستعمال pandas)."""

    DAYS = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    FIRST_HOUR = 8
    LAST_HOUR = 17          # نهاية آخر خانة 16:00 - 17:00
    _AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

    def __init__(self, df_history, parent=None, schedule=None):
        super().__init__(parent)
        self.setWindowTitle("جدول الأوقات")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1280, 520)
        self.n_slots = self.LAST_HOUR - self.FIRST_HOUR

        layout = QVBoxLayout(self)
        title = QLabel("🗓 جدول الأوقات")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E40AF; padding: 4px;")
        layout.addWidget(title)

        self.table = QTableWidget(len(self.DAYS), self.n_slots)
        self.table.setHorizontalHeaderLabels(
            [f"{h:02d}:00 - {h + 1:02d}:00" for h in range(self.FIRST_HOUR, self.LAST_HOUR)]
        )
        self.table.setVerticalHeaderLabels(self.DAYS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setMinimumWidth(80)
        layout.addWidget(self.table, 1)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #555;")
        layout.addWidget(self.info_label)

        buttons = QDialogButtonBox()
        buttons.addButton("إغلاق", QDialogButtonBox.RejectRole)
        set_dialog_button_action_types(buttons)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        schedule = (
            schedule if schedule is not None else self.build_schedule(df_history)
        )
        self.fill_table(schedule)

    # ---------- التحليل ----------
    @classmethod
    def _parse_heure(cls, text):
        """يرجع (بداية، نهاية) بالدقائق من نص مثل '08:00-09:00'، والنهاية None إن غابت."""
        text = str(text or "").translate(cls._AR_DIGITS)
        found = re.findall(r"(\d{1,2})\s*[:hH.]\s*(\d{2})", text)
        if not found:
            return None, None
        start = int(found[0][0]) * 60 + int(found[0][1])
        end = int(found[1][0]) * 60 + int(found[1][1]) if len(found) > 1 else None
        return start, end

    @classmethod
    def _duration_minutes(cls, heure, time_text):
        start, end = cls._parse_heure(heure)
        if start is not None and end is not None and end > start:
            return end - start
        m = re.search(r"\d+", str(time_text or "").translate(cls._AR_DIGITS))
        return int(m.group()) if m else 60

    @classmethod
    def build_schedule(cls, df):
        """يرجع {صف_اليوم: [(عمود، امتداد، نص، تكرار)]} بعد اختيار الأكثر تكرارًا دون تداخل."""
        if df is None or df.empty:
            return {}
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["wd"] = df["date"].dt.dayofweek
        df = df[df["wd"] <= 5]          # من الإثنين إلى السبت فقط

        n_slots = cls.LAST_HOUR - cls.FIRST_HOUR
        counter = {}
        for r in df.itertuples(index=False):
            classe = str(r.classe or "").strip()
            majal = str(r.majal or "").strip()
            if not classe and not majal:
                continue
            start, _end = cls._parse_heure(r.heure)
            if start is None:
                continue
            col = start // 60 - cls.FIRST_HOUR
            if not 0 <= col < n_slots:
                continue
            minutes = cls._duration_minutes(r.heure, r.time)
            span = max(1, min(minutes // 60, n_slots - col))   # 120 دقيقة => خليتان
            key = (int(r.wd), col, span, classe, majal)
            counter[key] = counter.get(key, 0) + 1

        schedule = {}
        for wd in range(len(cls.DAYS)):
            candidates = [(cnt, k) for k, cnt in counter.items() if k[0] == wd]
            # الأكثر تكرارًا أولًا، وعند التساوي الأبكر ثم الأطول
            candidates.sort(key=lambda x: (-x[0], x[1][1], -x[1][2]))
            occupied, cells = set(), []
            for cnt, (_wd, col, span, classe, majal) in candidates:
                cols = set(range(col, col + span))
                if cols & occupied:
                    continue
                occupied |= cols
                text = f"{classe}:{majal}" if classe and majal else (classe or majal)
                cells.append((col, span, text, cnt))
            schedule[wd] = cells
        return schedule

    # ---------- العرض ----------
    def fill_table(self, schedule):
        palette = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FCE7F3", "#E0E7FF", "#CCFBF1", "#FFEDD5"]
        colors, total = {}, 0
        for wd, cells in schedule.items():
            for col, span, text, cnt in cells:
                majal = text.split(":", 1)[-1]
                color = colors.setdefault(majal, palette[len(colors) % len(palette)])
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(color))
                item.setForeground(QColor("#111827"))
                item.setToolTip(f"{text}\nتكرّرت {cnt} مرة" + (" (حصة مدتها 120 دقيقة)" if span > 1 else ""))
                self.table.setItem(wd, col, item)
                if span > 1:
                    self.table.setSpan(wd, col, 1, span)
                total += 1
        if total:
            self.info_label.setText(
                "يُملأ الجدول بأكثر حصة تكرّرت في كل يوم وساعة بحسب السجل. "
                "الحصص ذات 120 دقيقة تُدمج خليتاها."
            )
        else:
            self.info_label.setText("لا توجد حصص مسجلة بعد لبناء جدول الأوقات.")





class ConceptManagerDialog(QDialog):
    """حوار إدارة المفاهيم (CRUD كامل لجدول concept).

    يُفتح بالاختصار Ctrl+Shift+R. عمود name فريد (UNIQUE) ولا يُسمح بالتكرار.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إدارة المفاهيم المتصلة بالمقاربة بالكفايات")
        self.resize(720, 520)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = db if db else Database(DB_PATH)
        self.selected_concept_id = None
        self.init_ui()
        self.load_concepts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title_label = QLabel("🧠 إدارة المفاهيم (اسم العنصر + محتوى العنصر)")
        title_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1E40AF; padding: 5px;"
        )
        main_layout.addWidget(title_label)

        btns_layout = QHBoxLayout()
        for text, slot, act_type in [
            ("＋ إضافة", self.add_concept, "add"),
            ("✎ تعديل", self.edit_concept, "edit"),
            ("－ حذف", self.delete_concept, "delete"),
        ]:
            b = QPushButton(text)
            b.setMinimumWidth(110)
            b.setProperty("actionType", act_type)
            b.clicked.connect(slot)
            btns_layout.addWidget(b)
        btns_layout.addStretch()
        main_layout.addLayout(btns_layout)

        self.tbl_concepts = QTableWidget(0, 2)
        self.tbl_concepts.setHorizontalHeaderLabels(["اسم العنصر", "محتوى العنصر"])
        self.tbl_concepts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_concepts.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_concepts.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_concepts.setAlternatingRowColors(True)
        self.tbl_concepts.verticalHeader().setVisible(False)
        self.tbl_concepts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_concepts.itemSelectionChanged.connect(self.on_concept_selected)
        main_layout.addWidget(self.tbl_concepts, 1)

        self.lbl_status = QLabel("0 مفهوم")
        self.lbl_status.setStyleSheet("color: #6B7280; padding: 3px;")
        main_layout.addWidget(self.lbl_status)

        close_btn = QPushButton("إغلاق")
        close_btn.setProperty("actionType", "close")
        close_btn.clicked.connect(self.accept)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    def load_concepts(self):
        self.tbl_concepts.setUpdatesEnabled(False)
        try:
            self.tbl_concepts.setRowCount(0)
            with self.db.connect() as con:
                rows = con.execute(
                    "SELECT id, name, content FROM concept ORDER BY name COLLATE NOCASE"
                ).fetchall()
            for rec_id, name, content in rows:
                r = self.tbl_concepts.rowCount()
                self.tbl_concepts.insertRow(r)
                item_name = QTableWidgetItem(name)
                item_name.setData(Qt.UserRole, rec_id)
                self.tbl_concepts.setItem(r, 0, item_name)
                self.tbl_concepts.setItem(r, 1, QTableWidgetItem(content or ""))
            self.lbl_status.setText(f"{self.tbl_concepts.rowCount()} مفهوم")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر تحميل المفاهيم:\n{exc}")
        finally:
            self.tbl_concepts.setUpdatesEnabled(True)

    def on_concept_selected(self):
        row = self.tbl_concepts.currentRow()
        if row < 0:
            self.selected_concept_id = None
            return
        item = self.tbl_concepts.item(row, 0)
        self.selected_concept_id = item.data(Qt.UserRole) if item else None

    def add_concept(self):
        dlg = EntryDialog(
            "إضافة مفهوم جديد",
            [("اسم العنصر:", "line", ""), ("محتوى العنصر:", "multiline", "")],
            parent=self,
        )
        if not dlg.exec():
            return
        vals = dlg.values()
        name = vals[0]
        content = vals[1]
        try:
            self.db.save_concept(name, content)
            self.load_concepts()
        except ValueError as exc:
            QMessageBox.warning(self, "اسم مكرر", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر إضافة المفهوم:\n{exc}")

    def edit_concept(self):
        if not self.selected_concept_id:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مفهوم للتعديل.")
            return
        row = self.tbl_concepts.currentRow()
        current_name = self.tbl_concepts.item(row, 0).text()
        current_content = self.tbl_concepts.item(row, 1).text()
        dlg = EntryDialog(
            "تعديل المفهوم",
            [("اسم العنصر:", "line", ""), ("محتوى العنصر:", "multiline", "")],
            values=[current_name, current_content],
            parent=self,
        )
        if not dlg.exec():
            return
        vals = dlg.values()
        try:
            self.db.save_concept(vals[0], vals[1], concept_id=self.selected_concept_id)
            self.load_concepts()
        except ValueError as exc:
            QMessageBox.warning(self, "اسم مكرر", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر تعديل المفهوم:\n{exc}")

    def delete_concept(self):
        if not self.selected_concept_id:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مفهوم للحذف.")
            return
        row = self.tbl_concepts.currentRow()
        name = self.tbl_concepts.item(row, 0).text()
        confirm = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل تريد حذف المفهوم '{name}'؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.db.delete_concept(self.selected_concept_id)
            self.selected_concept_id = None
            self.load_concepts()
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"تعذر حذف المفهوم:\n{exc}")
