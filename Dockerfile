FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --group web

COPY agent ./agent
COPY web ./web
COPY main.py .

RUN mkdir -p /app/resumes

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080"]