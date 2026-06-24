# 👑 MAJESTIK Bot

Discord бот для семьи **MAJESTIK**. Построен на discord.py 2.x.

## ⚡ Возможности

### 👋 Приветствия
- Красивый embed в канале при входе участника
- Приветствие в ЛС с инструкциями
- Кнопки: «Что дальше?», «Подать заявку», «Связаться с руководством», «Представиться»
- Сообщение о выходе участника

### 🎫 Тикеты
- Панель тикетов с кнопкой создания
- Выбор категории (Поддержка, Жалоба, Вопрос, Предложение, Другое)
- Приватные каналы с ролью поддержки
- Закрытие с подтверждением
- Логирование и экспорт истории

### ⚙️ Полная конфигурация через команды
- `/config show` — просмотр всех настроек
- `/config family-name` — название семьи
- `/config color` — цвет embed'ов
- `/config welcome-channel` — канал приветствий
- `/config dm-toggle` — вкл/выкл ЛС
- `/config ticket-support-role` — роль поддержки
- И ещё 20+ команд настройки!

## 🚀 Установка

### 1. Клонировать / скачать проект

### 2. Установить зависимости
```bash
pip install -r requirements.txt
```

### 3. Настроить токен
Скопируйте `.env.example` в `.env` и вставьте токен бота:
```
DISCORD_TOKEN=your_bot_token_here
```

### 4. Настроить Discord Developer Portal
- Перейдите в [Discord Developer Portal](https://discord.com/developers/applications)
- Выберите вашего бота → **Bot** → включите:
  - ✅ **Server Members Intent**
  - ✅ **Message Content Intent**
- **OAuth2** → URL Generator:
  - Scopes: `bot`, `applications.commands`
  - Permissions: `Administrator` (или отдельные: Manage Channels, Send Messages, Embed Links, Read Message History, Manage Messages)

### 5. Запустить
```bash
python bot.py
```

## 🔧 Первоначальная настройка на сервере

После добавления бота на сервер, используйте команды:
```
/config welcome-channel #приветствия
/config farewell-channel #прощания
/config ticket-log-channel #логи-тикетов
/config ticket-support-role @Поддержка
/config admin-role @Администрация
/config apply-channel #заявки
/config introduce-channel #знакомства
/config dm-rules-channel #правила
/config dm-apply-channel #заявки
```

Затем отправьте панель тикетов:
```
/ticket-panel
```

Проверить все настройки:
```
/config show
```

## 📁 Структура

```
├── bot.py               # Главный файл
├── cogs/
│   ├── welcome.py       # Приветствия
│   ├── tickets.py       # Тикеты
│   └── config_cog.py    # Настройки
├── config/
│   ├── config.py        # Менеджер конфигурации
│   └── settings.json    # Настройки
├── utils/
│   └── embeds.py        # Утилиты embed'ов
├── requirements.txt
└── .env                 # Токен (не коммитить!)
```
