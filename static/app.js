document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Haritayı Başlat ---
    // Ankara'nın merkezi koordinatları ve zoom seviyesi
    const map = L.map('map').setView([39.93, 32.85], 10); 

    // Harita katmanı (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let ankaraLayer; // İlçe katmanını saklamak için global değişken
    let sicaklikData = {}; // Mevcut sıcaklık verilerini (renkleri) saklamak için

    // --- 2. Haritayı Boyamak İçin Stil Fonksiyonu ---
    function getStyle(feature) {
        // !!! GÜNCELLEME GEREKEBİLECEK YER 1 !!!
        // GeoJSON dosyanızdaki ilçe adı özelliğinin adı 'NAME_3' olmayabilir.
        // (Örn: 'ilce_adi', 'district', 'ADM2_TR' vb.)
        const districtName = feature.properties.NAME_3; 
        
        // Backend'den gelen veriye göre rengi belirle, veri yoksa gri yap
        const color = sicaklikData[districtName] || '#999999'; 

        return {
            fillColor: color,
            weight: 2,        // Sınır çizgisi kalınlığı
            opacity: 1,
            color: 'white',   // Sınır çizgisi rengi
            dashArray: '3',   // Sınır çizgisi stili
            fillOpacity: 0.7  // Dolgu opaklığı
        };
    }

    // --- 3. Ana Harita Verisi Yükleme Fonksiyonu ---
    async function loadMapData() {
        try {
            // 1. Adım: Backend'den mevcut verileri (renkleri) al
            const dataResponse = await fetch('/get_data');
            const allData = await dataResponse.json();
            sicaklikData = allData.sicaklik || {};

            // 2. Adım: Tüm Türkiye GeoJSON dosyasını yükle
            // (Dosyanın adını 'turkey-districts.geojson' olarak varsayıyoruz)
            const geoJsonResponse = await fetch('/turkey-districts.geojson');
            const allDistricts = await geoJsonResponse.json();

            // 3. Adım: Haritada eski katman varsa kaldır (güncelleme için)
            if (ankaraLayer) {
                map.removeLayer(ankaraLayer);
            }
            
            // 4. Adım: GeoJSON'u haritaya ekle (FİLTRELİ)
            ankaraLayer = L.geoJson(allDistricts, { 
                
                // -------- SADECE ANKARA'YI GÖSTERME FİLTRESİ --------
                filter: function(feature) {
                    // !!! GÜNCELLEME GEREKEBİLECEK YER 2 !!!
                    // İl (province) adını içeren özelliğin adı 'NAME_1' olmayabilir.
                    // (Örn: 'il_adi', 'province', 'ADM1_TR' vb.)
                    const provinceName = feature.properties.NAME_1; 
                    return provinceName === "Ankara";
                },
                // ----------------------------------------------------

                // Her ilçe için stili belirle
                style: getStyle,
                
                // Her ilçeye tıklandığında popup ekle
                onEachFeature: (feature, layer) => {
                    // !!! GÜNCELLEME GEREKEBİLECEK YER 3 !!!
                    // (Yukarıdaki 'NAME_3' ile aynı olmalı)
                    const districtName = feature.properties.NAME_3;
                    layer.bindPopup(districtName); // İlçeye tıklayınca adını göster
                }
            }).addTo(map);

        } catch (error) {
            console.error('Harita verisi yüklenirken hata oluştu:', error);
            alert("Hata: 'turkey-districts.geojson' dosyası bulunamadı veya okunamadı. Lütfen dosyanın ana dizinde olduğundan emin olun.");
        }
    }

    // --- 4. Sayfa Yüklendiğinde Haritayı İlk Kez Yükle ---
    loadMapData();


    // --- 5. Kontrol Paneli Açma/Kapatma Mantığı ---
    const toggleBtn = document.getElementById('admin-toggle-btn');
    const adminPanel = document.getElementById('admin-panel');
    toggleBtn.addEventListener('click', () => {
        adminPanel.classList.toggle('open');
    });

    // --- 6. Kontrol Paneli İçi Tab Değiştirme Mantığı ---
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab; // 'data-tab' özelliğini al

            // Tüm içerikleri gizle ve linklerin 'active' durumunu kaldır
            tabContents.forEach(content => content.classList.remove('active'));
            tabLinks.forEach(link => link.classList.remove('active'));

            // Sadece tıklananı aktif et
            document.getElementById(tabId).classList.add('active');
            e.target.classList.add('active');
        });
    });

    // --- 7. Sıcaklık Formu Gönderme (Submit) Mantığı ---
    const sicaklikForm = document.getElementById('sicaklik-form');
    const sicaklikStatus = document.getElementById('sicaklik-status');

    sicaklikForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Sayfanın yeniden yüklenmesini engelle
        sicaklikStatus.textContent = 'Yükleniyor...';
        sicaklikStatus.style.color = 'black';

        // Form verilerini al (ilçe adı ve CSV dosyası)
        const formData = new FormData(sicaklikForm);

        try {
            // Veriyi Backend'e (/upload/sicaklik) gönder
            const response = await fetch('/upload/sicaklik', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) { // HTTP 200-299 arası
                sicaklikStatus.textContent = `Başarılı: ${result.district} için ortalama ${result.avg_temp.toFixed(2)}°C olarak kaydedildi.`;
                sicaklikStatus.style.color = 'green';
                
                // Haritayı yeni renklerle yeniden çizmek için ana fonksiyonu tekrar çağır
                loadMapData(); 
                
                // Formu temizle (isteğe bağlı)
                sicaklikForm.reset();
            } else {
                // Sunucudan gelen hatayı (örn: 'sıcaklık sütunu bulunamadı') göster
                sicaklikStatus.textContent = `Hata: ${result.message}`;
                sicaklikStatus.style.color = 'red';
            }
        } catch (error) {
            // Sunucuya ulaşılamazsa (örn: Flask çalışmıyorsa)
            sicaklikStatus.textContent = `Sunucu hatası: ${error.message}`;
            sicaklikStatus.style.color = 'red';
        }
    });
});
