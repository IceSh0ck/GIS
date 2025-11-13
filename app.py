from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import requests # API'ye bağlanmak için eklendi

app = Flask(__name__)

# Veritabanı yerine basit bir Python sözlüğü (dictionary)
data_storage = {
    "sicaklik": {}
}

@app.route('/')
def index():
    """Ana HTML sayfasını sunar."""
    return render_template('index.html')

# ==========================================================
# YENİ EKLENEN API ADRESİ
# ==========================================================
@app.route('/get_ankara_map')
def get_ankara_map():
    """
    TKGM'nin resmi API'sinden Ankara ilçe sınırlarını (GeoJSON) çeker.
    """
    # Sizin bulduğunuz API adresi (Ankara'nın ID'si 6)
    api_url = "https://cbsservis.tkgm.gov.tr/megsiswebapi.v3/api/idariYapi/ilceListe/6"
    
    # Sizin Postman'den aldığınız header bilgileri
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    }
    
    try:
        # API'ye isteği gönder
        response = requests.get(api_url, headers=headers, timeout=10)
        # Bir hata oluşursa (404, 500 vb.) exception fırlat
        response.raise_for_status() 
        
        # Gelen GeoJSON verisini doğrudan frontend'e (app.js) ilet
        return response.json() 
        
    except requests.RequestException as e:
        print(f"TKGM API Hatası: {e}")
        return jsonify({"error": "Harita servisine ulaşılamadı. Lütfen daha sonra tekrar deneyin."}), 502

# ==========================================================

@app.route('/get_data')
def get_data():
    """Haritanın yüklenmesi için mevcut boyama verilerini gönderir."""
    return jsonify(data_storage)

@app.route('/upload/sicaklik', methods=['POST'])
def upload_sicaklik():
    """
    Sıcaklık "Yapay Zekası" (Veri İşleme)
    """
    if 'csv_file' not in request.files:
        return jsonify({"status": "error", "message": "Dosya bulunamadı"}), 400
    
    file = request.files['csv_file']
    district_name = request.form['districtName']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "Dosya seçilmedi"}), 400

    try:
        df = pd.read_csv(file.stream)
        
        if 'sıcaklık' not in df.columns:
            return jsonify({"status": "error", "message": "CSV'de 'sıcaklık' sütunu bulunamadı."}), 400
            
        average_temp = df['sıcaklık'].mean()
        
        # Rengi belirle
        color = "#FFFFFF" 
        if average_temp > 17:
            color = "#FF0000" # Kırmızı
        elif average_temp > 15:
            color = "#FFFF00" # Sarı
        else:
            color = "#0000FF" # Mavi (Örnek)
            
        # Veriyi sakla
        data_storage["sicaklik"][district_name] = color
        
        print(f"İşlem tamam: {district_name}, Ortalama: {average_temp}, Renk: {color}")
        
        return jsonify({
            "status": "success", 
            "district": district_name, 
            "avg_temp": average_temp,
            "color": color
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
