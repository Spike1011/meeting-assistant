# Meeting Assistant

Утилита для записи, транскрибации и суммаризации встреч (созвонов) на macOS с поддержкой двух движков записи: нативного (ScreenCaptureKit) и legacy (sounddevice).

## 🎯 Возможности

- **Интерактивная настройка**: Автоматический мастер выбора аудиоустройств при первом запуске
- **Два режима записи аудио**:
  - **Legacy Mode**: Захват через Aggregate Device (BlackHole + Mic) с помощью sounddevice
  - **Native Mode**: Нативный захват macOS через ScreenCaptureKit и AVFoundation (требует macOS 13.0+)
- **Транскрибация**: Deepgram Nova-2 с поддержкой русского языка
- **Диаризация**: Автоматическое разделение спикеров с временными метками `[MM:SS] Speaker N:`
- **Суммаризация**: Генерация итогов встречи на базе любого из провайдеров: **DeepSeek (V3/R1)**, **ChatGPT (4o/4o-mini)** или **Google Gemini (2.0 Flash)**.
- **Гибкая настройка LLM**: Выбор провайдера и модели через системный конфиг или мастер настройки.
- **Retry Logic**: Автоматические повторные попытки с экспоненциальной задержкой при сбоях API
- **Graceful Shutdown**: Корректная остановка записи по Ctrl+C
- **Два формата вывода**: 
  - `transcript_YYYYMMDD_HHMMSS.md` - полный лог с временными метками
  - `summary_YYYYMMDD_HHMMSS.md` - краткие итоги с датой встречи, темами, решениями и задачами

## 📋 Требования

- **macOS** (проверено на Apple Silicon)
- **Python 3.12+**
- **Для Legacy Mode**: BlackHole или аналогичный аудио-драйвер
- **Для Native Mode**: macOS 13.0+ (Ventura) с разрешениями Screen Recording и Microphone
- **API Ключи (в файле .env)**:
  - [Deepgram API Key](https://console.deepgram.com/) (**Обязательно**)
  - [Gemini API Key](https://aistudio.google.com/) (Опционально)
  - [DeepSeek API Key](https://platform.deepseek.com/) (Опционально)
  - [OpenAI API Key](https://platform.openai.com/) (Опционально)

## 🚀 Быстрый старт (через Makefile)

Если у вас установлен `make`, вы можете настроить всё одной командой:

```bash
# 1. Установка окружения и зависимостей
make install

# 2. Настройка API ключей
# Отредактируйте созданный файл .env и добавьте ваши ключи:
# DEEPGRAM_API_KEY=...
# DEEPSEEK_API_KEY=...
# OPENAI_API_KEY=...
# GEMINI_API_KEY=...

# 3. Запуск записи
make run
```

### Другие команды Makefile:
- `make setup` — запуск интерактивной настройки аудио (флаг --setup).
- `make api` — запуск Web API сервера.
- `make clean` — полная очистка виртуального окружения и временных файлов.

---

## 🚀 Ручная установка (если нет make)

### 1. Клонируйте репозиторий

> **⚠️ Важно**: В целях безопасности API ключи теперь считываются **только** из файла `.env`. Файл `config.json` используется только для нечувствительных настроек.

## ⚙️ Настройка и первый запуск

### Автоматическая настройка

Просто запустите программу:
```bash
python main.py
```

Если программа запускается впервые или устройство записи не выбрано, запустится интерактивный мастер:

1. **Выбор аудиоустройства**:
```text
Select device number (1-7) [default: 1]:
[+] Selected: Микрофон EarPods
```

2. **Выбор модели ИИ для суммаризации**:
```text
Available Models:
    1. deepseek-chat (deepseek) - DeepSeek V3 (Recommended)
    2. deepseek-reasoner (deepseek) - DeepSeek R1
    3. gpt-4o (chatgpt) - ChatGPT 4o
    4. gemini-2.0-flash (gemini) - Gemini 2.0 Flash
    ...
Select model number (1-6) [default: 1]:
```

### Смена устройства

Если вы хотите сменить аудиоустройство или перенастроить программу, используйте флаг `--setup`:
```bash
python main.py --setup
```

## 📖 Использование

### CLI: Запись новой встречи

Запустите скрипт для начала записи. Нажмите **Ctrl+C** для остановки.

```bash
python main.py
```

Пример вывода:
```text
[*] Meeting Assistant initialized.
------------------------------------------------------------
[+] Configuration loaded
    Recording method: dual
[+] API keys validated
[+] Recorder initialized: multi
[+] Transcription processor initialized
[+] Summarizer initialized
[*] Session directory: output/2026_02_06 14:00
------------------------------------------------------------
[>] RECORDING... Press Ctrl+C to stop
```

### CLI: Обработка существующего файла

```bash
python main.py -f /путь/к/файлу.wav
```

### Web API (Swagger UI)

Запустите сервер:
```bash
python api.py
```
Откройте в браузере: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Эндпоинты Web API

- **`POST /process-audio`**  
  Загружает аудиофайл, делает транскрибацию через Deepgram и сразу же запускает саммаризацию с использованием LLM‑провайдера по умолчанию из `config.json`.  
  Дополнительно:
  - если передать параметр `download=true`, эндпоинт вернёт **скачиваемый `.md`‑файл** с саммари (правильные отступы/Markdown‑разметка);
  - без `download` возвращается JSON с полями `transcript` и `summary`.

- **`POST /summarize-transcript`**  
  Принимает **готовый текстовый файл транскрипции** (например, `*.txt` или `*.md`) и делает только саммаризацию без повторной транскрибации.  
  В Swagger UI можно:
  - загрузить файл транскрипта,
  - выбрать провайдера модели (`gemini`, `deepseek`, `chatgpt`) из выпадающего списка,
  - указать режим суммаризации (`meeting`, `english`, `interview`),
  - при необходимости выставить флаг `download=true`, чтобы получить результат как `.md`‑файл,
  - нажать кнопку **Execute** для запуска саммаризации.

## 🏗️ Архитектура

### Кодировка статусов в консоли

Программа использует единый стиль текстовых индикаторов вместо emoji:
- `[*] ` — Информационные сообщения.
- `[+] ` — Успешное выполнение.
- `[-] ` — Ошибки.
- `[!] ` — Предупреждения и важные уведомления.
- `[>] ` — Активные процессы (запись, транскрибация).

### Структура проекта

```
meeting-assistant/
├── core/
│   ├── config_manager.py      # Загрузка/сохранение конфигурации
│   ├── processor.py           # Транскрибация Deepgram + post‑обработка
│   ├── recorder.py            # Вспомогательная логика выбора рекордера
│   ├── llm/                   # Модуль LLM (Gemini, DeepSeek, ChatGPT)
│   │   ├── base.py            # Базовый класс провайдера LLM
│   │   ├── deepseek_provider.py   # DeepSeek V3/R1
│   │   ├── gemini_provider.py     # Gemini 2.0 Flash и fallback
│   │   ├── chatgpt_provider.py    # OpenAI GPT‑4o / 4o‑mini
│   │   └── prompts/               # Промпты для режимов саммари
│   │       ├── base_prompt.py
│   │       ├── meeting_prompt.py
│   │       ├── english_prompt.py
│   │       └── interview_prompt.py
│   ├── recorders/             # Движки записи (Legacy, Native, Multi)
│   │   ├── base_recorder.py   # Общий интерфейс рекордера
│   │   ├── legacy_recorder.py # Захват через Aggregate Device (BlackHole)
│   │   ├── native_recorder.py # Нативный macOS ScreenCaptureKit
│   │   └── multi_recorder.py  # Объединение системного звука и микрофона
│   └── utils/
│       ├── setup_utils.py     # Мастер настройки аудио и конфигурации
│       ├── audio_utils.py     # Обработка аудиофайлов
│       └── prompt_manager.py  # Управление выбором промптов/режимов
├── recorder_factory.py        # Фабрика выбора рекордера по конфигу
├── main.py                    # CLI точка входа
├── api.py                     # FastAPI сервер (Web API)
├── config.example.json        # Шаблон конфигурации
├── config.json                # Локальная конфигурация (игнорируется Git)
├── .env                       # API ключи (игнорируется Git)
├── Makefile                   # Утилитарные команды (install/run/api/clean)
└── requirements.txt           # Python‑зависимости
```

## 📄 Лицензия

MIT License

## 🙏 Благодарности

- [Deepgram](https://deepgram.com/) - за лучший API транскрибации
- [DeepSeek](https://www.deepseek.com/) - за мощные и доступные LLM (V3/R1)
- [OpenAI](https://openai.com/) - за ChatGPT
- [Google Gemini](https://ai.google.dev/) - за Gemini API
- [BlackHole](https://github.com/ExistentialAudio/BlackHole) - за виртуальный аудио-драйвер
