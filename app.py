from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

# Geçici olarak Ankara ilçelerinin bir listesi
# Tam bir CBS sistemi için bu, bir GeoJSON dosyasından gelmelidir
ANKARA_ILCELERI = [
    "Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere",
    "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı",
    "Güdül", "Haymana", "Kahramankazan", "Kalecik", "Keçiören", "Kızılcahamam",
    "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"
]

# Ana sayfayı yükler ve ilçe listesini HTML'e gönderir
@app.route('/')
def index():
    return render_template('index.html', ilceler=ANKARA_ILCELERI)

# Kontrol panelinden gelen veri yükleme işlemini yönetir
@app.route('/upload_data', methods=['POST'])
def upload_data():
    try:
        data_type = request.form['data_type']  # (Sıcaklık, Nem, Eğim)
        ilce = request.form['ilce']
        file = request.files['file']

        if not file:
            return jsonify({'success': False, 'error': 'Dosya seçilmedi.'}), 400

        # Şu an için sadece 'Sıcaklık' işlemesini yapıyoruz
        if data_type == 'sicaklik':
            # Dosyayı oku ( birden fazla dosya için mantık genişletilmeli)
            df = pd.read_csv(file)

            # --- Sizin "Sıcaklık Yapay Zekası" (Gerçekte Veri İşleme) ---
            # CSV'de 'yıl', 'ay', 'sicaklik' sütunları olduğunu varsayıyoruz
            if 'sicaklik' not in df.columns:
                return jsonify({'success': False, 'error': '"sicaklik" sütunu bulunamadı.'}), 400

            # Yüklenen dosyadaki verilerin genel ortalamasını al
            genel_ortalama = df['sicaklik'].mean()

            # Sizin kuralınıza göre renklendirme mantığı
            renk = "beyaz" # Varsayılan
            if genel_ortalama > 17:
                renk = "kırmızı"
            elif genel_ortalama > 15:
                renk = "sarı"
            else:
                renk = "mavi" # Örnek

            # Normalde bu veri (ilce, renk, ortalama) bir veritabanına kaydedilir
            # ve haritanın güncellenmesi için bir sinyal gönderilir.
            # Şimdilik sadece başarılı bir yanıt döndürüyoruz.

            print(f"İŞLEM BAŞARILI: İlçe={ilce}, Tür={data_type}, Ortalama={genel_ortalama}, Renk={renk}")

            return jsonify({
                'success': True,
                'message': f'{ilce} ilçesi için {data_type} verisi işlendi. Ortalama: {genel_ortalama:.2f}°C. Harita rengi: {renk}'
            })

        else:
            # Nem ve Eğim için işlemciler daha sonra eklenecek
            return jsonify({'success': True, 'message': f'{data_type} için işlemci henüz tanımlanmadı.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
