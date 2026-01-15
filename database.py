import sqlite3
from config import Config

class Database:
    def __init__(self, db_name="tarot_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_text TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_by INTEGER,
                answer_text TEXT,
                moderated BOOLEAN DEFAULT 0,
                moderated_by INTEGER,
                moderated_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        self.conn.commit()
    
    def add_question(self, user_id, question_text):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO questions (user_id, question_text)
            VALUES (?, ?)
        ''', (user_id, question_text))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_unanswered_questions(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT q.id, q.question_text, u.username, u.first_name, q.created_at
            FROM questions q
            JOIN users u ON q.user_id = u.user_id
            WHERE q.status = 'new' AND q.moderated = 1
            ORDER BY q.created_at
        ''')
        return cursor.fetchall()
    
    def add_answer(self, question_id, tarot_id, answer_text):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE questions 
            SET answered_by = ?, answer_text = ?, status = 'answered'
            WHERE id = ?
        ''', (tarot_id, answer_text, question_id))
        self.conn.commit()
    
    def get_questions_for_moderation(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT q.id, q.question_text, q.answer_text, 
                   u1.username as asker, u2.username as answerer
            FROM questions q
            JOIN users u1 ON q.user_id = u1.user_id
            LEFT JOIN users u2 ON q.answered_by = u2.user_id
            WHERE q.moderated = 0
            ORDER BY q.created_at
        ''')
        return cursor.fetchall()
    
    def moderate_question(self, question_id, approve, admin_id):
        cursor = self.conn.cursor()
        if approve:
            cursor.execute('''
                UPDATE questions 
                SET moderated = 1, moderated_by = ?, moderated_at = CURRENT_TIMESTAMP,
                    status = CASE WHEN answer_text IS NOT NULL THEN 'answered' ELSE 'new' END
                WHERE id = ?
            ''', (admin_id, question_id))
        else:
            cursor.execute('''
                UPDATE questions 
                SET moderated = 1, moderated_by = ?, moderated_at = CURRENT_TIMESTAMP,
                    status = 'rejected'
                WHERE id = ?
            ''', (admin_id, question_id))
        self.conn.commit()
        # Получаем ID пользователя для уведомления
        cursor.execute('SELECT user_id FROM questions WHERE id = ?', (question_id,))
        return cursor.fetchone()
    
    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def set_user_role(self, user_id, role):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
        self.conn.commit()
    
    def get_question_info(self, question_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM questions WHERE id = ?', (question_id,))
        return cursor.fetchone()
    
    def get_user_questions(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, question_text, status, answer_text
            FROM questions
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
