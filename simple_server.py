import os
import torch
import tempfile
import shutil
import atexit
from flask import Flask, request, send_file, jsonify
from TTS.api import TTS
import io
import requests as req


# ============================================
# Управление временными файлами
# ============================================
class TempFileManager:
    """Менеджер временных файлов для автоматической очистки"""

    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
        atexit.register(self.cleanup)

    def add_file(self, path):
        """Добавляет файл для отслеживания"""
        if path and os.path.exists(path):
            self.temp_files.append(path)
        return path

    def add_dir(self, path):
        """Добавляет директорию для отслеживания"""
        if path and os.path.exists(path):
            self.temp_dirs.append(path)
        return path

    def create_temp_file(self, suffix='.wav', prefix='tts_'):
        """Создает временный файл и регистрирует его"""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        self.temp_files.append(path)
        return path

    def create_temp_dir(self, prefix='tts_'):
        """Создает временную директорию и регистрирует её"""
        path = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(path)
        return path

    def cleanup(self):
        """Очищает все временные файлы и директории"""
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass
        self.temp_files.clear()

        for path in self.temp_dirs:
            try:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
            except:
                pass
        self.temp_dirs.clear()

    def cleanup_file(self, path):
        """Удаляет конкретный файл из отслеживания"""
        if path in self.temp_files:
            self.temp_files.remove(path)
        try:
            if os.path.exists(path):
                os.unlink(path)
        except:
            pass


# Глобальный менеджер временных файлов
temp_manager = TempFileManager()


# ============================================
# Определение устройства (GPU/CPU)
# ============================================
def get_device():
    """Определяет доступное устройство (GPU или CPU)"""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"   🚀 GPU найден: {gpu_name}")
        print(f"   📊 Видеопамять: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        return device
    else:
        print("   💻 GPU не доступен, используем CPU")
        return "cpu"


# Определяем устройство
device = get_device()

# Патч для PyTorch load
original_load = torch.load


def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)


torch.load = patched_load

app = Flask(__name__)

print("=" * 60)
print("Запуск TTS сервера...")
print("=" * 60)

# Загружаем модель на нужное устройство
print(f"Загрузка модели XTTS v2 на {device.upper()}...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print("✓ Модель успешно загружена!")

# Скачиваем пример голоса для клонирования
DEFAULT_VOICE_URL = "https://github.com/coqui-ai/TTS/raw/dev/tests/data/ljspeech/wavs/LJ001-0001.wav"
default_voice_file = None


def get_default_voice():
    """Возвращает путь к голосу по умолчанию (с кэшированием)"""
    global default_voice_file
    if default_voice_file and os.path.exists(default_voice_file):
        return default_voice_file

    print("Скачиваем пример голоса...")
    try:
        response = req.get(DEFAULT_VOICE_URL, timeout=30)
        if response.status_code == 200:
            default_voice_file = temp_manager.create_temp_file(suffix='.wav', prefix='default_voice_')
            with open(default_voice_file, 'wb') as f:
                f.write(response.content)
            print(f"✓ Голос скачан")
            return default_voice_file
    except Exception as e:
        print(f"⚠️ Не удалось скачать голос: {e}")
    return None


print("\n✓ Сервер готов!")
print(f"   🖥️ Устройство: {device.upper()}")
print(f"   🌐 Слушаем на http://0.0.0.0:5002")
print("=" * 60)


@app.route('/api/health', methods=['GET'])
def health():
    """Проверка состояния сервера"""
    return jsonify({
        "status": "ok",
        "model": "xtts_v2",
        "device": device.upper(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB" if torch.cuda.is_available() else None
    })


@app.route('/api/tts', methods=['POST'])
def tts_endpoint():
    """Синтез речи с поддержкой JSON и multipart/form-data"""

    # Для отслеживания созданных временных файлов в этом запросе
    request_temp_files = []

    try:
        speaker_wav = None
        text = None
        language = "ru"

        # Параметры синтеза с значениями по умолчанию
        temperature = 0.65
        top_k = 50
        top_p = 0.85
        repetition_penalty = 2.0
        length_penalty = 1.0
        gpt_cond_len = None
        enable_text_splitting = False

        # Поддержка и JSON, и multipart/form-data
        if request.is_json:
            data = request.get_json()
            text = data.get('text', '')
            language = data.get('language', 'ru')
            speaker_wav = data.get('speaker_wav', None)

            # Читаем дополнительные параметры
            temperature = data.get('temperature', temperature)
            top_k = data.get('top_k', top_k)
            top_p = data.get('top_p', top_p)
            repetition_penalty = data.get('repetition_penalty', repetition_penalty)
            length_penalty = data.get('length_penalty', length_penalty)
            gpt_cond_len = data.get('gpt_cond_len', gpt_cond_len)
            enable_text_splitting = data.get('enable_text_splitting', enable_text_splitting)
        else:
            # multipart/form-data
            text = request.form.get('text', '')
            language = request.form.get('language', 'ru')

            # Читаем параметры из form
            if request.form.get('temperature'):
                temperature = float(request.form.get('temperature'))
            if request.form.get('top_k'):
                top_k = int(request.form.get('top_k'))
            if request.form.get('top_p'):
                top_p = float(request.form.get('top_p'))
            if request.form.get('repetition_penalty'):
                repetition_penalty = float(request.form.get('repetition_penalty'))
            if request.form.get('length_penalty'):
                length_penalty = float(request.form.get('length_penalty'))
            if request.form.get('gpt_cond_len'):
                gpt_cond_len = int(request.form.get('gpt_cond_len'))
            enable_text_splitting = request.form.get('enable_text_splitting', 'false').lower() == 'true'

            # Проверяем, есть ли файл в запросе
            if 'speaker_wav' in request.files:
                file = request.files['speaker_wav']
                if file and file.filename:
                    # Сохраняем во временный файл
                    temp_voice = temp_manager.create_temp_file(suffix='.wav', prefix='upload_')
                    file.save(temp_voice)
                    speaker_wav = temp_voice
                    print(f"   📥 Получен файл: {file.filename} -> {temp_voice}")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        print(f"\n📝 Синтез:")
        print(f"   Текст: {text[:80]}...")
        print(f"   Язык: {language}")
        print(f"   🖥️ Устройство: {device.upper()}")
        print(f"   ⚙️ Параметры: temp={temperature}, top_k={top_k}, top_p={top_p}")

        # Если speaker_wav не указан, используем голос по умолчанию
        if not speaker_wav:
            print(f"   🎤 Используем голос по умолчанию")
            speaker_wav = get_default_voice()
            if not speaker_wav:
                return jsonify({"error": "No speaker_wav provided and default voice not available"}), 400
        else:
            print(f"   🎤 Клонирование голоса")

        # Если speaker_wav - это URL, скачиваем
        local_voice = None
        if isinstance(speaker_wav, str) and speaker_wav.startswith(('http://', 'https://')):
            print(f"   📥 Скачиваем голос из URL: {speaker_wav[:50]}...")
            local_voice = temp_manager.create_temp_file(suffix='.wav', prefix='url_')
            response = req.get(speaker_wav, timeout=30)
            if response.status_code != 200:
                return jsonify({"error": f"Failed to download voice from {speaker_wav}"}), 400
            with open(local_voice, 'wb') as f:
                f.write(response.content)
            speaker_wav = local_voice
            print(f"   ✓ Голос скачан")

        # Создаем выходной файл
        output_path = temp_manager.create_temp_file(suffix='.wav', prefix='output_')

        # Формируем аргументы для синтеза
        kwargs = {
            "text": text,
            "speaker_wav": speaker_wav,
            "language": language,
            "file_path": output_path,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "length_penalty": length_penalty,
            "enable_text_splitting": enable_text_splitting
        }

        if gpt_cond_len is not None:
            kwargs["gpt_cond_len"] = gpt_cond_len

        # Синтез
        tts.tts_to_file(**kwargs)

        # Читаем результат
        with open(output_path, 'rb') as f:
            audio_data = f.read()

        # Удаляем выходной файл (он уже прочитан)
        temp_manager.cleanup_file(output_path)

        # Если это был скачанный URL-голос, удаляем его
        if local_voice:
            temp_manager.cleanup_file(local_voice)

        # Если это был загруженный через форму файл, удаляем его
        if speaker_wav and speaker_wav != get_default_voice() and speaker_wav != local_voice:
            # Проверяем, не является ли это голосом по умолчанию
            is_default = (default_voice_file and speaker_wav == default_voice_file)
            if not is_default:
                temp_manager.cleanup_file(speaker_wav)

        print(f"   ✓ Готово! Размер: {len(audio_data)} байт")

        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/wav',
            as_attachment=True,
            download_name='speech.wav'
        )

    except Exception as e:
        print(f"   ✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Дополнительный эндпоинт для информации о GPU
@app.route('/api/gpu', methods=['GET'])
def gpu_info():
    """Информация о GPU"""
    if torch.cuda.is_available():
        return jsonify({
            "available": True,
            "name": torch.cuda.get_device_name(0),
            "memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB",
            "memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
            "memory_cached": f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB"
        })
    else:
        return jsonify({
            "available": False,
            "message": "CUDA not available, using CPU"
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)