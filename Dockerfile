# 1. Adım: Temel Python imajını seç
FROM python:3.10-slim

# 2. Adım (KRİTİK): Geopandas'ın ihtiyaç duyduğu sistem kütüphanelerini kur
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
 && rm -rf /var/lib/apt/lists/*

# 3. Adım: Çalışma dizinini ayarla
WORKDIR /app

# 4. Adım: Önce requirements.txt dosyasını kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Adım: Geri kalan tüm kodları (app.py, static/, templates/) kopyala
COPY . .

# 6. Adım: Gunicorn sunucusunu çalıştır
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
