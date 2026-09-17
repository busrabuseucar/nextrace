# NexTrace AI

NexTrace AI, kritik mühendislik projelerinde bir değişikliğin gereksinim, kod, test ve dokümanlar üzerindeki etkisini açıklanabilir kanıt zincirleriyle görünür kılmayı hedefleyen karar destek yazılımıdır.

![NexTrace AI çalışan demo ekranı](docs/nextrace-dashboard.png)

## Mevcut sürüm

Bu depo, ürün fikrini ve temel kullanıcı akışını doğrulamak için hazırlanmış **çalışan sentetik veri demosunu** içerir. Henüz gerçek kurum sistemlerine bağlanan üretim sürümü veya doğrulanmış müşteri pilotu değildir.

Demoda üç örnek değişiklik senaryosu bulunur:

- Telemetri gecikme eşiğinin değiştirilmesi
- Şifreleme standardının yükseltilmesi
- Sensör örnekleme sıklığının artırılması

Kullanıcı bir senaryo seçip etki analizini çalıştırdığında sistem:

- Etkilenen mühendislik varlıklarını,
- Kritik, yüksek ve orta düzey riskleri,
- Gereksinimden kod, test ve dokümana uzanan kanıt yollarını,
- İnceleme ve denetim günlüğünü

görselleştirir.

## Çalıştırma

Proje herhangi bir derleme adımı gerektirmeyen statik bir web uygulamasıdır.

1. Depoyu indir veya klonla.
2. Proje klasöründe basit bir yerel sunucu başlat:

   ```bash
   python -m http.server 8000
   ```

3. Tarayıcıda `http://localhost:8000` adresini aç.

## Dosya yapısı

```text
.
├── index.html
├── styles.css
├── app.js
├── docs/
│   └── nextrace-dashboard.png
└── assets/
    ├── nextrace-architecture.svg
    └── nextrace-architecture.png
```

## Planlanan MVP kapsamı

- CSV/Excel üzerinden gereksinim, kod, test ve doküman verisi alma
- Kaynak varlıklar arasında sürümlü izlenebilirlik grafiği oluşturma
- Yeni değişiklik talepleri için dinamik etki ve risk analizi
- Sonuçların gerekçesiyle ve kaynak yoluyla gösterilmesi
- Kanıt raporunun dışa aktarılması
- Kurum içi veya özel bulut kurulumu

## Güvenlik ve veri yaklaşımı

Hedef ürün, müşteri verilerini müşteri ortamında tutacak şekilde kurum içi veya özel bulut kurulumu için tasarlanmaktadır. Bu depodaki bütün örnekler sentetik veridir ve gerçek kurum verisi içermez.

## Fikri mülkiyet

Bu proje açık kaynak lisansı altında yayımlanmamıştır. Tüm hakları saklıdır. Kaynak kodun kullanılması, kopyalanması, dağıtılması veya türev çalışmalarda kullanılması için hak sahibinden yazılı izin alınmalıdır.
