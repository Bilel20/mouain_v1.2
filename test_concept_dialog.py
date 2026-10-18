# -*- coding: utf-8 -*-
"""اختبار ConceptManagerDialog مع قاعدة بيانات مؤقتة (بدون تفاعل مستخدم)."""
import os
import sys
import tempfile

from PySide6.QtWidgets import QApplication, QMessageBox

import database
from dialogs import ConceptManagerDialog

app = QApplication(sys.argv)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)  # auto-confirm

tmp = tempfile.mktemp(suffix=".db")
db = database.Database(tmp)

# بيانات مبدئية
db.save_concept("الكفاية", "قدرة على توظيف الموارد لحل مشكلات")
db.save_concept("المقاربة بالكفايات", "منهجية تجعل المتعلم محور العملية")

dlg = ConceptManagerDialog(db=db)
assert dlg.tbl_concepts.rowCount() == 2, dlg.tbl_concepts.rowCount()
assert dlg.windowTitle(), "title missing"
print("dialog built, rows:", dlg.tbl_concepts.rowCount())

# أنواع الأزرار موحدة عبر setProperty
btn_types = []
for btn in dlg.findChildren(type(dlg.tbl_concepts)):
    pass
from PySide6.QtWidgets import QPushButton
for btn in dlg.findChildren(QPushButton):
    btn_types.append((btn.text(), btn.property("actionType")))
print("buttons:", btn_types)
assert all(bt[1] for bt in btn_types), "some button missing actionType"

# محاكاة إضافة مفهوم مكرر — يجب أن يرفع ValueError
try:
    dlg.db.save_concept("الكفاية", "x")
    print("FAIL: duplicate allowed in dialog path")
    sys.exit(1)
except ValueError as exc:
    print("duplicate blocked in dialog path:", exc)

# تحديد صف ومحاكاة الحذف
dlg.show()
dlg.tbl_concepts.setFocus()
dlg.tbl_concepts.setCurrentCell(0, 0)
dlg.on_concept_selected()
print("selected id:", dlg.selected_concept_id)
assert dlg.selected_concept_id is not None, \
    f"selection failed; currentRow={dlg.tbl_concepts.currentRow()}"
dlg.close()

for path in (tmp,):
    try:
        os.remove(path)
    except PermissionError:
        pass
print("DIALOG TEST PASSED")
