"""
Persistent per-user chat history: conversations and messages.
Uses PostgreSQL (DATABASE_URL). Qdrant remains the vector DB for RAG.
"""
import os
import logging
import json
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from contextlib import contextmanager

try:
	from dotenv import load_dotenv
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except Exception:
	pass

logger = logging.getLogger("db_conversations")

try:
	import psycopg2
	from psycopg2.extras import RealDictCursor
except ImportError:
	psycopg2 = None
	RealDictCursor = None


def _get_database_url() -> str:
	url = os.getenv("DATABASE_URL", "").strip()
	if not url:
		raise RuntimeError(
			"DATABASE_URL is not set. Set it to your PostgreSQL connection string, e.g. "
			"postgresql://user:password@host:5432/dbname"
		)
	return url


@contextmanager
def _get_conn():
	if psycopg2 is None:
		raise RuntimeError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
	conn = psycopg2.connect(_get_database_url())
	try:
		yield conn
		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


def _ensure_tables(conn) -> None:
	with conn.cursor() as cur:
		cur.execute("""
			CREATE TABLE IF NOT EXISTS conversations (
				id TEXT PRIMARY KEY,
				user_id TEXT NOT NULL,
				title TEXT NOT NULL DEFAULT 'New Chat',
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			);
		""")
		cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);")
		cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC);")
		cur.execute("""
			CREATE TABLE IF NOT EXISTS messages (
				id TEXT PRIMARY KEY,
				conversation_id TEXT NOT NULL,
				role TEXT NOT NULL,
				content TEXT NOT NULL,
				sources_json TEXT,
				created_at TEXT NOT NULL,
				FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
			);
		""")
		cur.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);")


def _now() -> str:
	return datetime.utcnow().isoformat() + "Z"


def create_conversation(user_id: str, title: str = "New Chat") -> dict:
	cid = f"conv_{uuid4().hex[:12]}"
	now = _now()
	with _get_conn() as conn:
		_ensure_tables(conn)
		with conn.cursor() as cur:
			cur.execute(
				"INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
				(cid, user_id, title, now, now),
			)
	logger.info("Created conversation %s for user %s", cid, user_id)
	return {"id": cid, "user_id": user_id, "title": title, "created_at": now, "updated_at": now}


def list_conversations(user_id: str, limit: int = 50) -> List[dict]:
	with _get_conn() as conn:
		_ensure_tables(conn)
		with conn.cursor(cursor_factory=RealDictCursor) as cur:
			cur.execute(
				"SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
				(user_id, limit),
			)
			rows = cur.fetchall()
	return [dict(r) for r in rows]


def get_conversation(conversation_id: str, user_id: str) -> Optional[dict]:
	with _get_conn() as conn:
		_ensure_tables(conn)
		with conn.cursor(cursor_factory=RealDictCursor) as cur:
			cur.execute(
				"SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = %s AND user_id = %s",
				(conversation_id, user_id),
			)
			row = cur.fetchone()
	return dict(row) if row else None


def get_messages(conversation_id: str, user_id: str, limit: int = 200) -> List[dict]:
	if not get_conversation(conversation_id, user_id):
		return []
	with _get_conn() as conn:
		with conn.cursor(cursor_factory=RealDictCursor) as cur:
			cur.execute(
				"SELECT id, conversation_id, role, content, sources_json, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC LIMIT %s",
				(conversation_id, limit),
			)
			rows = cur.fetchall()
	out = []
	for r in rows:
		d = dict(r)
		if d.get("sources_json"):
			try:
				d["sources_detail"] = json.loads(d["sources_json"])
			except Exception:
				d["sources_detail"] = None
		out.append(d)
	return out


def add_message(conversation_id: str, user_id: str, role: str, content: str, sources_json: Optional[str] = None) -> dict:
	if not get_conversation(conversation_id, user_id):
		raise ValueError("Conversation not found or access denied")
	mid = f"msg_{uuid4().hex[:12]}"
	now = _now()
	with _get_conn() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"INSERT INTO messages (id, conversation_id, role, content, sources_json, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
				(mid, conversation_id, role, content, sources_json or None, now),
			)
			cur.execute("UPDATE conversations SET updated_at = %s WHERE id = %s", (now, conversation_id))
	return {"id": mid, "conversation_id": conversation_id, "role": role, "content": content, "created_at": now}


def update_conversation_title(conversation_id: str, user_id: str, title: str) -> None:
	with _get_conn() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"UPDATE conversations SET title = %s, updated_at = %s WHERE id = %s AND user_id = %s",
				(title, _now(), conversation_id, user_id),
			)


def delete_conversation(conversation_id: str, user_id: str) -> bool:
	with _get_conn() as conn:
		with conn.cursor() as cur:
			cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
			cur.execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
			deleted = cur.rowcount > 0
	if deleted:
		logger.info("Deleted conversation %s for user %s", conversation_id, user_id)
	return deleted


def title_from_first_query(query: str, max_len: int = 60) -> str:
	"""Generate a conversation title from the first user query."""
	s = (query or "").strip()
	if not s:
		return "New Chat"
	if len(s) <= max_len:
		return s
	return s[: max_len - 3].rstrip() + "..."


def get_active_users_counts() -> dict:
	"""
	Return active user counts from conversations:
	- active_users_today: distinct user_id with a conversation updated today (UTC)
	- active_users_7d: distinct user_id with a conversation updated in last 7 days (UTC)
	"""
	today = datetime.utcnow().date().isoformat()
	with _get_conn() as conn:
		_ensure_tables(conn)
		with conn.cursor() as cur:
			# created_at/updated_at are stored as ISO strings; prefix match by YYYY-MM-DD works for UTC date bucket
			cur.execute(
				"SELECT COUNT(DISTINCT user_id) FROM conversations WHERE updated_at LIKE %s",
				(today + "%",),
			)
			today_count = int((cur.fetchone() or [0])[0] or 0)
			cur.execute(
				"SELECT COUNT(DISTINCT user_id) FROM conversations WHERE updated_at >= %s",
				((datetime.utcnow().replace(microsecond=0) - timedelta(days=7)).isoformat() + "Z",),
			)
			week_count = int((cur.fetchone() or [0])[0] or 0)
	return {"active_users_today": today_count, "active_users_7d": week_count}
