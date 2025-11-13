from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import json # JSON dosyasını okumak için eklendi

app = Flask(__name__)

# --- Sunucu Hafızası ---
# Yüklenen verileri (Sıcaklık, Nem, Eğim) burada saklayacağız
processed_data = {
    "sicaklik": {}, # örn: {"Çankaya": 15.5, "Akyurt": 16.2}
    "nem": {},
    "egim": {}
}

# --- İlçe Listesi (Artık JSON'dan Okunacak) ---
ANKARA_ILCELERI = [] # Başlangıçta boş

def load_district_list_from_json():
    """
    Haritadan bağımsız olarak, SADECE menü için
    'static/il-ilce-listesi.json' dosyasından Ankara ilçelerini okur.
    """
    global ANKARA_ILCELERI
    json_path = os.path.join('static', 'il-ilce-listesi.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if "Ankara" in data:
                # JSON'dan listeyi al
                ANKARA_ILCELERI = sorted(data["Ankara"])
                
                # Not: JSON listende "Kazan" var, haritalarda genelde "Kahramankazan" olur.
                # Şimdilik JSON'daki listeyi birebir kullanıyoruz.
                # (Eğer harita dosyasındaki ad "Kahramankazan" ise burayı düzeltmemiz gerekecek)
                
                print(f"Başarılı: Menü için {len(ANKARA_ILCELERI)} ilçe JSON'dan yüklendi.")
            else:
                print(f"HATA: '{json_path}' dosyasında 'Ankara' anahtarı bulunamadı.")
    
    except FileNotFoundError:
        print(f"HATA: '{json_path}' dosyası bulunamadı!")
        print("Lütfen bir önceki mesajdaki JSON listesini bu yola kaydettiğinizden emin olun.")
    except Exception as e:
        print(f"JSON yüklenirken kritik hata: {e}")

# Ana sayfayı yükler ve ilçe listesini HTML'e gönderir
@app.route('/')
def index():
    # Artık ANKARA_ILCELERI listesi JSON'dan dolu olmalı
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# GÜNCELLENDİ: Tüm 3 veri tipini de işler ve hafızaya kaydeder
@app.route('/upload_data', methods=['POST'])
def upload_data():
    global processed_data
    try:
        data_type = request.form['data_type']  # (sicaklik, nem, egim)
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400
        
        # Gelen veri tipinin (sicaklik, nem, egim) bizim hafızamızda yeri var mı?
        if data_type not in processed_data:
            return jsonify({'success': False, 'error': 'Geçersiz veri tipi.'}), 400

        df = pd.read_csv(file)

        # CSV'de 'data_type' ile aynı isimde sütun arayacağız
        # (Yani 'sicaklik.csv'de 'sicaklik' sütunu, 'nem.csv'de 'nem' sütunu olmalı)
        if data_type not in df.columns:
            return jsonify({'success': False, 'error': f'CSV dosyanızda "{data_type}" adında bir sütun bulunamadı.'}), 400

        # Ortalama değeri hesapla
        ortalama_deger = df[data_type].mean()

        # Değeri sunucu hafızasına kaydet
        # örn: processed_data['sicaklik']['Çankaya'] = 15.5
        processed_data[data_type][ilce] = ortalama_deger

        print(f"KAYIT: Tür={data_type}, İlçe={ilce}, Ortalama={ortalama_deger}")
        # Hafızanın son halini görmek için:
        # print(f"Tüm Veri: {processed_data}")

        return jsonify({
            'success': True,
            'message': f'{ilce} için ortalama {data_type} {ortalama_deger:.2f} olarak kaydedildi.'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Sunucuyu Başlat ---
if __name__ == '__main__':
    load_district_list_from_json() # Sunucu başlarken menü listesini yükle
    app.run(debug=True)
else:
    # Render.com (Gunicorn) için de listeyi yükle
    load_district_list_from_json()
