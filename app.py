from flask import Flask, render_template, request, jsonify
import pandas as pd
import geopandas as gpd
import os

app = Flask(__name__)

# --- BÜYÜK GÜNCELLEME (VERİ FİLTRELEME) ---

# GeoJSON dosyasının yolu (Artık tüm Türkiye'yi içeriyor)
GEOJSON_PATH = 'static/turkey-ilceler.geojson'
ANKARA_IL_ADI = "Ankara" # Filtreleyeceğimiz ilin adı

# Global değişkenler (Sunucu açılırken doldurulacak)
ankara_gdf = None
ANKARA_ILCELERI = []

def load_and_filter_map():
    """
    Sunucu başlarken haritayı SADECE BİR KEZ yükler,
    Ankara'yı filtreler ve hafızaya alır.
    """
    global ankara_gdf, ANKARA_ILCELERI
    
    try:
        print(f"Büyük harita dosyası ({GEOJSON_PATH}) yükleniyor...")
        # 1. Tüm Türkiye haritasını yükle (Sadece 1 kez)
        all_districts_gdf = gpd.read_file(GEOJSON_PATH)
        
        print(f"'{ANKARA_IL_ADI}' iline ait veriler filtreleniyor...")
        # 2. Sadece Ankara'ya ait olanları filtrele
        #    GeoJSON dosyasındaki il adı sütununun 'il_adi' olduğunu varsayıyoruz
        ankara_gdf = all_districts_gdf[all_districts_gdf['il_adi'] == ANKARA_IL_ADI].copy()
        
        if ankara_gdf.empty:
            print(f"HATA: '{ANKARA_IL_ADI}' için veri bulunamadı. 'il_adi' anahtarı doğru mu?")
            return

        # 3. GeoJSON'daki ilçe adı sütununu ('ad') 'ilce' adına çevir
        if 'ad' in ankara_gdf.columns:
            ankara_gdf = ankara_gdf.rename(columns={'ad': 'ilce'})
        else:
            print("HATA: GeoJSON'da 'ad' sütunu bulunamadı.")
            return

        # 4. İlçe listesini güncelle (Kontrol panelindeki <select> için)
        ANKARA_ILCELERI = sorted(ankara_gdf['ilce'].unique())
        
        print(f"Başarılı: Ankara için {len(ankara_gdf)} ilçe haritası hafızaya yüklendi.")
        print(f"Bulunan ilçeler: {ANKARA_ILCELERI}")

    except Exception as e:
        print(f"Harita yüklenirken kritik hata: {e}")

# --- ESKİ KODLAR (Hafifçe Güncellendi) ---

# Veritabanı yerine geçici global veri saklama alanı
processed_data = {
    "sicaklik": {},
    "nem": {},
    "egim": {}
}

# Ana sayfayı yükler (Artık ilçe listesini global değişkenden alır)
@app.route('/')
def index():
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# CSV Yükleme ve İşleme (Değişiklik yok)
@app.route('/upload_data', methods=['POST'])
def upload_data():
    try:
        data_type = request.form['data_type']  # (Sıcaklık, Nem, Eğim)
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400

        df = pd.read_csv(file)

        if data_type == 'sicaklik':
            if 'sicaklik' not in df.columns:
                return jsonify({'success': False, 'error': '"sicaklik" sütunu bulunamadı.'}), 400
            
            genel_ortalama = df['sicaklik'].mean()
            processed_data[data_type][ilce] = genel_ortalama

            return jsonify({
                'success': True,
                'message': f'{ilce} için ortalama sıcaklık {genel_ortalama:.2f} olarak kaydedildi.'
            })
        
        else:
            return jsonify({'success': False, 'error': 'Bu veri tipi henüz desteklenmiyor.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === HARİTA İÇİN API ROUTE (Artık Çok Hızlı) ===
# Bu fonksiyon artık hafızadaki KÜÇÜK Ankara haritasını kullanır
@app.route('/api/get_map_data/<data_type>')
def get_map_data(data_type):
    global ankara_gdf
    if ankara_gdf is None:
        return jsonify({"error": "Harita verisi sunucuda yüklenemedi."}), 500

    try:
        # 1. Hafızadaki filtrelenmiş Ankara haritasını kopyala (Çok Hızlı)
        gdf_copy = ankara_gdf.copy()

        # 2. İşlenmiş verileri bir DataFrame'e dönüştür
        data_to_merge = processed_data.get(data_type, {})
        if not data_to_merge:
            # Veri yoksa bile, renksiz haritayı döndür
            gdf_copy['ortalama'] = pd.NA
            gdf_copy['renk'] = '#808080' # Gri (veri yoksa)
            return gdf_copy.to_json()
        
        df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])

        # 3. Ankara haritası ile sıcaklık verisini birleştir
        merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

        # 4. Renklendirme mantığı
        def get_color(ortalama):
            if pd.isna(ortalama):
                return '#808080'  # Gri (veri yoksa)
            if ortalama > 17:
                return '#FF0000'  # Kırmızı
            if ortalama > 15:
                return '#FFFF00'  # Sarı
            return '#0000FF'  # Mavi

        merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)
        
        # 5. Sonuçları Leaflet'in anlayacağı GeoJSON formatında döndür
        return merged_gdf.to_json()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SUNUCUYU BAŞLAT ---
if __name__ == '__main__':
    # Sunucu çalışmadan önce haritayı yükle VE FİLTRELE
    load_and_filter_map()
    app.run(debug=True)
else:
    # OnRender gibi Gunicorn sunucuları 'app' değişkenini arar
    # Onlar için de haritayı yükle ve filtrele
    load_and_filter_map()
