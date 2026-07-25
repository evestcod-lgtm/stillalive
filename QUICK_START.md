# StillLife — Быстрый Старт

## Шаг 1: Получить API ключ (5 мин)

1. Откройте https://console.groq.com/
2. Нажмите "Sign Up" или "Sign In"
3. Перейдите в "API Keys"
4. Скопируйте ключ
5. Сохраните где-нибудь

## Шаг 2: Получить Session ID (5 мин)

1. Откройте https://www.tiktok.com в браузере
2. Залогиньтесь своим аккаунтом
3. Нажмите F12 (откроется DevTools)
4. Нажмите вкладку "Application"
5. Найдите "Cookies" → "www.tiktok.com"
6. Ищите cookie с названием `sessionid`
7. Скопируйте значение (длинная строка)
8. Сохраните

## Шаг 3: GitHub Actions (если собираешь в облаке)

1. Откройте ваш GitHub репо
2. Settings → Secrets and variables → Actions
3. Нажмите "New repository secret"
4. Name: `GROQ_API_KEY`
5. Value: [вставьте ключ из шага 1]
6. Add secret

## Шаг 4: Собрать APK

### Вариант A: GitHub Actions (автоматически)
- Просто `git push` на main
- Ждите 30 минут
- Скачайте APK из Actions → Artifacts

### Вариант B: Локально на Termux
```bash
pkg install nodejs python git
git clone https://github.com/вы/stilllife.git
cd stilllife
npm install --legacy-peer-deps
pip install -r requirements.txt
expo build --platform android --local
```

## Шаг 5: Запустить приложение

1. Установите APK на телефон
2. Откройте приложение
3. Выберите способ входа (браузер или вручную)
4. Вставьте Session ID из шага 2
5. Настройте параметры (язык, имя и т.д.)
6. Добавьте целевые @username
7. Нажмите START

## Готово! 

Бот будет автоматически:
- Постить комментарии
- Отправлять DM
- Отслеживать целевых пользователей

---

Любые вопросы? Проверьте README.md
