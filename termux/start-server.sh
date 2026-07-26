#!/data/data/com.termux/files/usr/bin/bash
# Запускает бэкенд (FastAPI/uvicorn) в фоне и держит телефон разбуженным.
# Логи пишет в server.log в этой же папке.
#
# После запуска можно закрыть эту сессию Termux — сервер останется жить
# благодаря nohup, но термуксу всё равно нужно быть в живых (не выгружен
# системой) — см. "Отключить оптимизацию батареи" в TERMUX_BACKEND.md.

cd "$(dirname "$0")/.."   # переходим в корень проекта (на уровень выше termux/)
APPDIR="$(pwd)"

termux-wake-lock 2>/dev/null

echo "🐍 Запуск StillAlive backend..."
echo "Рабочая папка: $APPDIR"

if [ ! -f ".env" ]; then
  echo "⚠️  Файл .env не найден. Создай его: echo 'GROQ_API_KEY=...' > .env"
fi

# Запускаем именно из src/ — server.py импортирует свои модули как
# "from services.groq_service import ..." (относительно src/, а не
# относительно корня репозитория), поэтому "python -m uvicorn src.server:app"
# из корня падает с ModuleNotFoundError: No module named 'services'.
cd "$APPDIR/src"
nohup python -m uvicorn server:app --host 0.0.0.0 --port 8000 > "$APPDIR/server.log" 2>&1 &
SERVER_PID=$!
cd "$APPDIR"
echo "$SERVER_PID" > "$APPDIR/termux/server.pid"

echo "✅ Сервер запущен (PID $SERVER_PID). Логи: $APPDIR/server.log"
echo ""
echo "Дальше открой НОВУЮ сессию Termux (свайп слева → New session)"
echo "и в ней выполни: ./termux/start-tunnel.sh"
