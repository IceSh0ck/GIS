from flask import Flask, render_template, request, jsonify
import pandas as pd
import geopandas as gpd
import os
import io

app = Flask(__name__)

# GeoJSON dosyasının yolu
GEOJSON_PATH = 'static/ankara-ilceler.geojson'

# Ankara ilçeleri (GeoJSON'dan da alınabilir)
ANKARA_ILCELERI = [
    "Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere",
    "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı",
    "Güdül", "Haymana", "Kahramankazan", "Kalecik", "Keçiören", "Kızılcahamam",
    "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"
]

# Veritabanı yerine geçici global veri saklama alanı
# { "sicaklik": {"Çankaya": 16.5, "Keçiören": 17.2}, "nem": {...} }
processed_data = {
    "sicaklik": {},
    "nem": {},
    "egim": {}
}

# Ana sayfayı yükler
@app.route('/')
def index():
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# CSV Yükleme ve İşleme (Sadece işler ve 'processed_data'ya kaydeder)
@app.route('/upload_data', methods=['POST'])
def upload_data():
    try:
        data_type = request.form['data_type']  # (Sıcaklık, Nem, Eğim)
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400

        # CSV'yi Pandas ile oku
        df = pd.read_csv(file)

        if data_type == 'sicaklik':
            if 'sicaklik' not in df.columns:
                return jsonify({'success': False, 'error': '"sicaklik" sütunu bulunamadı.'}), 400
            
            # Ortalama hesapla
            genel_ortalama = df['sicaklik'].mean()
            
            # "Veritabanına" kaydet (Birden fazla dosya için mantık güncellenmeli)
            processed_data[data_type][ilce] = genel_ortalama

            return jsonify({
                'success': True,
                'message': f'{ilce} için ortalama sıcaklık {genel_ortalama:.2f} olarak kaydedildi. Haritayı güncelleyin.'
            })
        
        # Nem ve Eğim için de benzer mantık eklenebilir
        else:
            return jsonify({'success': False, 'error': 'Bu veri tipi henüz desteklenmiyor.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === HARİTA İÇİN YENİ API ROUTE ===
# Leaflet'in haritayı çizmek için ihtiyaç duyduğu GeoJSON verisini sağlar
@app.route('/api/get_map_data/<data_type>')
def get_map_data(data_type):
    try:
        # 1. GeoJSON dosyasını GeoPandas ile oku
        # GeoJSON'unuzdaki ilçe adının olduğu sütun adını 'ILCE_ADI' ile değiştirin
        gdf = gpd.read_file(GEOJSON_PATH)
        
        # GeoJSON'daki ilçe sütun adını (örn: 'NAME_2', 'ilce_adi') 'ilce' yap
        # BU KISMI KENDİ GEOJSON DOSYANIZA GÖRE GÜNCELLEMENİZ GEREKİR
        # Örnek: gdf = gdf.rename(columns={'NAME_2': 'ilce'})
        # Biz 'ilce' olduğunu varsayalım:
        if 'ilce' not in gdf.columns:
             # Örnek bir GeoJSON'da 'NAME' olabilir, onu 'ilce' yapalım
             if 'NAME' in gdf.columns:
                 gdf = gdf.rename(columns={'NAME': 'ilce'})
             else:
                 # Uygun sütun bulunamazsa hata ver
                 return jsonify({"error": "GeoJSON dosyasında 'ilce' sütunu bulunamadı."}), 500


        # 2. İşlenmiş verileri bir DataFrame'e dönüştür
        data_to_merge = processed_data.get(data_type, {})
        if not data_to_merge:
            # Veri yoksa bile GeoJSON'u döndür
            return gdf.to_json()
        
        df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])

        # 3. GeoDataFrame (harita) ile DataFame'i (veri) birleştir
        # GeoJSON'daki ilçe adları ile bizim ilçe adlarımızın eşleştiğinden emin olun
        merged_gdf = gdf.merge(df, on='ilce', how='left')

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

if __name__ == '__main__':
    app.run(debug=True)
