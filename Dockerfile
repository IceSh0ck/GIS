# 1. Temel işletim sistemi olarak Python 3.10'u seç
FROM python:3.10-slim-bookworm

# 2. GeoPandas'ın ihtiyacı olan SİSTEM kütüphanelerini kur
#    (OnRender'da hataya sebep olan kısım burasıydı)
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# 3. Konteyner içinde çalışacağımız klasörü oluştur
WORKDIR /app

# 4. Önce kütüphane listesini kopyala ve kur
#    Bu sıralama, kodunuzu her değiştirdiğinizde kurulumu hızlandırır
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Projenin geri kalan tüm dosyalarını (app.py, static/, templates/) kopyala
COPY . .

# 6. OnRender'ın sunucuya hangi porttan ulaşacağını tanımla
#    OnRender bu çevre değişkenini otomatik olarak sağlar
ENV PORT 10000

# 7. Konteyner başladığında çalıştırılacak ana komut
#    Bu, OnRender'daki "Start Command"in yerini alır
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:${PORT}"]
