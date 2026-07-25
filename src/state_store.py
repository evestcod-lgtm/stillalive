"""
Персистентное хранение состояния бота (bot_state) на диске.

Раньше bot_state жил только в оперативной памяти процесса — при
перезапуске сервера (падение Termux, перезагрузка телефона, обновление
кода) всё обнулялось: targets, running, история переписки, session_id
для TikTok — всё терялось, и охоту приходилось запускать заново вручную
из приложения.

Теперь состояние сохраняется в JSON-файл при каждом изменении и
подгружается при старте сервера. Если на момент сохранения running
было True — сервер сам возобновит цикл охоты при следующем запуске,
без участия приложения.

Файл специально лежит вне репозитория (см. .gitignore) — там же хранится
session_id для TikTok, а это по сути пароль от аккаунта.
"""
import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_state.json")

# Поля, которые реально стоит переживать между перезапусками.
# conversation_history и who_count намеренно НЕ включены целиком без
# ограничения — история может расти бесконечно; сохраняем последние
# N сообщений на цель, чтобы файл не разрастался и не тормозил запись.
MAX_HISTORY_PER_TARGET = 20


def load_state() -> Dict[str, Any]:
    """Загружает сохранённое состояние с диска. Если файла нет или он
    повреждён — возвращает пустой dict (сервер стартует с чистого листа,
    как раньше)."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"✓ Состояние бота восстановлено из {STATE_FILE}")
        return data
    except Exception as e:
        logger.error(f"⚠ Не удалось прочитать сохранённое состояние ({e}), стартую с чистого листа")
        return {}


def save_state(bot_state: Dict[str, Any], session_id: str = None) -> None:
    """Сохраняет текущее состояние на диск. Вызывается при каждом
    значимом изменении (подключение, старт/стоп охоты, смена целей
    и настроек) — не в горячем цикле на каждое сообщение, чтобы не
    дёргать диск слишком часто."""
    try:
        trimmed_history = {
            target: messages[-MAX_HISTORY_PER_TARGET:]
            for target, messages in bot_state.get("conversation_history", {}).items()
        }

        payload = {
            "authenticated": bot_state.get("authenticated", False),
            "running": bot_state.get("running", False),
            "creature_name": bot_state.get("creature_name", "Существо"),
            "language": bot_state.get("language", "ru"),
            "font_mode": bot_state.get("font_mode", "normal"),
            "targets": bot_state.get("targets", []),
            "target_styles": bot_state.get("target_styles", {}),
            "who_count": bot_state.get("who_count", {}),
            "conversation_history": trimmed_history,
            "comment_mode": bot_state.get("comment_mode", True),
            "dm_mode": bot_state.get("dm_mode", True),
            "session_id": session_id,
        }

        tmp_path = STATE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STATE_FILE)  # атомарная замена — без риска битого файла при сбое посреди записи
    except Exception as e:
        logger.error(f"⚠ Не удалось сохранить состояние: {e}")


def clear_state() -> None:
    """Удаляет сохранённое состояние (например, при явном выходе/сбросе)."""
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except Exception as e:
        logger.error(f"⚠ Не удалось удалить сохранённое состояние: {e}")

