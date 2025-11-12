from flask import Flask, render_template, request, jsonify
import pandas as pd
import geopandas as gpd
import os

app = Flask(__name__)

# --- BÜYÜK GÜNCELLEME (VERİ FİLTRELEME) ---

GEOJSON_PATH = 'static/turkey-ilceler.geojson'
ANKARA_IL_ADI = "Ankara" # Filtreleyeceğimiz ilin adı

ankara_gdf = None
ANKARA_ILCELERI = []

def load_and_filter_map():
    """
    Sunucu başlarken haritayı yükler, AKILLI filtreleme yapar 
    ve sonucu hafızaya alır.
    """
    global ankara_gdf, ANKARA_ILCELERI
    
    try:
        print(f"Büyük harita dosyası ({GEOJSON_PATH}) yükleniyor...")
        all_districts_gdf = gpd.read_file(GEOJSON_PATH)
        
        # --- YENİ KONTROL 1: İL SÜTUNUNU BUL ---
        il_sutun_adi = None
        if 'il_adi' in all_districts_gdf.columns:
            il_sutun_adi = 'il_adi'
        elif 'NAME_1' in all_districts_gdf.columns:
            il_sutun_adi = 'NAME_1'
        else:
            print(f"HATA: GeoJSON'da 'il_adi' veya 'NAME_1' adında bir İL sütunu bulunamadı!")
            print(f"BULUNAN TÜM SÜTUNLAR: {list(all_districts_gdf.columns)}")
            return # Fonksiyonu durdur

        print(f"İl filtresi için '{il_sutun_adi}' sütunu kullanılacak.")
        
        # --- Filtreleme ---
        ankara_gdf = all_districts_gdf[all_districts_gdf[il_sutun_adi] == ANKARA_IL_ADI].copy()
        
        if ankara_gdf.empty:
            print(f"HATA: '{ANKARA_IL_ADI}' için veri bulunamadı. '{il_sutun_adi}' sütunu doğru mu?")
            return

        # --- YENİ KONTROL 2: İLÇE SÜTUNUNU BUL ---
        ilce_sutun_adi = None
        if 'ad' in ankara_gdf.columns:
            ilce_sutun_adi = 'ad'
        elif 'NAME_2' in ankara_gdf.columns:
            ilce_sutun_adi = 'NAME_2'
        else:
            print(f"HATA: GeoJSON'da 'ad' veya 'NAME_2' adında bir İLÇE sütunu bulunamadı!")
            print(f"BULUNAN TÜM SÜTUNLAR: {list(ankara_gdf.columns)}")
            return # Fonksiyonu durdur
        
        print(f"İlçe adları için '{ilce_sutun_adi}' sütunu kullanılacak.")

        # --- Sütun adını standart 'ilce' adına çevir ---
        ankara_gdf = ankara_gdf.rename(columns={ilce_sutun_adi: 'ilce'})

        # --- İlçe listesini güncelle (Kontrol panelindeki <select> için) ---
        ANKARA_ILCELERI = sorted(ankara_gdf['ilce'].unique())
        
        print(f"Başarılı: Ankara için {len(ankara_gdf)} ilçe haritası hafızaya yüklendi.")
        print(f"Bulunan ilçeler: {ANKARA_ILCELERI}")

    except Exception as e:
        print(f"Harita yüklenirken kritik hata: {e}")

# --- KODUN GERİ KALANI (Değişiklik Yok) ---

# Veritabanı yerine geçici global veri saklama alanı
processed_data = {
    "sicaklik": {},
    "nem": {},
    "egim": {}
}

# Ana sayfayı yükler
@app.route('/')
def index():
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# CSV Yükleme ve İşleme
@app.route('/upload_data', methods=['POST'])
def upload_data():
    try:
        data_type = request.form['data_type']
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

# === HARİTA İÇİN API (Artık Hafızadaki KÜÇÜK Haritayı Kullanır) ===
@app.route('/api/get_map_data/<data_type>')
def get_map_data(data_type):
    global ankara_gdf # Hafızadaki filtrelenmiş haritayı kullan
    if ankara_gdf is None:
        return jsonify({"error": "Harita verisi sunucuda yüklenemedi."}), 500

    try:
        gdf_copy = ankara_gdf.copy()
        data_to_merge = processed_data.get(data_type, {})
        
        if not data_to_merge:
            gdf_copy['ortalama'] = pd.NA
            gdf_copy['renk'] = '#808080' 
            return gdf_copy.to_json()
        
        df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])
        merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

        def get_color(ortalama):
            if pd.isna(ortalama):
                return '#808080'  # Gri (veri yoksa)
            if ortalama > 17:
                return '#FF0000'  # Kırmızı
            if ortalama > 15:
                return '#FFFF00'  # Sarı
            return '#0000FF'  # Mavi

        merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)
        
        return merged_gdf.to_json()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SUNUCUYU BAŞLAT ---
if __name__ == '__main__':
    load_and_filter_map()
    app.run(debug=True)
else:
    # OnRender (Gunicorn) için de haritayı yükle ve filtrele
    load_and_filter_map()
