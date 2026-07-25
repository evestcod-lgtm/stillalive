# Бэкенд в Termux + автообновляемый Cloudflare Tunnel

Схема как в SecureChat: сервер и туннель работают в Termux на телефоне,
watchdog следит за туннелем и при смене адреса сам пушит новый URL
в GitHub — тебе останется только нажать пересборку APK с этим адресом.

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

Если что-то из `pymorphy2`/`lxml` не собралось:

```bash
pkg install -y clang libxml2 libxslt
```

## 2. .env для бэкенда

```bash
echo "GROQ_API_KEY=твой_ключ_groq" > .env
```

## 3. GitHub-токен для автопуша адреса

Нужен Personal Access Token с правом **Contents: Read and write** на репозиторий
`evestcod-lgtm/stillalive`:

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
- при любом новом/изменившемся адресе — пушит его в
  `patches/current-server-url.txt` в репозитории `evestcod-lgtm/stillalive`
  через GitHub API (создаёт файл, если его ещё нет, иначе обновляет)

Логи: `termux/watchdog.log` (решения супервизора) и `termux/tunnel.log`
(сырой вывод cloudflared).

## 7. Пересборка APK с новым адресом

1. Открой `patches/current-server-url.txt` в репозитории — там актуальный URL
2. Repo → Settings → Secrets and variables → Actions → `API_URL` → Update → вставь адрес
3. Actions → Build Android APK → Run workflow

Пересборка ручная/по кнопке, как и хотел — без автообновления самого APK на лету.
Если адрес поменялся, а ты забыл пересобрать — приложение продолжит стучаться
на старый (уже мёртвый) адрес, поэтому проверяй `current-server-url.txt` перед
использованием, если давно не запускал бэкенд.

## Частые проблемы

- **"network request failed" сразу после сборки** — бэкенд/туннель просто не запущены
  в Termux в этот момент. Само приложение никогда не поднимет сервер за тебя.
- **watchdog.log пишет "❌ Пуш в GitHub не удался (HTTP 401)"** — токен неверный/просрочен,
  пересоздай и перезапиши `~/.stillalive_github_token`.
- **HTTP 404 при пуше в первый раз** — нормально, если файла `current-server-url.txt`
  ещё не было в репозитории, скрипт создаёт его сам.
- **Адрес меняется каждые пару часов сам по себе** — это нормальное поведение
  cloudflare quick tunnel (не именованного). Если хочешь стабильный постоянный
  адрес — нужен бесплатный аккаунт Cloudflare и `cloudflared tunnel login`
  (именованный туннель) — скажи, распишу отдельно.

