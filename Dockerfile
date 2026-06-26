FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY api_operator ./api_operator

RUN pip install --no-cache-dir .

EXPOSE 8100

CMD ["api-operator", "serve", "--host", "0.0.0.0", "--port", "8100", "--adapter", "yaml", "--planner", "mock"]
