document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Haritayı Başlat ---
    const map = L.map('map').setView([39.93, 32.85], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let ankaraLayer; 
    let sicaklikData = {}; 

    // --- 2. Stil Fonksiyonu (Değişiklik yok) ---
    function getStyle(feature) {
        const districtName = feature.properties.NAME_3; // (Dosyaya göre 'ilce_adi' vb. olabilir)
        const color = sicaklikData[districtName] || '#999999'; 
        return {
            fillColor: color,
            weight: 2, opacity: 1, color: 'white',
            dashArray: '3', fillOpacity: 0.7
        };
    }

    // --- 3. Ana Harita Verisi Yükleme Fonksiyonu ---
    async function loadMapData() {
        try {
            // 1. Adım: Backend'den mevcut boyama verilerini al (Aynı)
            const dataResponse = await fetch('/get_data');
            const allData = await dataResponse.json();
            sicaklikData = allData.sicaklik || {};

            // ==========================================================
            // DEĞİŞİKLİK BURADA
            // ==========================================================
            // 2. Adım: GeoJSON'u GitHub yerine kendi backend'imizdeki proxy'den yükle
            
            // Eski satır: const geoJsonUrl = 'https://github.com/...';
            // Eski satır: const geoJsonResponse = await fetch(geoJsonUrl);
            
            // Yeni satır:
            const geoJsonResponse = await fetch('/get_map_data_from_github');
            
            if (!geoJsonResponse.ok) {
                // app.py'den gelen hata mesajını al
                const errorData = await geoJsonResponse.json();
                throw new Error(errorData.error || 'Harita dosyası backend\'den çekilemedi.');
            }
            // ==========================================================
            
            const allDistricts = await geoJsonResponse.json();

            // 3. Adım: Haritada eski katman varsa kaldır (Aynı)
            if (ankaraLayer) {
                map.removeLayer(ankaraLayer);
            }
            
            // 4. Adım: GeoJSON'u haritaya ekle (FİLTRELİ - Aynı)
            ankaraLayer = L.geoJson(allDistricts, { 
                
                filter: function(feature) {
                    const provinceName = feature.properties.NAME_1; 
                    return provinceName === "Ankara";
                },
                style: getStyle,
                onEachFeature: (feature, layer) => {
                    const districtName = feature.properties.NAME_3; 
                    layer.bindPopup(districtName); 
                }
            }).addTo(map);

        } catch (error) {
            console.error('Harita verisi yüklenirken hata oluştu:', error);
            alert(`Kritik Hata: ${error.message}`);
        }
    }

    // --- 4. Sayfa Yüklendiğinde Haritayı İlk Kez Yükle (Aynı) ---
    loadMapData();

    // --- 5, 6, 7 (Panel, Tab ve Form mantığı) ---
    // Bu kısımlarda hiçbir değişiklik yok. Tamamen aynı.
    
    const toggleBtn = document.getElementById('admin-toggle-btn');
    const adminPanel = document.getElementById('admin-panel');
    toggleBtn.addEventListener('click', () => {
        adminPanel.classList.toggle('open');
    });

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
                loadMapData(); // Haritayı yeniden çiz
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
