FROM python:3.11-slim-bookworm

# ─────────────────────────────────────────────────────────
# ⚙️ RUNTIME ENVIRONMENT PARAMETERS (Koyeb RAM Protection)
# ─────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ="Asia/Kolkata"

WORKDIR /app

# ─────────────────────────────────────────────────────────
# 📦 INSTALL ESSENTIALS & C-COMPILER DEPS
# ─────────────────────────────────────────────────────────
# tzdata: Syncs OS level time with info.py TIME_ZONE
# ffmpeg: Vital engine for video metadata diagnostics
# gcc/python3-dev: Required for compiling uvloop and TgCrypto C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    python3-dev \
    ffmpeg \
    git \
    tzdata \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────
# ⚡ DEPENDENCIES PRE-COMPILATION PIPELINE
# ─────────────────────────────────────────────────────────
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --compile -r requirements.txt

# ─────────────────────────────────────────────────────────
# 🗑️ AGGRESSIVE IMAGES TRIMMING (Post-Compilation Purge)
# ─────────────────────────────────────────────────────────
# Removing heavy C-compilers after wheels are built successfully.
# This drops the container layer storage footprint by up to 60%.
RUN apt-get purge -y --auto-remove \
    gcc \
    python3-dev \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip

# Copy absolute production repository elements
COPY . .

# Expose communication port for web server sync
EXPOSE 8000

# Start core admin bot lifecycle loop
CMD ["python", "bot.py"]
