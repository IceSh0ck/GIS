from flask import Flask, render_template, request, jsonify
import pandas as pd
import geopandas as gpd 
import os
import json 

app = Flask(__name__)

# --- Sunucu Hafızası ---
processed_data = {
    "sicaklik": {}, 
    "nem": {},
    "egim": {}
}
ANKARA_ILCELERI = [] 
JSON_LIST_PATH = os.path.join('static', 'il-ilce-listesi.json')
ankara_gdf = None 
GEOJSON_MAP_PATH = os.path.join('static', 'İlçe_Sınırı.shp')

def load_district_list_from_json():
    """MENÜ için ilçe listesini JSON'dan okur"""
    global ANKARA_ILCELERI
    try:
        with open(JSON_LIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "Ankara" in data:
                ANKARA_ILCELERI = sorted(data["Ankara"])
                print(f"Başarılı: Menü için {len(ANKARA_ILCELERI)} ilçe JSON'dan yüklendi.")
            else:
                print(f"HATA: '{JSON_LIST_PATH}' dosyasında 'Ankara' anahtarı bulunamadı.")
    except FileNotFoundError:
        print(f"HATA: Menü listesi '{JSON_LIST_PATH}' dosyası bulunamadı!")
    except Exception as e:
        print(f"Menü JSON yüklenirken hata: {e}")

def load_map_file():
    """HARİTA için ilçe şekillerini .shp dosyasından okur"""
    global ankara_gdf
    try:
        print(f"Ankara haritası ({GEOJSON_MAP_PATH}) yükleniyor...")
        
        # --- DÜZELTME BURADA ---
        # Shapefile'daki Türkçe karakterleri (Ç, Ş, Ğ) okuyabilmek için
        # 'latin5' veya 'ISO-8859-9' kodlamasını ekliyoruz.
        ankara_gdf = gpd.read_file(GEOJSON_MAP_PATH, encoding='ISO-8859-9')
        # -------------------------
        
        ilce_sutun_adi = None
        if 'ilce_adi' in ankara_gdf.columns: ilce_sutun_adi = 'ilce_adi'
        elif 'AD' in ankara_gdf.columns: ilce_sutun_adi = 'AD'
        elif 'NAME' in ankara_gdf.columns: ilce_sutun_adi = 'NAME'
        elif 'ilce' in ankara_gdf.columns: ilce_sutun_adi = 'ilce'
        elif 'NAME_2' in ankara_gdf.columns: ilce_sutun_adi = 'NAME_2'
        else:
            print(f"HATA: Shapefile (.dbf) içinde ilçe sütunu bulunamadı.")
            print(f"Bulunan sütunlar: {list(ankara_gdf.columns)}")
            return

        print(f"Harita için '{ilce_sutun_adi}' sütunu ilçe adı olarak kullanılacak.")
        
        # Haritadaki ilçe adlarını temizle ve standart 'ilce' sütununa ata
        ankara_gdf['ilce'] = ankara_gdf[ilce_sutun_adi].astype(str).str.strip()
        
        # Web haritalarıyla uyumlu Koordinat Referans Sistemine (CRS) dönüştür
        ankara_gdf = ankara_gdf.to_crs(epsg=4326)
        
        print(f"Başarılı: {len(ankara_gdf)} ilçelik harita şekli yüklendi.")
        
        # Eşleşme Kontrolü
        menu_ilceleri = set(ANKARA_ILCELERI)
        harita_ilceleri = set(ankara_gdf['ilce'])
        
        fark_menude_var = menu_ilceleri - harita_ilceleri
        fark_haritada_var = harita_ilceleri - menu_ilceleri
        
        if fark_menude_var: print(f"UYARI (Eşleşme Sorunu): Menüde olup haritada olmayan ilçeler: {fark_menude_var}")
        if fark_haritada_var: print(f"UYARI (Eşleşme Sorunu): Haritada olup menüde olmayan ilçeler: {fark_haritada_var}")
        
        if not menu_ilceleri.intersection(harita_ilceleri):
            print("KRİTİK HATA: Menüdeki ilçe adları (örn: 'Çankaya') ile haritadaki ilçe adları (örn: 'CANKAYA') HİÇ EŞLEŞMİYOR!")

    except FileNotFoundError:
        print(f"HATA: Harita dosyası '{GEOJSON_MAP_PATH}' bulunamadı!")
    except Exception as e:
        print(f".shp haritası yüklenirken kritik hata: {e}")
        print("Not: 'fiona' veya 'pyproj' kütüphaneleri eksik olabilir.")


# --- Ana Sayfa ---
@app.route('/')
def index():
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# --- Veri Yükleme (Değişiklik Yok) ---
@app.route('/upload_data', methods=['POST'])
def upload_data():
    global processed_data
    try:
        data_type = request.form['data_type']  
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400
        
        if data_type not in processed_data:
            return jsonify({'success': False, 'error': 'Geçersiz veri tipi.'}), 400

        df = pd.read_csv(file)

        if data_type not in df.columns:
            return jsonify({'success': False, 'error': f'CSV dosyanızda "{data_type}" adında bir sütun bulunamadı.'}), 400

        ortalama_deger = df[data_type].mean()
        processed_data[data_type][ilce] = ortalama_deger

        print(f"KAYIT: Tür={data_type}, İlçe={ilce}, Ortalama={ortalama_deger}")

        return jsonify({
            'success': True,
            'message': f'{ilce} için ortalama {data_type} {ortalama_deger:.2f} olarak kaydedildi.'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Harita Veri API'si (Değişiklik Yok) ---
@app.route('/api/get_map_data/<data_type>')
def get_map_data(data_type):
    global ankara_gdf, processed_data
    
    if ankara_gdf is None:
        print("API Hatası: Harita hafızaya yüklenememiş (ankara_gdf is None).")
        return jsonify({"error": "Harita verisi sunucuda yüklenemedi. .shp dosyasını kontrol edin."}), 500

    try:
        gdf_copy = ankara_gdf.copy()
        varsayilan_renk = '#808080'
        
        if data_type in processed_data:
            data_to_merge = processed_data[data_type]
            df = pd.DataFrame(list(data_to_merge.items()), columns=['ilce', 'ortalama'])
            merged_gdf = gdf_copy.merge(df, on='ilce', how='left')

            if data_type == 'sicaklik':
                def get_color(ortalama):
                    if pd.isna(ortalama): return varsayilan_renk
                    if ortalama > 17: return '#FF0000'
                    if ortalama > 15: return '#FFFF00'
                    return '#0000FF'
                merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)

            elif data_type == 'nem':
                def get_color(ortalama):
                    if pd.isna(ortalama): return varsayilan_renk
                    if ortalama > 70: return '#0000FF'
                    if ortalama > 50: return '#00FF00'
                    return '#FFFF00'
                merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)
                
            elif data_type == 'egim':
                def get_color(ortalama):
                    if pd.isna(ortalama): return varsayilan_renk
                    if ortalama > 20: return '#FF0000'
                    if ortalama > 10: return '#FFFF00'
                    return '#00FF00'
                merged_gdf['renk'] = merged_gdf['ortalama'].apply(get_color)
            
            else:
                 merged_gdf['renk'] = varsayilan_renk

        elif data_type == 'toplama':
            sicaklik_df = pd.DataFrame(list(processed_data['sicaklik'].items()), columns=['ilce', 'sicaklik'])
            nem_df = pd.DataFrame(list(processed_data['nem'].items()), columns=['ilce', 'nem'])
            egim_df = pd.DataFrame(list(processed_data['egim'].items()), columns=['ilce', 'egim'])
            
            merged_gdf = gdf_copy.merge(sicaklik_df, on='ilce', how='left')
            merged_gdf = merged_gdf.merge(nem_df, on='ilce', how='left')
            merged_gdf = merged_gdf.merge(egim_df, on='ilce', how='left')

            def get_toplama_color(row):
                s, n, e = row['sicaklik'], row['nem'], row['egim']
                
                if pd.isna(s) or pd.isna(n) or pd.isna(e):
                    return varsayilan_renk

                score = 0
                if s > 15: score += 1
                if n < 60: score += 1
                if e < 10: score += 1
                
                if score == 3: return '#00FF00'
                if score == 2: return '#FFFF00'
                return '#FF0000'
            
            merged_gdf['renk'] = merged_gdf.apply(get_toplama_color, axis=1)
            merged_gdf['ortalama'] = pd.NA 

        else:
            merged_gdf = gdf_copy
            merged_gdf['renk'] = varsayilan_renk
            merged_gdf['ortalama'] = pd.NA
        
        return merged_gdf.to_json()

    except Exception as e:
        print(f"API Hatası (/get_map_data): {e}")
        return jsonify({"error": str(e)}), 500

# --- SUNUCUYU BAŞLAT ---
if __name__ == '__main__':
    load_district_list_from_json() # 1. Menü listesini yükle
    load_map_file()                # 2. Harita şeklini yükle
    app.run(debug=True)
else:
    load_district_list_from_json()
    load_map_file()
