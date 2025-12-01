FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV APP_DIR=/usr/src/crm
WORKDIR $APP_DIR

# Copy dependency files
COPY ./pyproject.toml ./uv.lock ./

# Install dependencies without dev dependencies
RUN uv sync --frozen --no-dev --no-cache

# Copy application code
COPY ./src ./src
COPY ./alembic ./alembic
COPY ./alembic.ini ./
COPY ./entrypoint.sh ./
COPY ./gunicorn_conf.py ./

# Add venv to PATH so installed packages are available
ENV PATH="${APP_DIR}/.venv/bin:${PATH}"

RUN chmod +x ./entrypoint.sh
ENV PYTHONPATH="${PYTHONPATH}:${APP_DIR}"
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
