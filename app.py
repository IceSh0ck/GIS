from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import requests # API/URL isteği için geri eklendi

app = Flask(__name__)

data_storage = {
    "sicaklik": {}
}

# ==========================================================
# YENİ EKLENEN PROXY ADRESİ
# ==========================================================
@app.route('/get_map_data_from_github')
def get_map_data_from_github():
    """
    Frontend'in CORS hatası almaması için bir proxy görevi görür.
    GeoJSON dosyasını GitHub Release'den çeker ve frontend'e iletir.
    """
    
    # 1. Adımda kopyaladığınız GitHub Release linkini buraya yapıştırın
    github_url = 'https://github.com/KULLANICI_ADINIZ/PROJE_ADINIZ/releases/download/v1.0-data/turkey-districts.geojson'
    
    try:
        # Python sunucusu GitHub'dan veriyi çeker
        response = requests.get(github_url, timeout=15)
        response.raise_for_status() # Hata varsa (404 vb.) exception fırlat
        
        # Gelen veriyi (GeoJSON) doğrudan frontend'e (app.js) ilet
        return response.json() 
        
    except requests.RequestException as e:
        print(f"GitHub Release Hatası: {e}")
        return jsonify({"error": "Harita dosyası GitHub'dan çekilemedi."}), 502
# ==========================================================


@app.route('/')
def index():
    """Ana HTML sayfasını sunar."""
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    """Haritanın yüklenmesi için mevcut boyama verilerini gönderir."""
    return jsonify(data_storage)

@app.route('/upload/sicaklik', methods=['POST'])
def upload_sicaklik():
    # ... (Bu fonksiyonun geri kalanı aynı, değişiklik yok) ...
    
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
        
        color = "#FFFFFF" 
        if average_temp > 17:
            color = "#FF0000"
        elif average_temp > 15:
            color = "#FFFF00"
        else:
            color = "#0000FF"
            
        data_storage["sicaklik"][district_name] = color
        
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
