import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket

from config.settings import settings

logger = logging.getLogger("orthobite.websocket")


class ConnectionManager:
    """
    Manages active WebSocket connections for users.
    Supports in-memory dispatch with Redis Pub/Sub fallback for horizontal clustering.
    """

    def __init__(self):

        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Attempts to connect to Redis; falls back gracefully to in-memory mode."""
        try:
            import redis
            if settings.REDIS_URL:
                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                r.ping()
                self.redis_client = r
                logger.info("WebSocket Redis Pub/Sub adapter connected successfully.")
        except Exception as e:
            self.redis_client = None
            logger.info(f"Running WebSocket manager in local in-memory mode ({e}).")

    async def connect(self, user_id: int, websocket: WebSocket):
        """Accepts and registers a new WebSocket connection for a given user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket (total user devices: {len(self.active_connections[user_id])}).")

    def disconnect(self, user_id: int, websocket: WebSocket):
        """Unregisters a closed WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    def is_user_online(self, user_id: int) -> bool:
        """Checks if a user has at least one active WebSocket connection."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_online_users(self) -> Set[int]:
        """Returns the set of all user IDs currently connected."""
        return set(self.active_connections.keys())

    async def send_personal_message(self, user_id: int, message: Dict[str, Any]):
        """Sends a JSON frame to all active devices of a specific user."""
        if user_id in self.active_connections:
            dead_sockets = set()
            for ws in list(self.active_connections[user_id]):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending message to user {user_id}: {e}")
                    dead_sockets.add(ws)

            for dead in dead_sockets:
                self.active_connections[user_id].discard(dead)

    async def broadcast_to_users(self, user_ids: Set[int], message: Dict[str, Any]):
        """Dispatches a message to a set of specific users."""
        for uid in user_ids:
            await self.send_personal_message(uid, message)

    async def broadcast(self, message: Dict[str, Any], exclude_user_id: Optional[int] = None):
        """Broadcasts message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            if exclude_user_id is not None and user_id == exclude_user_id:
                continue
            await self.send_personal_message(user_id, message)


manager = ConnectionManager()
