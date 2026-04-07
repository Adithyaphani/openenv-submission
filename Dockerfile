FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn openenv-core pydantic openai
COPY . .
EXPOSE 7860
CMD python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
