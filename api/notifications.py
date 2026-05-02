"""Ntfy push notification utilities"""
import asyncio
import logging
import requests
from database import get_online_players, is_worldserver_online

logger = logging.getLogger(__name__)

NTFY_TOPIC = "https://ntfy.sh/verticix-wow-server"

# Track state
_online_players: set[str] = set()
_server_online: bool | None = None
_poll_task: asyncio.Task | None = None


def send_notification(message: str):
    """Send a notification to the ntfy topic"""
    try:
        requests.post(NTFY_TOPIC, data=message.encode(encoding="utf-8"), timeout=10)
    except Exception as e:
        logger.error(f"Failed to send ntfy notification: {e}")


def _check_server_status():
    """Check if the worldserver status changed and notify"""
    global _server_online
    try:
        online = is_worldserver_online()
    except Exception as e:
        logger.error(f"Failed to check server status: {e}")
        return

    if _server_online is None:
        _server_online = online
        return

    if online and not _server_online:
        send_notification("🟢 WoW server is online!")
    elif not online and _server_online:
        send_notification("🔴 WoW server has gone offline!")

    _server_online = online


def _check_player_changes():
    """Poll online players and detect joins/leaves"""
    global _online_players
    try:
        players = get_online_players()
        current = {p["name"] for p in players}
    except Exception as e:
        logger.error(f"Failed to poll online players: {e}")
        return

    joined = current - _online_players
    left = _online_players - current

    for name in joined:
        send_notification(f"📥 {name} has joined the server!")

    for name in left:
        send_notification(f"📤 {name} has left the server!")

    _online_players = current


async def start_polling(interval: int = 30):
    """Background task that polls for player and server status changes"""
    global _poll_task, _online_players, _server_online

    # Seed initial state without sending notifications
    try:
        players = get_online_players()
        _online_players = {p["name"] for p in players}
    except Exception:
        pass

    try:
        _server_online = is_worldserver_online()
    except Exception:
        pass

    async def _poll():
        while True:
            await asyncio.sleep(interval)
            _check_server_status()
            _check_player_changes()

    _poll_task = asyncio.create_task(_poll())


def stop_polling():
    """Cancel the background polling task"""
    global _poll_task
    if _poll_task:
        _poll_task.cancel()
        _poll_task = None
