import requests
import os
import sys
import argparse


class TTSClient:
    def __init__(self, url="http://localhost:5002"):
        self.url = url
        self.session = requests.Session()

    def health(self):
        """Полная информация о сервере"""
        try:
            response = self.session.get(f"{self.url}/api/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def gpu_info(self):
        """Информация о GPU сервера"""
        try:
            response = self.session.get(f"{self.url}/api/gpu", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def is_server_running(self):
        return self.health() is not None

    def synthesize(self, text, language="ru", speaker_wav=None, output_file="output.wav",
                   temperature=0.65, top_k=50, top_p=0.85,
                   repetition_penalty=2.0, length_penalty=1.0,
                   gpt_cond_len=None, enable_text_splitting=False):
        """Синтез речи с расширенными параметрами"""

        print(f"\n📝 Синтез речи:")
        print(f"   Текст: {text[:80]}...")
        print(f"   Язык: {language}")
        print(f"   ⚙️ Параметры: temp={temperature}, top_k={top_k}, top_p={top_p}")

        # Если это локальный файл
        if speaker_wav and os.path.exists(speaker_wav):
            print(f"   🎤 Отправляем локальный файл: {speaker_wav}")
            return self._synthesize_with_file(text, language, speaker_wav, output_file,
                                              temperature, top_k, top_p, repetition_penalty,
                                              length_penalty, gpt_cond_len, enable_text_splitting)

        # Если это URL или None
        data = {
            "text": text,
            "language": language,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "length_penalty": length_penalty,
            "enable_text_splitting": enable_text_splitting
        }

        if gpt_cond_len is not None:
            data["gpt_cond_len"] = gpt_cond_len

        if speaker_wav:
            if speaker_wav.startswith(('http://', 'https://')):
                print(f"   🎤 Используем URL: {speaker_wav[:50]}...")
                data["speaker_wav"] = speaker_wav
            else:
                print(f"   🎤 Используем голос по умолчанию")

        try:
            response = self.session.post(
                f"{self.url}/api/tts",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=120
            )

            if response.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ Готово! Сохранено в: {output_file}")
                return True
            else:
                print(f"   ❌ Ошибка: {response.status_code}")
                print(f"   {response.text[:500]}")
                return False

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False

    def _synthesize_with_file(self, text, language, file_path, output_file,
                              temperature, top_k, top_p, repetition_penalty,
                              length_penalty, gpt_cond_len, enable_text_splitting):
        """Отправка локального файла с параметрами"""
        print(f"   📤 Отправляем файл...")
        try:
            with open(file_path, 'rb') as f:
                files = {'speaker_wav': (os.path.basename(file_path), f, 'audio/wav')}
                data = {
                    'text': text,
                    'language': language,
                    'temperature': str(temperature),
                    'top_k': str(top_k),
                    'top_p': str(top_p),
                    'repetition_penalty': str(repetition_penalty),
                    'length_penalty': str(length_penalty),
                    'enable_text_splitting': str(enable_text_splitting).lower()
                }
                if gpt_cond_len is not None:
                    data['gpt_cond_len'] = str(gpt_cond_len)

                response = self.session.post(
                    f"{self.url}/api/tts",
                    data=data,
                    files=files,
                    timeout=120
                )

                if response.status_code == 200:
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    print(f"   ✅ Готово! Сохранено в: {output_file}")
                    return True
                else:
                    print(f"   ❌ Ошибка: {response.status_code}")
                    print(f"   {response.text[:500]}")
                    return False

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='TTS Client с расширенными настройками')
    parser.add_argument('--text', '-t', type=str, help='Текст для озвучки')
    parser.add_argument('--language', '-l', type=str, default='ru', help='Язык (по умолчанию: ru)')
    parser.add_argument('--speaker', '-s', type=str, help='Путь к файлу с голосом или URL')
    parser.add_argument('--output', '-o', type=str, default='output.wav', help='Выходной файл')

    # Параметры синтеза
    parser.add_argument('--temperature', type=float, default=0.65, help='Креативность (0.0-1.0)')
    parser.add_argument('--top_k', type=int, default=50, help='Top-K фильтр (0-100)')
    parser.add_argument('--top_p', type=float, default=0.85, help='Top-P ядерная выборка (0-1)')
    parser.add_argument('--repetition_penalty', type=float, default=2.0, help='Штраф за повторы')
    parser.add_argument('--length_penalty', type=float, default=1.0, help='Контроль длины')
    parser.add_argument('--gpt_cond_len', type=int, help='Длина контекста клонирования')
    parser.add_argument('--split_sentences', action='store_true', help='Разбивать текст на предложения')
    parser.add_argument('--info', action='store_true', help='Показать информацию о сервере')
    parser.add_argument('--interactive', '-i', action='store_true', help='Интерактивный режим')

    args = parser.parse_args()

    client = TTSClient()

    print("Проверка подключения к TTS серверу...")
    if not client.is_server_running():
        print("❌ Сервер не запущен!")
        print("\nЗапустите сервер:")
        print('docker start tts-server')
        sys.exit(1)

    health = client.health()
    print(f"✓ Сервер работает")
    print(f"   🖥️ Устройство: {health.get('device', 'unknown')}")
    if health.get('gpu_available'):
        print(f"   🚀 GPU: {health.get('gpu_name')}")
        print(f"   💾 Память: {health.get('memory_allocated')}")

    # Показать информацию о GPU
    if args.info:
        gpu = client.gpu_info()
        if gpu:
            print("\n📊 Информация о GPU:")
            if gpu.get('available'):
                print(f"   🚀 {gpu.get('name')}")
                print(f"   💾 Всего памяти: {gpu.get('memory_total')}")
                print(f"   📊 Выделено: {gpu.get('memory_allocated')}")
                print(f"   📦 Зарезервировано: {gpu.get('memory_cached')}")
            else:
                print(f"   💻 {gpu.get('message')}")
        return

    if args.interactive:
        print("\n" + "=" * 50)
        print("Интерактивный режим TTS")
        print("=" * 50)

        while True:
            print("\n" + "-" * 40)
            text = input("Введите текст (или 'exit'): ").strip()
            if text.lower() == 'exit':
                break
            if not text:
                continue

            speaker = input("Путь к файлу с голосом (Enter - голос по умолчанию): ").strip()
            output = input("Имя выходного файла [output.wav]: ").strip() or "output.wav"

            client.synthesize(text, args.language, speaker if speaker else None, output,
                              args.temperature, args.top_k, args.top_p,
                              args.repetition_penalty, args.length_penalty,
                              args.gpt_cond_len, args.split_sentences)

    elif args.text:
        client.synthesize(args.text, args.language, args.speaker, args.output,
                          args.temperature, args.top_k, args.top_p,
                          args.repetition_penalty, args.length_penalty,
                          args.gpt_cond_len, args.split_sentences)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()