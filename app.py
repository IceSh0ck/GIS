from flask import Flask, render_template, request, jsonify
import pandas as pd
import geopandas as gpd # Harita işlemleri için GEREKLİ
import os

app = Flask(__name__)

# --- Sunucu Hafızası ---
# Yüklenen verileri burada saklayacağız
processed_data = {
    "sicaklik": {}, # örn: {"Çankaya": 15.5, "Akyurt": 16.2}
    "nem": {},
    "egim": {}
}

# Ankara haritasını ve ilçe listesini hafızada tutacağız
ankara_gdf = None
ANKARA_ILCELERI = []

GEOJSON_PATH = 'static/turkey-ilceler.geojson'
ANKARA_IL_ADI = "Ankara"

def load_and_filter_map():
    """
    Sunucu başlarken haritayı yükler, Ankara'yı filtreler
    ve sonucu hafızaya alır.
    """
    global ankara_gdf, ANKARA_ILCELERI
    
    try:
        print(f"Büyük harita dosyası ({GEOJSON_PATH}) yükleniyor...")
        all_districts_gdf = gpd.read_file(GEOJSON_PATH)

        # Akıllı filtreleme (Büyük/küçük harf ve boşluk duyarsız)
        target_il = ANKARA_IL_ADI.strip().upper()
        il_sutun_adi = 'NAME_1' if 'NAME_1' in all_districts_gdf.columns else 'il_adi'
        
        il_filtresi = all_districts_gdf[il_sutun_adi].astype(str).str.strip().str.upper() == target_il
        ankara_gdf = all_districts_gdf[il_filtresi].copy()

        if ankara_gdf.empty:
            print(f"HATA: '{ANKARA_IL_ADI}' için veri bulunamadı. GeoJSON dosyasını kontrol edin.")
            return

        # İlçe sütununu bul ve standartlaştır
        ilce_sutun_adi = 'NAME_2' if 'NAME_2' in ankara_gdf.columns else 'ad'
        ankara_gdf['ilce'] = ankara_gdf[ilce_sutun_adi].astype(str).str.strip()
        
        # Gelecekte birleştirme için CRS (Koordinat Referans Sistemi) ayarla
        ankara_gdf = ankara_gdf.to_crs(epsg=4326)

        # İlçe listesini güncelle (Kontrol panelindeki <select> için)
        ANKARA_ILCELERI = sorted(ankara_gdf['ilce'].unique())
        
        print(f"Başarılı: Ankara için {len(ankara_gdf)} ilçe haritası hafızaya yüklendi.")
        print(f"Bulunan ilçeler: {ANKARA_ILCELERI}")

    except Exception as e:
        print(f"Harita yüklenirken kritik hata: {e}")

# --- Ana Sayfa ---
@app.route('/')
def index():
    # İlçe listesini (ANKARA_ILCELERI) dinamik olarak HTML'e gönder
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# --- Veri Yükleme (GÜNCELLENDİ) ---
@app.route('/upload_data', methods=['POST'])
def upload_data():
    global processed_data
    try:
        data_type = request.form['data_type'] # (sicaklik, nem, egim)
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400
        
        if data_type not in processed_data:
             return jsonify({'success': False, 'error': 'Geçersiz veri tipi.'}), 400

        df = pd.read_csv(file)

        # CSV'de 'data_type' ile aynı isimde sütun arayacağız
        if data_type not in df.columns:
            return jsonify({'success': False, 'error': f'CSV dosyasında "{data_type}" sütunu bulunamadı.'}), 400

        # Ortalama değeri hesapla
        ortalama_deger = df[data_type].mean()

        # Değeri sunucu hafızasına kaydet
        processed_data[data_type][ilce] = ortalama_deger

        print(f"KAYIT: Tür={data_type}, İlçe={ilce}, Ortalama={ortalama_deger}")

        return jsonify({
            'success': True,
            'message': f'{ilce} için ortalama {data_type} {ortalama_deger:.2f} olarak kaydedildi.'
        })

    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Harita Veri API'si (YENİ EKLENDİ) ---
# Burası, haritayı boyamak için veriyi GeoJSON ile birleştiren yer
@app.route('/api/get_map_data/<data_type>')
def get_map_data(data_type):
    global ankara_gdf, processed_data
    if ankara_gdf is None:
        return jsonify({"error": "Harita verisi sunucuda yüklenemedi."}), 500

    try:
        # Ana harita verisinin kopyasını al
        gdf_copy = ankara_gdf.copy()
        
        # Veri yoksa varsayılan renk
        varsayilan_renk = '#808080' # Gri
        
        if data_type == 'sicaklik':
            data_to_merge = processed_data['sicaklik']
            df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])
            merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

            def get_color(ortalama):
                if pd.isna(ortalama): return varsayilan_renk
                if ortalama > 17: return '#FF0000' # Kırmızı
                if ortalama > 15: return '#FFFF00' # Sarı
                return '#0000FF' # Mavi
            
            merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)

        elif data_type == 'nem':
            data_to_merge = processed_data['nem']
            df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])
            merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

            def get_color(ortalama):
                if pd.isna(ortalama): return varsayilan_renk
                if ortalama > 70: return '#0000FF' # Mavi (Çok Nemli)
                if ortalama > 50: return '#00FF00' # Yeşil (Orta)
                return '#FFFF00' # Sarı (Az Nemli)
            
            merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)
            
        elif data_type == 'egim':
            data_to_merge = processed_data['egim']
            df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])
            merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

            def get_color(ortalama):
                if pd.isna(ortalama): return varsayilan_renk
                if ortalama > 20: return '#FF0000' # Kırmızı (Çok Eğimli)
                if ortalama > 10: return '#FFFF00' # Sarı (Orta)
                return '#00FF00' # Yeşil (Az Eğimli)
            
            merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)

        elif data_type == 'toplama':
            # 3 veri setini de 'ilce' bazında birleştir
            sicaklik_df = pd.DataFrame(list(processed_data['sicaklik'].items()), columns=['ilce', 'sicaklik'])
            nem_df = pd.DataFrame(list(processed_data['nem'].items()), columns=['ilce', 'nem'])
            egim_df = pd.DataFrame(list(processed_data['egim'].items()), columns=['ilce', 'egim'])
            
            merged_gdf = gdf_copy.merge(sicaklik_df, on='ilce', how='left')
            merged_gdf = merged_gdf.merge(nem_df, on='ilce', how='left')
            merged_gdf = merged_gdf.merge(egim_df, on='ilce', how='left')

            def get_toplama_color(row):
                s = row['sicaklik']
                n = row['nem']
                e = row['egim']
                
                # Verilerden biri eksikse Gri
                if pd.isna(s) or pd.isna(n) or pd.isna(e):
                    return varsayilan_renk

                # Basit bir "Uygunluk" skoru hesaplayalım
                # İdeal: Sıcaklık > 15, Nem < 60, Eğim < 10
                score = 0
                if s > 15: score += 1
                if n < 60: score += 1
                if e < 10: score += 1
                
                if score == 3: return '#00FF00' # Yeşil (Çok Uygun)
                if score == 2: return '#FFFF00' # Sarı (Orta Uygun)
                return '#FF0000' # Kırmızı (Uygun Değil)
            
            merged_gdf['renk'] = merged_gdf.apply(get_toplama_color, axis=1)
            # Ortalama sütununu doldur ki popup'ta "Veri Yok" demesin
            merged_gdf['ortalama'] = merged_gdf['renk'] # Popup'ta 'ortalama' yerine rengi gösterebiliriz

        else:
             gdf_copy['ortalama'] = pd.NA
             gdf_copy['renk'] = varsayilan_renk
             return gdf_copy.to_json()

        return merged_gdf.to_json()

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- SUNUCUYU BAŞLAT ---
if __name__ == '__main__':
    load_and_filter_map() # Sunucu başlamadan haritayı hafızaya yükle
    app.run(debug=True)
else:
    # Gunicorn (Render.com vb.) için de haritayı yükle
    load_and_filter_map()
