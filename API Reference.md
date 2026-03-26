# API Reference

Сервер предоставляет REST API для синтеза речи. Все эндпоинты доступны по базовому URL `http://localhost:5002`.

## Health Check

Проверка состояния сервера и получение информации о конфигурации.

### `GET /api/health`

**Response:**

```json
{
  "status": "ok",
  "model": "xtts_v2",
  "device": "CUDA",
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 3060",
  "memory_allocated": "2.45 GB"
}
```

---

## GPU Information

Детальная информация о графическом процессоре (если доступен).

### `GET /api/gpu`

**Response (GPU доступен):**

```json
{
  "available": true,
  "name": "NVIDIA GeForce RTX 3060",
  "memory_total": "12.0 GB",
  "memory_allocated": "2.45 GB",
  "memory_cached": "3.12 GB"
}
```

**Response (GPU не доступен):**

```json
{
  "available": false,
  "message": "CUDA not available, using CPU"
}
```

---

## Синтез речи

### `POST /api/tts`

Основной эндпоинт для генерации речи. Поддерживает два формата запроса:

1. **JSON** — для программного использования
2. **multipart/form-data** — для загрузки файлов с голосом

---

### Параметры запроса

| Параметр      | Тип         | Обязательный | По умолчанию  | Описание                                                                                |
| ------------- | ----------- | ------------ | ------------- | --------------------------------------------------------------------------------------- |
| `text`        | string      | ✅            | —             | Текст для озвучивания                                                                   |
| `language`    | string      | ❌            | `"ru"`        | Язык текста (`ru`, `en`, `es`, `fr`, `de`, `it`, `pt`, `pl`, `tr`, `zh-cn`, `ja`, `ko`) |
| `speaker_wav` | string/file | ❌            | default voice | Путь к WAV-файлу с голосом для клонирования (URL, локальный путь или загружаемый файл)  |

#### Параметры синтеза (опциональные)

| Параметр                | Тип   | По умолчанию | Описание                                                     |
| ----------------------- | ----- | ------------ | ------------------------------------------------------------ |
| `temperature`           | float | `0.65`       | Креативность (0.0–1.0). Выше = более разнообразный результат |
| `top_k`                 | int   | `50`         | Top-K фильтр. Ограничивает выбор следующих токенов           |
| `top_p`                 | float | `0.85`       | Ядерная выборка (nucleus sampling). Альтернатива top_k       |
| `repetition_penalty`    | float | `2.0`        | Штраф за повторяющиеся фразы. >1 = меньше повторов           |
| `length_penalty`        | float | `1.0`        | Контроль длины. <1 = короче, >1 = длиннее                    |
| `gpt_cond_len`          | int   | `null`       | Длина контекста для клонирования голоса                      |
| `enable_text_splitting` | bool  | `false`      | Разбивать длинный текст на предложения                       |

---

### Формат 1: JSON

**Запрос:**

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Привет, это тест русского языка",
    "language": "ru",
    "temperature": 0.7,
    "top_p": 0.9
  }' \
  --output speech.wav
```

**Response:** WAV-файл (audio/wav)

---

### Формат 2: multipart/form-data

Для отправки локального WAV-файла для клонирования голоса.

**Запрос:**

```bash
curl -X POST http://localhost:5002/api/tts \
  -F "text=Это клонирование моего голоса" \
  -F "language=ru" \
  -F "temperature=0.65" \
  -F "speaker_wav=@/path/to/voice.wav" \
  --output cloned.wav
```

**Параметры в form-data:**

- Все параметры передаются как текстовые поля
- `speaker_wav` — файл WAV (multipart file)

---

### Клонирование голоса по URL

Если голос для клонирования доступен по ссылке:

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Клонирование из интернета",
    "language": "ru",
    "speaker_wav": "https://example.com/voice.wav"
  }' \
  --output cloned.wav
```

---

## Примеры использования

### Простейший запрос (голос по умолчанию)

```bash
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, мир"}' \
  --output hello.wav
```

### С параметрами

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
  -d '{
    "text": "Hello, this is English test",
    "language": "en"
  }' \
  --output english.wav
```

### Клонирование с локальным файлом

```bash
curl -X POST http://localhost:5002/api/tts \
  -F "text=Это мой клонированный голос" \
  -F "speaker_wav=@my_voice.wav" \
  --output my_voice_clone.wav
```

---

## Коды ошибок

| Код   | Описание                                                       |
| ----- | -------------------------------------------------------------- |
| `200` | Успешный синтез, возвращается WAV-файл                         |
| `400` | Ошибка в запросе (нет текста, неверные параметры)              |
| `500` | Внутренняя ошибка сервера (проблемы с моделью, памятью и т.д.) |

**Пример ошибки (400):**

```json
{
  "error": "No text provided"
}
```

---

## Python пример без использования tts_client

```python
import requests

def simple_tts(text, output_file, language="ru", speaker_wav=None):
    url = "http://localhost:5002/api/tts"

    if speaker_wav and not speaker_wav.startswith(('http://', 'https://')):
        # Локальный файл — используем multipart
        with open(speaker_wav, 'rb') as f:
            files = {'speaker_wav': f}
            data = {'text': text, 'language': language}
            response = requests.post(url, data=data, files=files)
    else:
        # JSON запрос
        payload = {
            "text": text,
            "language": language,
            "speaker_wav": speaker_wav if speaker_wav else None
        }
        response = requests.post(url, json=payload)

    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"✅ Сохранено в {output_file}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)

# Использование
simple_tts("Привет, мир", "hello.wav")
simple_tts("Клонирование", "clone.wav", speaker_wav="my_voice.wav")
```

---

## JavaScript (Node.js) пример

```javascript
const fs = require('fs');
const fetch = require('node-fetch');
const FormData = require('form-data');

async function tts(text, outputFile, options = {}) {
    const url = 'http://localhost:5002/api/tts';

    let response;

    if (options.speakerWav && !options.speakerWav.startsWith('http')) {
        // Локальный файл
        const form = new FormData();
        form.append('text', text);
        form.append('language', options.language || 'ru');
        form.append('speaker_wav', fs.createReadStream(options.speakerWav));

        response = await fetch(url, {
            method: 'POST',
            body: form
        });
    } else {
        // JSON запрос
        response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                language: options.language || 'ru',
                speaker_wav: options.speakerWav || null,
                temperature: options.temperature,
                top_p: options.top_p
            })
        });
    }

    if (response.ok) {
        const buffer = await response.buffer();
        fs.writeFileSync(outputFile, buffer);
        console.log(`✅ Saved to ${outputFile}`);
    } else {
        console.error(`❌ Error: ${response.status}`);
    }
}

// Использование
await tts("Привет, мир", "hello.wav");
await tts("Клонирование", "clone.wav", { speakerWav: "my_voice.wav" });
```

---

## Поддерживаемые языки

| Код     | Язык                   |
| ------- | ---------------------- |
| `ru`    | Русский                |
| `en`    | Английский             |
| `es`    | Испанский              |
| `fr`    | Французский            |
| `de`    | Немецкий               |
| `it`    | Итальянский            |
| `pt`    | Португальский          |
| `pl`    | Польский               |
| `tr`    | Турецкий               |
| `zh-cn` | Китайский (упрощённый) |
| `ja`    | Японский               |
| `ko`    | Корейский              |

---


