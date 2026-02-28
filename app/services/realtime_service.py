from datetime import datetime

from app import socketio


def publish_platform_update(scope: str, action: str, actor_role: str = "system"):
    socketio.emit(
        "platform_update",
        {
            "scope": scope,
            "action": action,
            "actor_role": actor_role,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
