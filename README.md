# 🎙️ TTS Russian Server

Простой и надёжный сервер для синтеза русской речи на основе Coqui XTTS-v2. Всё работает в Docker — никаких проблем с зависимостями, Python-версиями или CUDA.

## Возможности

- 🐳 **Docker-упаковка** — запускается одной командой, работает везде одинаково
- 🎤 **Клонирование голоса** — по локальному файлу, URL или голос по умолчанию
- 🌍 **12 языков** — русский, английский, испанский, французский, немецкий, итальянский, португальский, польский, турецкий, китайский, японский, корейский
- 🚀 **GPU поддержка** — автоматически использует CUDA при наличии
- 📡 **REST API** — можно использовать из любого языка программирования
- 🧹 **Автоочистка** — временные файлы удаляются автоматически, без утечек памяти

## Запуск

### 1. Сборка образа

```bash
docker build -t tts-russian .
```

### 2. Первый запуск (скачивание модели)

При первом запуске модель скачается в кэш. Нужно указать `-it`, чтобы принять условия лицензии:

```bash
docker run -it -p 5002:5002 --entrypoint python3 tts-russian /app/server.py
```

После того как увидите `✓ Сервер готов!`, можно переходить к использованию. Модель сохранится в volume и при следующих запусках не будет скачиваться заново.

### 3. Последующие запуски (фон)

Когда модель уже закеширована, можно запускать в фоне:

```bash
docker run -d -p 5002:5002 --entrypoint python3 tts-russian /app/server.py
```

### 4. Запуск с GPU

```bash
docker run -it --gpus all -p 5002:5002 --entrypoint python3 tts-russian /app/server.py
```

### 5. Проверка работы

```bash
curl http://localhost:5002/api/health
```

Ответ должен быть таким:

```json
{"device":"CUDA","gpu_available":true,"gpu_name":"NVIDIA GeForce RTX 3080","memory_allocated":"1.91 GB","model":"xtts_v2","status":"ok"}
```

## Использование

### Простой синтез

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, это тест русского языка"}' \
  --output speech.wav
```

### Клонирование голоса из файла

```bash
curl -X POST http://localhost:5002/api/tts \
  -F "text=Это клонирование моего голоса" \
  -F "speaker_wav=@/путь/к/voice.wav" \
  --output cloned.wav
```

### Клонирование голоса из URL

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Клонирование из интернета",
    "speaker_wav": "https://example.com/voice.wav"
  }' \
  --output cloned.wav
```

### С параметрами синтеза

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Экспериментальный синтез",
    "temperature": 0.8,
    "top_k": 30,
    "repetition_penalty": 2.5
  }' \
  --output experimental.wav
```

### Английский текст

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world", "language": "en"}' \
  --output hello_en.wav
```

### Встроенный клиент (опционально)

В репозитории есть удобный Python-клиент:

```bash
python tts_clientv3.py --text "Привет, мир" --output hello.wav
python tts_clientv3.py --text "Клонирование" --speaker voice.wav --output clone.wav
python tts_clientv3.py --interactive
python tts_clientv3.py --info  # информация о GPU
```

## 📚 API Reference

Полная документация по API находится в файле [API_REFERENCE.md](API_REFERENCE.md).

Там описаны:

- Все эндпоинты (`/api/health`, `/api/gpu`, `/api/tts`)
- Параметры запроса с пояснениями
- Примеры на curl, Python, JavaScript
- Коды ошибок
- Поддерживаемые языки

## Примеры синтеза

### Голос по умолчанию

Текст: *«Привет, это тест русского языка. Система работает отлично!»*

<video src='' controls width='100%' />

*Примечание: после запуска видео нажмите на иконку звука 🔈, чтобы включить аудио.*

### Клонирование голоса

Текст: *«Это пример клонирования голоса. Звучит как оригинал.»*

<video src='' controls width='100%' />

### Английская речь

Текст: *«The quick brown fox jumps over the lazy dog.»*

<video src='' controls width='100%' />

## Лицензия

**Mozilla Public License Version 2.0**

Этот проект использует:

- **Coqui TTS** — MPL-2.0
- **Flask** — BSD 3-Clause
- **PyTorch** — BSD-style

Подробности в файле [LICENSE](LICENSE).

---

## Благодарности

- [Coqui TTS](https://github.com/coqui-ai/TTS) — за отличную модель синтеза речи
- [Flask](https://flask.palletsprojects.com/) — за лёгкий и гибкий веб-фреймворк
- Сообщество open source — за поддержку и развитие
