import aiosqlite
import os

DB_PATH = "data/database.sqlite"

async def init_db():
    """Инициализация базы данных."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_duty (
                user_id INTEGER PRIMARY KEY,
                total_time INTEGER DEFAULT 0,
                current_status TEXT DEFAULT 'offline',
                session_start REAL DEFAULT 0,
                afk_start REAL DEFAULT 0,
                session_afk_time REAL DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    """Получить данные пользователя, если нет - создать."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_duty WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO user_duty (user_id) VALUES (?)", (user_id,))
                await db.commit()
                return {"user_id": user_id, "total_time": 0, "current_status": "offline", "session_start": 0, "afk_start": 0, "session_afk_time": 0}
            return dict(row)

async def update_user(user_id: int, **kwargs):
    """Обновить поля пользователя."""
    if not kwargs: return
    
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(user_id)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE user_duty SET {set_clause} WHERE user_id = ?", values)
        await db.commit()

async def get_top_duty(limit: int = 10):
    """Получить топ пользователей по времени в войсках."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Сортируем только по сохраненному total_time
        # (для идеальной точности нужно было бы прибавлять текущую сессию, но для простоты лидерборда достаточно сохраненного времени)
        async with db.execute("SELECT user_id, total_time FROM user_duty WHERE total_time > 0 ORDER BY total_time DESC LIMIT ?", (limit,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]
