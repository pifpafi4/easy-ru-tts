FROM ghcr.io/coqui-ai/tts-cpu

# Устанавливаем Flask
RUN pip install flask

# Копируем наш сервер
COPY simple_server.py /app/server.py

# Открываем порт
EXPOSE 5002

# Запускаем сервер
CMD ["python3", "/app/server.py"]
