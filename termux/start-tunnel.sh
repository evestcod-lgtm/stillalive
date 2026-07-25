#!/data/data/com.termux/files/usr/bin/bash
# Запускает Cloudflare quick tunnel под супервизором, который держит его
# живым всегда:
#   1) если процесс cloudflared упадёт целиком — перезапускает его;
#   2) если процесс жив, но реальный URL не отвечает на HTTP — тоже
#      перезапускает (просто "живой процесс" не значит "рабочий туннель").
# Каждый раз при новом/изменившемся адресе пушит его в GitHub
# (patches/current-server-url.txt). Приложение (App.js, resolveApiBase())
# само читает этот файл при каждом запуске — пересборка APK при смене
# адреса туннеля НЕ нужна.
#
# Держи эту сессию Termux открытой (или с wakelock) — quick-туннели
# cloudflare живут, пока жив сам процесс.

cd "$(dirname "$0")/.."
APPDIR="$(pwd)"
TUNNEL_LOG="$APPDIR/termux/tunnel.log"
LOG="$APPDIR/termux/watchdog.log"
LOCAL_URL="http://127.0.0.1:8000"

# ==== Настройки GitHub — поправь под себя ====
GITHUB_OWNER="evestcod-lgtm"
GITHUB_REPO="stillalive"
GITHUB_BRANCH="main"
GITHUB_FILE_PATH="patches/current-server-url.txt"
# Токен читаем из файла, чтобы не палить его в скрипте/логах/истории команд.
# Один раз выполни:  echo "ghp_твой_токен" > ~/.stillalive_github_token
GITHUB_TOKEN_FILE="$HOME/.stillalive_github_token"
# ================================================

termux-wake-lock 2>/dev/null
mkdir -p "$APPDIR/termux"

echo "=== start-tunnel.sh запущен $(date) ===" >> "$LOG"

# Убиваем возможные старые супервизоры/cloudflared, чтобы не плодить дубликаты
pkill -f "STILLALIVE_TUNNEL_WATCHDOG" 2>/dev/null
pkill -f cloudflared 2>/dev/null
sleep 1

if [ ! -f "$GITHUB_TOKEN_FILE" ]; then
  echo "⚠️  $GITHUB_TOKEN_FILE не найден — автопуш URL в GitHub работать не будет."
  echo "    Создай personal access token (Settings → Developer settings → Tokens,"
  echo "    права: Contents: Read and write на репозиторий $GITHUB_OWNER/$GITHUB_REPO)"
  echo "    и сохрани: echo 'ghp_...' > $GITHUB_TOKEN_FILE"
fi

push_url_to_github() {
  local new_url="$1"
  if [ ! -f "$GITHUB_TOKEN_FILE" ]; then
    echo "$(date) пропуск пуша — нет токена" >> "$LOG"
    return
  fi
  local token
  token=$(cat "$GITHUB_TOKEN_FILE" | tr -d '[:space:]')
  local api="https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/contents/$GITHUB_FILE_PATH"

  # Узнаём sha текущего файла (нужен GitHub API, чтобы обновить, а не создать конфликт)
  local sha
  sha=$(curl -s -H "Authorization: token $token" -H "Accept: application/vnd.github+json" "$api?ref=$GITHUB_BRANCH" \
        | grep -oE '"sha": ?"[a-f0-9]+"' | head -1 | grep -oE '[a-f0-9]{20,}')

  local content_b64
  content_b64=$(printf '%s' "$new_url" | base64 -w0)

  local payload
  if [ -n "$sha" ]; then
    payload=$(printf '{"message":"auto: update tunnel url","content":"%s","branch":"%s","sha":"%s"}' \
              "$content_b64" "$GITHUB_BRANCH" "$sha")
  else
    payload=$(printf '{"message":"auto: create tunnel url file","content":"%s","branch":"%s"}' \
              "$content_b64" "$GITHUB_BRANCH")
  fi

  local http_code
  http_code=$(curl -s -o /tmp/gh_push_response.json -w "%{http_code}" \
    -X PUT -H "Authorization: token $token" -H "Accept: application/vnd.github+json" \
    -d "$payload" "$api")

  if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "$(date) ✅ URL запушен в GitHub: $new_url" >> "$LOG"
  else
    echo "$(date) ❌ Пуш в GitHub не удался (HTTP $http_code): $(cat /tmp/gh_push_response.json)" >> "$LOG"
  fi
}

# Ждёт до 40 секунд появления URL в логе cloudflared
catch_url() {
  local url=""
  for i in $(seq 1 40); do
    url=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$TUNNEL_LOG" | tail -1)
    if [ -n "$url" ]; then
      echo "$url"
      return 0
    fi
    sleep 1
  done
  echo ""
  return 1
}

# Проверяет, что туннель реально отвечает. Раньше здесь curl шёл через сам
# внешний адрес (телефон стучался сам к себе через интернет+Cloudflare) —
# любая мимолётная заминка мобильной сети засчитывалась как "туннель мёртв",
# из-за чего cloudflared убивался и пересоздавался каждую минуту, а
# Cloudflare в итоге начинал троттлить такие частые пересоздания.
# Теперь: 1) сначала быстро проверяем, что локальный сервер вообще жив
#            (127.0.0.1, без интернета, доля секунды) — если он не отвечает,
#            это не вина туннеля, ждём и не убиваем cloudflared;
#         2) внешний адрес проверяем только раз в несколько циклов и не
#            убиваем при единичном сбое — только если внешняя проверка
#            не проходит несколько раз ПОДРЯД (реальный признак, что
#            именно туннель, а не сеть, отвалился).
EXTERNAL_FAIL_STREAK=0
EXTERNAL_FAIL_LIMIT=3   # убиваем только после 3 неудач подряд (не с первой)

local_server_is_up() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/docs")
  [ "$code" != "000" ] && [ "$code" -lt 500 ] 2>/dev/null
}

tunnel_is_healthy() {
  local url="$1"
  [ -z "$url" ] && return 1

  if ! local_server_is_up; then
    # Локальный сервер сам не отвечает — это не проблема туннеля,
    # не наказываем cloudflared за то, что не его вина.
    echo "$(date) ℹ️ Локальный сервер (127.0.0.1:8000) не отвечает — жду, туннель не трогаю" >> "$LOG"
    return 0
  fi

  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url/docs")
  if [ "$code" != "000" ] && [ "$code" -lt 500 ] 2>/dev/null; then
    EXTERNAL_FAIL_STREAK=0
    return 0
  fi

  EXTERNAL_FAIL_STREAK=$((EXTERNAL_FAIL_STREAK + 1))
  echo "$(date) ⚠️ Внешняя проверка не прошла ($EXTERNAL_FAIL_STREAK/$EXTERNAL_FAIL_LIMIT)" >> "$LOG"
  [ "$EXTERNAL_FAIL_STREAK" -lt "$EXTERNAL_FAIL_LIMIT" ]
}

LAST_URL=""

while true; do
  echo "$(date) 🚀 Запускаю cloudflared..." >> "$LOG"
  : > "$TUNNEL_LOG"

  # Метка процесса, чтобы pkill выше мог найти именно наши запуски
  STILLALIVE_TUNNEL_WATCHDOG=1 nohup cloudflared tunnel --url "$LOCAL_URL" >> "$TUNNEL_LOG" 2>&1 &
  CF_PID=$!
  echo "$CF_PID" > "$APPDIR/termux/tunnel.pid"

  NEW_URL=$(catch_url)

  if [ -z "$NEW_URL" ]; then
    echo "$(date) ❌ Не удалось поймать URL за 40с, убиваю и перезапускаю" >> "$LOG"
    kill "$CF_PID" 2>/dev/null
    sleep 3
    continue
  fi

  if [ "$NEW_URL" != "$LAST_URL" ]; then
    echo "$(date) 🔗 Новый адрес: $NEW_URL" >> "$LOG"
    push_url_to_github "$NEW_URL"
    LAST_URL="$NEW_URL"
  fi

  EXTERNAL_FAIL_STREAK=0

  # Пока процесс жив — раз в 45с проверяем реальную доступность
  while kill -0 "$CF_PID" 2>/dev/null; do
    sleep 45
    if ! tunnel_is_healthy "$LAST_URL"; then
      echo "$(date) ⚠️ Туннель не отвечает ($EXTERNAL_FAIL_LIMIT раз подряд), перезапускаю" >> "$LOG"
      kill "$CF_PID" 2>/dev/null
      break
    fi
  done

  echo "$(date) 💀 cloudflared завершился, перезапуск через 3с" >> "$LOG"
  sleep 3
done
