from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# Veritabanı yerine basit bir Python sözlüğü (dictionary) kullanacağız.
# Sunucu yeniden başladığında bu veriler sıfırlanır.
# (Gerçek bir proje için Supabase veya başka bir DB kullanmalısınız)
data_storage = {
    "sicaklik": {}
}

@app.route('/')
def index():
    """Ana HTML sayfasını sunar."""
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    """Haritanın yüklenmesi için mevcut verileri gönderir."""
    return jsonify(data_storage)

@app.route('/upload/sicaklik', methods=['POST'])
def upload_sicaklik():
    """
    Sıcaklık "Yapay Zekası" (Veri İşleme)
    CSV dosyasını alır, ortalamayı hesaplar ve rengi belirler.
    """
    if 'csv_file' not in request.files:
        return jsonify({"status": "error", "message": "Dosya bulunamadı"}), 400
    
    file = request.files['csv_file']
    district_name = request.form['districtName']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "Dosya seçilmedi"}), 400

    try:
        # CSV dosyasını Pandas ile oku
        # Birden fazla dosya yükleneceği için mevcut veriyi de hesaba katalım (şimdilik basitçe üzerine yazıyoruz)
        # Siz burada birden fazla CSV'yi birleştirip ortalamasını alabilirsiniz.
        df = pd.read_csv(file.stream)
        
        # 'sıcaklık' sütununun ortalamasını al
        if 'sıcaklık' not in df.columns:
            return jsonify({"status": "error", "message": "CSV'de 'sıcaklık' sütunu bulunamadı."}), 400
            
        average_temp = df['sıcaklık'].mean()
        
        # Rengi belirle (istediğiniz kurala göre)
        color = "#FFFFFF" # Varsayılan (Beyaz)
        if average_temp > 17:
            color = "#FF0000" # Kırmızı
        elif average_temp > 15:
            color = "#FFFF00" # Sarı
        else:
            color = "#0000FF" # Mavi
            
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
    # OnRender'ın ihtiyaç duyacağı port ayarı
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

