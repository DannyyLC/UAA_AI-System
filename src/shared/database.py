"""
Módulo para gestión de la base de datos SQLite.
Maneja usuarios, contraseñas y conversaciones.
"""
import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str = None):
        """
        Inicializa la conexión a la base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos. 
                     Si es None, usa DATABASE_PATH del entorno o valor por defecto.
        """
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'data/db/app.db')
        
        # Asegurar que el directorio existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establece conexión con la base de datos."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
    
    def _create_tables(self):
        """Crea las tablas necesarias si no existen."""
        cursor = self.conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabla de conversaciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabla de mensajes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,  -- 'user' o 'assistant'
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON para información adicional
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabla de sesiones (para manejo de tokens, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Índices para mejorar el rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
        
        self.conn.commit()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea una contraseña usando SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    # === Métodos para usuarios ===
    
    def create_user(self, username: str, email: str, password: str) -> Optional[int]:
        """
        Crea un nuevo usuario.
        
        Returns:
            ID del usuario creado o None si hay error.
        """
        try:
            cursor = self.conn.cursor()
            password_hash = self.hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Autentica un usuario.
        
        Returns:
            Diccionario con datos del usuario si es válido, None en caso contrario.
        """
        cursor = self.conn.cursor()
        password_hash = self.hash_password(password)
        cursor.execute(
            'SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1',
            (username, password_hash)
        )
        row = cursor.fetchone()
        
        if row:
            # Actualizar último login
            cursor.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (row['id'],)
            )
            self.conn.commit()
            return dict(row)
        return None
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un usuario por ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # === Métodos para conversaciones ===
    
    def create_conversation(self, user_id: int, title: str = "Nueva conversación") -> int:
        """Crea una nueva conversación."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO conversations (user_id, title) VALUES (?, ?)',
            (user_id, title)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_user_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las conversaciones de un usuario."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC',
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una conversación por ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Elimina una conversación."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # === Métodos para mensajes ===
    
    def add_message(self, conversation_id: int, role: str, content: str, 
                   metadata: str = None) -> int:
        """
        Añade un mensaje a una conversación.
        
        Args:
            conversation_id: ID de la conversación
            role: 'user' o 'assistant'
            content: Contenido del mensaje
            metadata: JSON string con metadata adicional
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO messages (conversation_id, role, content, metadata) VALUES (?, ?, ?, ?)',
            (conversation_id, role, content, metadata)
        )
        # Actualizar timestamp de la conversación
        cursor.execute(
            'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (conversation_id,)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los mensajes de una conversación."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
            (conversation_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # === Métodos para sesiones ===
    
    def create_session(self, user_id: int, token: str, expires_at: datetime) -> int:
        """Crea una nueva sesión."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user_id, token, expires_at.isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Valida un token de sesión."""
        cursor = self.conn.cursor()
        cursor.execute(
            '''SELECT s.*, u.username, u.email 
               FROM sessions s 
               JOIN users u ON s.user_id = u.id 
               WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP''',
            (token,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_session(self, token: str) -> bool:
        """Elimina una sesión (logout)."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Instancia global (singleton)
_db_instance = None

def get_db() -> Database:
    """Obtiene la instancia global de la base de datos."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
