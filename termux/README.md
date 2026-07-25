# Бэкенд в Termux + автообновляемый Cloudflare Tunnel

Схема как в SecureChat: сервер и туннель работают в Termux на телефоне.
Watchdog следит за туннелем и при смене адреса пушит новый URL в открытый
файл в GitHub (`patches/current-server-url.txt`). Само приложение при
каждом запуске само читает этот файл и подключается к актуальному
адресу — **пересборка APK при смене адреса туннеля не нужна вообще**.
Пересобирать нужно только когда меняется сам код приложения.

## 1. Установка (один раз)

Termux ставь **из F-Droid**, не Google Play.

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git cloudflared curl
git clone https://github.com/evestcod-lgtm/stillalive
cd stillalive
pip install --upgrade pip
pip install -r requirements.txt
```

Если что-то не соберётся (lxml/aiohttp/pydantic-core) — см. TERMUX_BACKEND.md,
там разобраны типичные ошибки под свежий Python в Termux.

## 2. .env для бэкенда

```bash
echo "GROQ_API_KEY=твой_ключ_groq" > .env
```

## 3. GitHub-токен для автопуша адреса

Нужен Personal Access Token с правом **Contents: Read and write** на репозиторий
`evestcod-lgtm/stillalive` — только на запись файла с адресом, больше ничего не требуется.

GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
→ New token → Repository access: только `stillalive` → Permissions → Contents: Read and write.

Сохрани токен на телефоне (не в самом скрипте):

```bash
echo "ghp_твой_токен_сюда" > ~/.stillalive_github_token
```

## 4. Права на выполнение

```bash
chmod +x termux/start-server.sh termux/start-tunnel.sh
```

## 5. Запуск

Сессия 1 (сервер):

```bash
./termux/start-server.sh
```

Сессия 2 (свайп слева → New session), туннель + вотчдог:

```bash
./termux/start-tunnel.sh
```

Держи вторую сессию открытой (или включи Termux wakelock + отключи оптимизацию
батареи для Termux в настройках Android — иначе система прибьёт процесс в фоне).

## 6. Как это работает

- `start-tunnel.sh` поднимает `cloudflared tunnel --url http://127.0.0.1:8000`
- ловит адрес `https://xxxx.trycloudflare.com` из его лога
- каждые 20 секунд реально проверяет через `curl`, что адрес отвечает —
  не просто "процесс жив", а именно что туннель рабочий
- если процесс упал ИЛИ перестал отвечать — убивает и перезапускает
- при любом новом/изменившемся адресе пушит его в
  `patches/current-server-url.txt` в репозитории (создаёт файл, если его
  ещё нет, иначе обновляет)
- **приложение само** при каждом запуске (см. `resolveApiBase()` в App.js)
  читает этот файл через `raw.githubusercontent.com` и подключается
  к свежему адресу — без пересборки

Логи: `termux/watchdog.log` (решения супервизора) и `termux/tunnel.log`
(сырой вывод cloudflared).

## 7. Когда всё же нужна пересборка APK

Только если поменялся сам код приложения (App.js, зависимости и т.п.) —
тогда как обычно: Actions → Build Android APK → Run workflow, скачать
из Artifacts, установить.

Смену адреса туннеля пересборка больше не касается — просто держи Termux
(сервер + туннель) запущенным, когда пользуешься приложением.

## Частые проблемы

- **"network request failed" / "Бэкенд не настроен"** — бэкенд или туннель
  не запущены в Termux в этот момент, либо у телефона нет интернета
  в момент запуска приложения (тогда оно не смогло прочитать свежий
  адрес и осталось на зашитом в сборку фолбэке). Проверь, что обе
  сессии Termux активны.
- **watchdog.log пишет "❌ Пуш в GitHub не удался (HTTP 401)"** — токен
  неверный/просрочен, пересоздай и перезапиши `~/.stillalive_github_token`.
- **HTTP 404 при пуше в первый раз** — нормально, если файла
  `current-server-url.txt` ещё не было в репозитории, скрипт создаёт его сам.
- **Адрес меняется каждые пару часов сам по себе** — нормальное поведение
  cloudflare quick tunnel (не именованного). Приложению это уже не мешает —
  оно каждый раз перечитывает адрес заново. Если всё же хочешь стабильный
  постоянный адрес — нужен бесплатный аккаунт Cloudflare и
  `cloudflared tunnel login` (именованный туннель) — скажи, распишу отдельно.
