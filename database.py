# -*- coding: utf-8 -*-
"""Extracted module database."""
import re
import sqlite3
from datetime import datetime

from app_config import DB_PATH, SCHOOL_INFO_COLUMNS
class Database:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        self.init_db()

    def connect(self):
        # إعادة استعمال العبارات وتقليل انتظار القفل عند فتح أكثر من نافذة.
        con = sqlite3.connect(self.path, timeout=10, cached_statements=256)
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def init_db(self):
        with self.connect() as c:
            # WAL يحسن التوازي بين القراءة والكتابة دون تغيير بنية البيانات.
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.executescript("""
            CREATE TABLE IF NOT EXISTS ann_scolaire (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_annee TEXT NOT NULL DEFAULT '2026-2027',
                nom_ecole TEXT DEFAULT '',
                nom_enseignant TEXT DEFAULT '',
                nom_inspecteur TEXT DEFAULT '',
                grade TEXT DEFAULT '',
                nom_assistant_pedagogique TEXT DEFAULT '',
                diplomes_scientifiques TEXT DEFAULT '',
                date_recrutement TEXT DEFAULT '',
                date_titularisation TEXT DEFAULT '',
                date_derniere_visite TEXT DEFAULT '',
                note_pedagogique TEXT DEFAULT '',
                resume_rapport_visite TEXT DEFAULT '',
                langue TEXT DEFAULT '',
                telephone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                situation_familiale TEXT DEFAULT '',
                nombre_enfants INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS day_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ann_scolaire_id INTEGER NOT NULL,
                UNIQUE(date, ann_scolaire_id),
                FOREIGN KEY(ann_scolaire_id) REFERENCES ann_scolaire(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS hessa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classe TEXT DEFAULT '',
                majal TEXT DEFAULT '',
                heure TEXT DEFAULT '',
                time TEXT DEFAULT '',
                wehda_number INTEGER DEFAULT 1,
                hessa_number INTEGER DEFAULT 1,
                namat_taallom TEXT DEFAULT '',
                day_data_id INTEGER NOT NULL,
                FOREIGN KEY(day_data_id) REFERENCES day_data(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS nachat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                time TEXT DEFAULT '',
                hessa_id INTEGER NOT NULL,
                FOREIGN KEY(hessa_id) REFERENCES hessa(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS nachat_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                value_text TEXT DEFAULT '',
                nachat_id INTEGER NOT NULL,
                FOREIGN KEY(nachat_id) REFERENCES nachat(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS level (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS majal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS competence_majal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competence TEXT NOT NULL,
                id_majal INTEGER NOT NULL,
                id_level INTEGER NOT NULL,
                FOREIGN KEY(id_majal) REFERENCES majal(id) ON DELETE CASCADE,
                FOREIGN KEY(id_level) REFERENCES level(id) ON DELETE CASCADE,
                UNIQUE(competence, id_majal, id_level)
            );

            CREATE TABLE IF NOT EXISTS competence_matiere (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matiere TEXT NOT NULL,
                competence TEXT NOT NULL,
                id_competence_majal INTEGER NOT NULL,
                FOREIGN KEY(id_competence_majal) REFERENCES competence_majal(id) ON DELETE CASCADE,
                UNIQUE(matiere, competence, id_competence_majal)
            );

            CREATE TABLE IF NOT EXISTS moukawan_kifaya (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competence TEXT NOT NULL,
                id_competence_matiere INTEGER NOT NULL,
                FOREIGN KEY(id_competence_matiere) REFERENCES competence_matiere(id) ON DELETE CASCADE,
                UNIQUE(competence, id_competence_matiere)
            );

            CREATE TABLE IF NOT EXISTS objectif_specifique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                objectif_specifique TEXT NOT NULL,
                id_moukawa_kifaya INTEGER NOT NULL,
                description TEXT DEFAULT '',
                FOREIGN KEY(id_moukawa_kifaya) REFERENCES moukawan_kifaya(id) ON DELETE CASCADE,
                UNIQUE(objectif_specifique, id_moukawa_kifaya)
            );

            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                id_objectif_specifique INTEGER NOT NULL,
                description TEXT DEFAULT '',
                FOREIGN KEY(id_objectif_specifique) REFERENCES objectif_specifique(id) ON DELETE CASCADE,
                UNIQUE(content, id_objectif_specifique)
            );

            CREATE TABLE IF NOT EXISTS concept (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                content TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            """)
            existing_columns = {
                row[1] for row in c.execute("PRAGMA table_info(ann_scolaire)")
            }
            new_columns = (
                ("nom_assistant_pedagogique", "TEXT DEFAULT ''"),
                ("diplomes_scientifiques", "TEXT DEFAULT ''"),
                ("date_recrutement", "TEXT DEFAULT ''"),
                ("date_titularisation", "TEXT DEFAULT ''"),
                ("date_derniere_visite", "TEXT DEFAULT ''"),
                ("note_pedagogique", "TEXT DEFAULT ''"),
                ("resume_rapport_visite", "TEXT DEFAULT ''"),
                ("langue", "TEXT DEFAULT ''"),
                ("telephone", "TEXT DEFAULT ''"),
                ("email", "TEXT DEFAULT ''"),
                ("situation_familiale", "TEXT DEFAULT ''"),
                ("nombre_enfants", "INTEGER NOT NULL DEFAULT 0"),
            )
            for column_name, column_definition in new_columns:
                if column_name not in existing_columns:
                    c.execute(
                        f"ALTER TABLE ann_scolaire ADD COLUMN "
                        f"{column_name} {column_definition}"
                    )

            c.executescript("""
            DELETE FROM level WHERE id NOT IN (
                SELECT MIN(id) FROM level GROUP BY name
            );
            DELETE FROM majal WHERE id NOT IN (
                SELECT MIN(id) FROM majal GROUP BY name
            );
            """)

            # ترقية جدول concept القديم: إضافة قيد UNIQUE على name إن لم يكن موجوداً.
            concept_sql = c.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='concept'"
            ).fetchone()
            if concept_sql and "UNIQUE" not in (concept_sql[0] or "").upper():
                c.executescript("""
                CREATE TABLE concept_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    content TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                );
                INSERT OR IGNORE INTO concept_new(id, name, content, created_at)
                    SELECT id, name, content, created_at FROM concept;
                DROP TABLE concept;
                ALTER TABLE concept_new RENAME TO concept;
                """)

            # فهارس تخدم الاستعلامات المتكررة في دفتر الدروس والبرامج الرسمية.
            c.executescript("""
            CREATE INDEX IF NOT EXISTS idx_day_data_year_date ON day_data(ann_scolaire_id, date);
            CREATE INDEX IF NOT EXISTS idx_hessa_day ON hessa(day_data_id);
            CREATE INDEX IF NOT EXISTS idx_nachat_hessa ON nachat(hessa_id);
            CREATE INDEX IF NOT EXISTS idx_nachat_title ON nachat(title);
            CREATE INDEX IF NOT EXISTS idx_nachat_detail_parent_key ON nachat_detail(nachat_id, key_name);
            CREATE INDEX IF NOT EXISTS idx_competence_majal_filter ON competence_majal(id_level, id_majal);
            CREATE INDEX IF NOT EXISTS idx_competence_matiere_parent ON competence_matiere(id_competence_majal);
            CREATE INDEX IF NOT EXISTS idx_moukawan_parent ON moukawan_kifaya(id_competence_matiere);
            CREATE INDEX IF NOT EXISTS idx_objectif_parent ON objectif_specifique(id_moukawa_kifaya);
            CREATE INDEX IF NOT EXISTS idx_content_parent ON content(id_objectif_specifique);
            CREATE INDEX IF NOT EXISTS idx_concept_name ON concept(name);
            """)

            row = c.execute("SELECT id FROM ann_scolaire ORDER BY id LIMIT 1").fetchone()
            if row:
                self.year_id = row[0]
            else:
                cur = c.execute(
                    "INSERT INTO ann_scolaire(nom_annee) VALUES(?)", ("2026-2027",)
                )
                self.year_id = cur.lastrowid

    def get_day_id(self, day):
        with self.connect() as c:
            row = c.execute(
                "SELECT id FROM day_data WHERE date=? AND ann_scolaire_id=?",
                (day, self.year_id)
            ).fetchone()
            if row:
                return row[0]
            cur = c.execute(
                "INSERT INTO day_data(date, ann_scolaire_id) VALUES(?,?)",
                (day, self.year_id)
            )
            return cur.lastrowid

    def lessons(self, day_id):
        with self.connect() as c:
            return c.execute("""SELECT id, hessa_number, classe, majal, heure, time,
                wehda_number, namat_taallom FROM hessa
                WHERE day_data_id=? ORDER BY id ASC""", (day_id,)).fetchall()

    def recorded_day_id(self, day):
        with self.connect() as c:
            row = c.execute("""
                SELECT d.id
                FROM day_data d
                WHERE d.date=? AND d.ann_scolaire_id=?
                    AND EXISTS (SELECT 1 FROM hessa h WHERE h.day_data_id=d.id)
            """, (day, self.year_id)).fetchone()
            return row[0] if row else None

    def lessons_for_weekday(self, weekday_num, target_day):
        sqlite_weekday = (weekday_num + 1) % 7
        with self.connect() as c:
            row = c.execute("""
                SELECT d.id
                FROM day_data d
                WHERE d.ann_scolaire_id=?
                    AND CAST(strftime('%w', d.date) AS INTEGER)=?
                    AND d.date<>?
                    AND EXISTS (SELECT 1 FROM hessa h WHERE h.day_data_id=d.id)
                ORDER BY ABS(julianday(d.date)-julianday(?)),
                    CASE WHEN d.date<=? THEN 0 ELSE 1 END,
                    d.date DESC
                LIMIT 1
            """, (self.year_id, sqlite_weekday, target_day, target_day, target_day)).fetchone()
            if not row:
                return []
            return c.execute("""
                SELECT classe, majal, heure, time
                FROM hessa
                WHERE day_data_id=?
                ORDER BY id
            """, (row[0],)).fetchall()

    def lesson_number_defaults(self, classe, majal):
        with self.connect() as c:
            rows = c.execute("""
                SELECT h.wehda_number, h.hessa_number, h.time
                FROM hessa h
                JOIN day_data d ON d.id=h.day_data_id
                WHERE d.ann_scolaire_id=? AND h.classe=? AND h.majal=?
                ORDER BY d.date DESC, h.id DESC
            """, (self.year_id, classe, majal)).fetchall()

        valid_rows = []
        for unit, lesson_number, duration in rows:
            try:
                unit = int(unit)
                lesson_number = int(lesson_number)
            except (TypeError, ValueError):
                continue
            if unit > 0 and lesson_number > 0:
                valid_rows.append((unit, lesson_number, duration))

        if not valid_rows:
            return 1, 1

        largest_unit = max(row[0] for row in valid_rows)
        rows_for_unit = [row for row in valid_rows if row[0] == largest_unit]
        largest_lesson = max(row[1] for row in rows_for_unit)
        last_lesson = next(row for row in rows_for_unit if row[1] == largest_lesson)
        is_arabic = "اللغة العربية" in majal.strip()
        has_120_minute_lesson = bool(re.search(r"\b120\b", str(last_lesson[2] or "")))
        next_lesson = largest_lesson + (2 if is_arabic and has_120_minute_lesson else 1)
        return largest_unit, next_lesson

    def lesson(self, lesson_id):
        with self.connect() as c:
            return c.execute("""SELECT id, classe, majal, heure, time, wehda_number,
                hessa_number, namat_taallom, day_data_id FROM hessa WHERE id=?""",
                (lesson_id,)).fetchone()

    def save_lessons(self, lessons, day_id):
        with self.connect() as c:
            c.executemany("""
                INSERT INTO hessa(classe,majal,heure,time,wehda_number,
                    hessa_number,namat_taallom,day_data_id)
                VALUES(?,?,?,?,?,?,?,?)
            """, [(*lesson, day_id) for lesson in lessons])

    def save_lesson(self, values, day_id, lesson_id=None):
        with self.connect() as c:
            if lesson_id:
                c.execute("""UPDATE hessa SET classe=?, majal=?, heure=?, time=?,
                    wehda_number=?, hessa_number=?, namat_taallom=? WHERE id=?""",
                    (*values, lesson_id))
            else:
                c.execute("""INSERT INTO hessa(classe,majal,heure,time,wehda_number,
                    hessa_number,namat_taallom,day_data_id) VALUES(?,?,?,?,?,?,?,?)""",
                    (*values, day_id))
                return c.execute("SELECT last_insert_rowid()").fetchone()[0]
        return lesson_id

    def delete_lesson(self, lesson_id):
        with self.connect() as c:
            c.execute("DELETE FROM hessa WHERE id=?", (lesson_id,))

    def activities(self, lesson_id):
        with self.connect() as c:
            return c.execute("SELECT id,title,time FROM nachat WHERE hessa_id=? ORDER BY id",
                             (lesson_id,)).fetchall()

    def save_activity(self, title, time, lesson_id, activity_id=None):
        with self.connect() as c:
            if activity_id:
                c.execute("UPDATE nachat SET title=?,time=? WHERE id=?",
                          (title, time, activity_id))
                return activity_id
            cur = c.execute("INSERT INTO nachat(title,time,hessa_id) VALUES(?,?,?)",
                            (title, time, lesson_id))
            return cur.lastrowid

    def delete_activity(self, activity_id):
        with self.connect() as c:
            c.execute("DELETE FROM nachat WHERE id=?", (activity_id,))

    def details(self, activity_id):
        with self.connect() as c:
            return c.execute("""SELECT id,key_name,value_text FROM nachat_detail
                WHERE nachat_id=? ORDER BY id""", (activity_id,)).fetchall()

    def save_detail(self, key, value, activity_id, detail_id=None):
        with self.connect() as c:
            if detail_id:
                c.execute("UPDATE nachat_detail SET key_name=?,value_text=? WHERE id=?",
                          (key, value, detail_id))
                return detail_id
            cur = c.execute("""INSERT INTO nachat_detail(key_name,value_text,nachat_id)
                VALUES(?,?,?)""", (key, value, activity_id))
            return cur.lastrowid

    def delete_detail(self, detail_id):
        with self.connect() as c:
            c.execute("DELETE FROM nachat_detail WHERE id=?", (detail_id,))

    def school_info(self):
        with self.connect() as c:
            columns = ", ".join(SCHOOL_INFO_COLUMNS)
            return c.execute(
                f"SELECT {columns} FROM ann_scolaire WHERE id=?",
                (self.year_id,)
            ).fetchone()

    def update_school_info(self, values):
        if len(values) != len(SCHOOL_INFO_COLUMNS):
            raise ValueError(
                f"Expected {len(SCHOOL_INFO_COLUMNS)} school-info values, "
                f"received {len(values)}."
            )
        assignments = ", ".join(
            f"{column}=?" for column in SCHOOL_INFO_COLUMNS
        )
        with self.connect() as c:
            c.execute(
                f"UPDATE ann_scolaire SET {assignments} WHERE id=?",
                (*values, self.year_id)
            )

    def get_latest_date(self):
        with self.connect() as c:
            row = c.execute(
                "SELECT date FROM day_data WHERE ann_scolaire_id=? ORDER BY date DESC LIMIT 1",
                (self.year_id,)
            ).fetchone()
            return row[0] if row else None
        
    def cleanup_empty_days(self):
        with self.connect() as c:
            c.execute("""
                DELETE FROM day_data 
                WHERE ann_scolaire_id=? 
                AND id NOT IN (SELECT DISTINCT day_data_id FROM hessa)
            """, (self.year_id,))

    # ---------------------------------------------------------
    # المفاهيم الجديدة (concept): اسم العنصر + محتوى العنصر
    # ---------------------------------------------------------
    def concepts(self):
        with self.connect() as c:
            return c.execute(
                "SELECT id, name, content FROM concept ORDER BY id ASC"
            ).fetchall()

    def save_concept(self, name, content, concept_id=None):
        """إضافة/تعديل مفهوم. يرفع ValueError إذا كان الاسم مكرراً."""
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم المفهوم مطلوب")
        with self.connect() as c:
            duplicate = c.execute(
                "SELECT id FROM concept WHERE name = ? AND id IS NOT ?",
                (name, concept_id),
            ).fetchone()
            if duplicate:
                raise ValueError(f"المفهوم '{name}' موجود مسبقاً")
            if concept_id:
                c.execute(
                    "UPDATE concept SET name=?, content=? WHERE id=?",
                    (name, content, concept_id),
                )
                return concept_id
            cur = c.execute(
                "INSERT INTO concept(name, content) VALUES(?, ?)",
                (name, content),
            )
            return cur.lastrowid

    def delete_concept(self, concept_id):
        with self.connect() as c:
            c.execute("DELETE FROM concept WHERE id=?", (concept_id,))

    def predict_next_detail_key(self, activity_title, namat_taallom, current_count):
        try:
            with self.connect() as c:
                cursor = c.execute("""
                    SELECT n.id, d.key_name
                    FROM nachat_detail d
                    JOIN nachat n ON d.nachat_id = n.id
                    JOIN hessa h ON n.hessa_id = h.id
                    WHERE n.title = ? AND h.namat_taallom = ?
                    ORDER BY n.id, d.id
                """, (activity_title, namat_taallom))
                rows = cursor.fetchall()
                
                sequences = {}
                for nachat_id, key_name in rows:
                    if nachat_id not in sequences:
                        sequences[nachat_id] = []
                    sequences[nachat_id].append(key_name)
                
                candidates = []
                for seq in sequences.values():
                    if len(seq) > current_count:
                        candidates.append(seq[current_count])
                
                if candidates:
                    from collections import Counter
                    most_common = Counter(candidates).most_common(1)
                    if most_common:
                        return most_common[0][0]
        except Exception as e:
            print(f"Prediction error: {e}")
        return ""


class SchoolDataFormatter:
    def __init__(self, db_name=DB_PATH):
        self.db_name = str(db_name)

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def normalize_date(self, date_str: str) -> str:
        date_str = date_str.strip()
        formats_to_try = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str


