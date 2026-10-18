# -*- coding: utf-8 -*-
"""اختبار سريع لجدول concept وقيود التفرد وحوار الإدارة."""
import sqlite3
import sys

import database
import tempfile, os


def main():
    tmp = tempfile.mktemp(suffix=".db")
    db = database.Database(tmp)

    # إضافة
    db.save_concept("مفهوم أ", "محتوى 1")
    assert db.concepts() == [(1, "مفهوم أ", "محتوى 1")], db.concepts()
    print("insert OK")

    # منع التكرار عبر save_concept
    try:
        db.save_concept("مفهوم أ", "محتوى 2")
        print("FAIL: duplicate allowed via save_concept")
        sys.exit(1)
    except ValueError as exc:
        print("duplicate blocked via save_concept:", exc)

    # منع التكرار على مستوى المخطط (قيد UNIQUE)
    con = db.connect()
    con.execute("INSERT INTO concept(name, content) VALUES('مكرر', 'x')")
    try:
        con.execute("INSERT INTO concept(name, content) VALUES('مكرر', 'y')")
        print("FAIL: schema-level duplicate allowed")
        sys.exit(1)
    except sqlite3.IntegrityError as exc:
        print("schema UNIQUE enforced:", exc)
    con.close()

    # التعديل مع الإبقاء على نفس الاسم مسموح
    db.save_concept("مفهوم أ", "محتوى معدل", concept_id=1)
    assert db.concepts() == [(1, "مفهوم أ", "محتوى معدل")], db.concepts()
    print("edit OK")

    # الحذف
    db.delete_concept(1)
    assert db.concepts() == [], db.concepts()
    print("delete OK")

    # الترقية: مخطط قديم بدون UNIQUE يجب أن يتحول تلقائياً
    tmp2 = tempfile.mktemp(suffix=".db")
    old = sqlite3.connect(tmp2)
    old.executescript("""
        CREATE TABLE concept (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        INSERT INTO concept(name, content) VALUES('قديم', 'نص');
        INSERT INTO concept(name, content) VALUES('قديم', 'نص آخر');
    """)
    old.commit()
    old.close()
    db2 = database.Database(tmp2)
    schema = db2.connect().execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='concept'"
    ).fetchone()[0]
    assert "UNIQUE" in schema.upper(), schema
    rows = db2.concepts()
    assert len(rows) == 1 and rows[0][1] == "قديم", rows  # أُبقي أول صف فقط
    print("legacy migration OK:", rows)
    db2.connect().close()
    for path in (tmp2, tmp):
        try:
            os.remove(path)
        except PermissionError:
            pass

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
