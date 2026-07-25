# StillLife — TikTok бот

Полностью автоматизированный бот для TikTok с AI-генерируемыми комментариями и DM.

## Требования

- Node.js 20+
- Python 3.11+
- GROQ API Key (бесплатно): https://console.groq.com/
- TikTok Session ID (от своего аккаунта)

## Установка

```bash
# Frontend
npm install --legacy-peer-deps

# Backend
pip install -r requirements.txt
```

## Запуск

### Backend
```bash
./start_backend.sh
# или
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
npm install
npm start
# или
npm run android
```

## Как использовать

1. **Вход в TikTok**
   - Откройте приложение
   - Выберите способ входа (браузер или вручную)
   - Браузер: автоматически найдёт Session ID
   - Вручную: получите Session ID из TikTok cookies

2. **Настройки**
   - Имя существа (для комментариев)
   - Язык (RU/EN)
   - Шрифт (обычный/искажённый)
   - Вкл/выкл комментарии и DM

3. **Цели**
   - Добавьте @username целевых пользователей
   - Начните отслеживание

4. **Управление**
   - Нажмите START для начала
   - Просмотрите лог активности
   - STOP для остановки

## Session ID как получить

1. Откройте https://www.tiktok.com в браузере
2. Залогиньтесь в аккаунт
3. F12 → Application → Cookies → www.tiktok.com
4. Найдите cookie с названием `sessionid`
5. Скопируйте значение
6. Вставьте в приложение

## API

### Endpoints

- `POST /api/connect` — вход в TikTok
- `POST /api/settings` — обновить настройки
- `POST /api/targets` — добавить целей
- `POST /api/control` — управление (start/stop)
- `WS /ws/logs` — WebSocket логи

## .env

```
GROQ_API_KEY=your_key_here
API_URL=http://localhost:8000
NODE_ENV=production
```

## Секреты GitHub (для Actions)

Если собираешь через GitHub Actions:
- `GROQ_API_KEY` — обязательно

Session ID вводишь в приложении, не в секреты.

## Troubleshooting

**"Session ID не найден"**
- Проверьте что залогинены в TikTok
- Убедитесь что браузер дал доступ к cookies
- Попробуйте ручной ввод

**"Backend не отвечает"**
- Проверьте что backend запущен на порту 8000
- Используйте правильный IP если на другой машине

**"Комментарии не постятся"**
- Проверьте Session ID валидный
- Убедитесь что GROQ_API_KEY установлен
- Проверьте лог ошибок в приложении

## Лицензия

MIT

---

**⚠️ Внимание:** Автоматические комментарии и DM могут нарушить ToS TikTok. Используйте на свой риск.
