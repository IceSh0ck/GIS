document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Haritayı Başlat ---
    // Ankara koordinatları
    const map = L.map('map').setView([39.93, 32.85], 10); 

    // Harita katmanı (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let ankaraLayer; // İlçe katmanını saklamak için değişken
    let sicaklikData = {}; // Sıcaklık verilerini saklamak için

    // --- 2. GeoJSON Katmanını Yükle ve Çiz ---

    // Haritayı boyamak için stil fonksiyonu
    function getStyle(feature) {
        // GeoJSON dosyanızdaki ilçe adı özelliğinin adı 'ilce_adi' olmayabilir.
        // Dosyayı inceleyip doğru özelliği bulmalısınız (Örn: 'NAME_2', 'district', 'ilce' vb.)
        const districtName = feature.properties.NAME_3; // BU KISMI GÜNCELLEMENİZ GEREKEBİLİR
        
        const color = sicaklikData[districtName] || '#999999'; // Veri varsa rengi al, yoksa gri yap

        return {
            fillColor: color,
            weight: 2,
            opacity: 1,
            color: 'white',
            dashArray: '3',
            fillOpacity: 0.7
        };
    }

    // İlçe katmanını yükleyen ve güncelleyen ana fonksiyon
    async function loadMapData() {
        try {
            // 1. Adım: Backend'den mevcut verileri (renkleri) al
            const dataResponse = await fetch('/get_data');
            const allData = await dataResponse.json();
            sicaklikData = allData.sicaklik || {};

            // 2. Adım: GeoJSON dosyasını yükle
            const geoJsonResponse = await fetch('/ankara-ilceler.geojson');
            const ankaraDistricts = await geoJsonResponse.json();

            // Haritada eski katman varsa kaldır
            if (ankaraLayer) {
                map.removeLayer(ankaraLayer);
            }
            
            // 3. Adım: GeoJSON'u haritaya ekle ve 'getStyle' fonksiyonu ile boya
            ankaraLayer = L.geoJson(ankaraDistricts, { 
                style: getStyle,
                onEachFeature: (feature, layer) => {
                    // İlçelerin üzerine gelince ilçe adını göster
                    const districtName = feature.properties.NAME_3; // BU KISMI GÜNCELLEMENİZ GEREKEBİLİR
                    layer.bindPopup(districtName);
                }
            }).addTo(map);

        } catch (error) {
            console.error('Harita verisi yüklenirken hata oluştu:', error);
            alert("Hata: ankara-ilceler.geojson dosyası bulunamadı veya okunamadı. Lütfen dosyanın ana dizinde olduğundan emin olun.");
        }
    }

    // Sayfa yüklendiğinde haritayı ilk kez yükle
    loadMapData();


    // --- 3. Kontrol Paneli Mantığı ---

    // Panel açma/kapatma
    const toggleBtn = document.getElementById('admin-toggle-btn');
    const adminPanel = document.getElementById('admin-panel');
    toggleBtn.addEventListener('click', () => {
        adminPanel.classList.toggle('open');
    });

    // Panel içi tab (Sıcaklık, Nem, Eğim) değiştirme
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab;

            // Tüm içerikleri gizle, tüm linklerin 'active' class'ını kaldır
            tabContents.forEach(content => content.classList.remove('active'));
            tabLinks.forEach(link => link.classList.remove('active'));

            // Sadece tıklananı göster
            document.getElementById(tabId).classList.add('active');
            e.target.classList.add('active');
        });
    });

    // --- 4. Sıcaklık Formu Gönderme (Submit) Mantığı ---
    const sicaklikForm = document.getElementById('sicaklik-form');
    const sicaklikStatus = document.getElementById('sicaklik-status');

    sicaklikForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Sayfanın yeniden yüklenmesini engelle
        sicaklikStatus.textContent = 'Yükleniyor...';

        const formData = new FormData(sicaklikForm);

        try {
            const response = await fetch('/upload/sicaklik', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                sicaklikStatus.textContent = `Başarılı: ${result.district} için ortalama sıcaklık ${result.avg_temp.toFixed(2)}°C olarak kaydedildi. Renk: ${result.color}`;
                // Haritayı yeni renklerle yeniden çiz
                loadMapData(); 
            } else {
                sicaklikStatus.textContent = `Hata: ${result.message}`;
            }
        } catch (error) {
            sicaklikStatus.textContent = `Sunucu hatası: ${error.message}`;
        }
    });
});
