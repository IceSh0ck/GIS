document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Haritayı Başlat ---
    const map = L.map('map').setView([39.93, 32.85], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let ankaraLayer; 
    let sicaklikData = {}; 

    // --- 2. Haritayı Boyamak İçin Stil Fonksiyonu ---
    function getStyle(feature) {
        // DEĞİŞTİ: API'den gelen veride ilçe adı 'text' özelliğindedir.
        const districtName = feature.properties.text; 
        
        const color = sicaklikData[districtName] || '#999999'; // Veri yoksa gri yap

        return {
            fillColor: color,
            weight: 2,
            opacity: 1,
            color: 'white',
            dashArray: '3',
            fillOpacity: 0.7
        };
    }

    // --- YENİ FONKSİYON: İlçe Seçim Menüsünü Doldurur ---
    function populateDistrictDropdown(features) {
        const selectMenu = document.getElementById('district-select-sicaklik');
        selectMenu.innerHTML = ''; // Menüyü temizle ("Yükleniyor..." yazısını kaldır)

        // API'den gelen her ilçe için bir <option> oluştur
        features.forEach(feature => {
            const districtName = feature.properties.text;
            const option = document.createElement('option');
            option.value = districtName;
            option.textContent = districtName;
            selectMenu.appendChild(option);
        });
    }

    // --- 3. Ana Harita Verisi Yükleme Fonksiyonu ---
    async function loadMapData() {
        try {
            // 1. Adım: Backend'den mevcut boyama verilerini (renkleri) al
            const dataResponse = await fetch('/get_data');
            const allData = await dataResponse.json();
            sicaklikData = allData.sicaklik || {};

            // 2. Adım: GeoJSON'u statik dosya yerine BİZİM BACKEND'imizden yükle
            const geoJsonResponse = await fetch('/get_ankara_map');
            
            if (!geoJsonResponse.ok) {
                // Backend'den (örn: TKGM API hatası) bir hata geldiyse
                const errorData = await geoJsonResponse.json();
                throw new Error(errorData.error || 'Harita verisi alınamadı.');
            }
            
            const ankaraDistricts = await geoJsonResponse.json();

            // 3. Adım: Haritada eski katman varsa kaldır
            if (ankaraLayer) {
                map.removeLayer(ankaraLayer);
            }
            
            // 4. Adım: GeoJSON'u haritaya ekle
            ankaraLayer = L.geoJson(ankaraDistricts, { 
                
                // DEĞİŞTİ: 'filter' bölümü SİLİNDİ
                // (Artık gerek yok, çünkü API'den sadece Ankara geliyor)

                style: getStyle,
                
                onEachFeature: (feature, layer) => {
                    // DEĞİŞTİ: İlçe adı 'text' özelliğinden geliyor
                    const districtName = feature.properties.text;
                    layer.bindPopup(districtName); 
                }
            }).addTo(map);

            // 5. Adım (YENİ): İlçe seçim menüsünü API'den gelen verilerle doldur
            populateDistrictDropdown(ankaraDistricts.features);

        } catch (error) {
            console.error('Harita verisi yüklenirken hata oluştu:', error);
            alert(`Kritik Hata: ${error.message}`);
        }
    }

    // --- 4. Sayfa Yüklendiğinde Haritayı İlk Kez Yükle ---
    loadMapData();


    // --- 5. Kontrol Paneli Açma/Kapatma Mantığı (Değişiklik yok) ---
    const toggleBtn = document.getElementById('admin-toggle-btn');
    const adminPanel = document.getElementById('admin-panel');
    toggleBtn.addEventListener('click', () => {
        adminPanel.classList.toggle('open');
    });

    // --- 6. Kontrol Paneli İçi Tab Değiştirme Mantığı (Değişiklik yok) ---
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab; 
            tabContents.forEach(content => content.classList.remove('active'));
            tabLinks.forEach(link => link.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            e.target.classList.add('active');
        });
    });

    // --- 7. Sıcaklık Formu Gönderme (Submit) Mantığı (Değişiklik yok) ---
    const sicaklikForm = document.getElementById('sicaklik-form');
    const sicaklikStatus = document.getElementById('sicaklik-status');

    sicaklikForm.addEventListener('submit', async (e) => {
        e.preventDefault(); 
        sicaklikStatus.textContent = 'Yükleniyor...';
        sicaklikStatus.style.color = 'black';

        const formData = new FormData(sicaklikForm);

        try {
            const response = await fetch('/upload/sicaklik', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) { 
                sicaklikStatus.textContent = `Başarılı: ${result.district} için ortalama ${result.avg_temp.toFixed(2)}°C olarak kaydedildi.`;
                sicaklikStatus.style.color = 'green';
                
                // Haritayı yeni renklerle yeniden çiz
                loadMapData(); 
                
                sicaklikForm.reset();
            } else {
                sicaklikStatus.textContent = `Hata: ${result.message}`;
                sicaklikStatus.style.color = 'red';
            }
        } catch (error) {
            sicaklikStatus.textContent = `Sunucu hatası: ${error.message}`;
            sicaklikStatus.style.color = 'red';
        }
    });
});
