# NexTrace AI

NexTrace AI, kritik mühendislik projelerinde bir değişikliğin gereksinim, kod, test ve dokümanlar üzerindeki etkisini açıklanabilir kanıt zincirleriyle görünür kılmayı hedefleyen karar destek yazılımıdır.

![NexTrace AI çalışan demo ekranı](docs/nextrace-dashboard.png)

## Mevcut sürüm — çalışan MVP temeli

Bu depo, ürün fikrini ve temel kullanıcı akışını doğrulayan **dinamik etki analizi motoru ile çalışan MVP temelini** içerir. Arayüz artık hazır sonuçları taklit etmez; Python API, yüklenen izlenebilirlik grafiğini tarayarak etkilenen varlıkları, kanıt yollarını ve risk puanlarını hesaplar. Projeler ve analiz geçmişi SQLite veritabanında kalıcı olarak tutulur. Henüz gerçek kurum sistemlerine doğrudan bağlanan üretim sürümü veya doğrulanmış müşteri pilotu değildir.

Demoda üç örnek değişiklik senaryosu bulunur:

- Telemetri gecikme eşiğinin değiştirilmesi
- Şifreleme standardının yükseltilmesi
- Sensör örnekleme sıklığının artırılması

Kullanıcı örnek senaryolardan birini seçebilir veya kendi düğüm/ilişki CSV dosyalarını yükleyebilir. Analiz çalıştırıldığında sistem:

- Etkilenen mühendislik varlıklarını,
- Kritik, yüksek ve orta düzey riskleri,
- Gereksinimden kod, test ve dokümana uzanan kanıt yollarını,
- İnceleme ve denetim günlüğünü

görselleştirir.

## Çalıştırma

Proje üçüncü taraf paket gerektirmeyen Python API ve web arayüzünden oluşur. Python 3.10 veya üzeri önerilir.

1. Depoyu indir veya klonla.
2. Proje klasöründe basit bir yerel sunucu başlat:

   ```bash
   python backend/server.py
   ```

3. Tarayıcıda `http://localhost:8000` adresini aç.
4. İlk açılışta yönetici e-posta adresini ve en az 12 karakterli parolanı belirle. Sonraki erişimlerde bu hesapla giriş yap.

## Dosya yapısı

```text
.
├── index.html
├── styles.css
├── app.js
├── backend/
│   ├── server.py
│   ├── engine.py
│   ├── auth.py
│   ├── storage.py
│   └── data/
│       ├── nodes.csv
│       └── edges.csv
├── tests/
│   ├── test_auth.py
│   ├── test_engine.py
│   └── test_storage.py
├── docs/
│   └── nextrace-dashboard.png
└── assets/
    ├── nextrace-architecture.svg
    └── nextrace-architecture.png
```

## CSV veri şeması

`nodes.csv` sütunları:

```text
id,label,type,owner,criticality
```

`edges.csv` sütunları:

```text
source,target,relation,reason
```

Örnek dosyalar `backend/data/` klasöründedir. Web arayüzünde iki dosyayı seçtikten sonra analiz başlangıcı olacak düğüm kimliğini yazıp grafiği yükleyebilirsin.

## API

- `GET /api/health`: servis ve demo grafiği durumu
- `GET /api/auth/status`: ilk kurulum ve oturum durumu
- `GET /api/projects`: kalıcı proje listesi ve grafik büyüklükleri
- `GET /api/analyses?project_id=demo`: kayıtlı analiz geçmişi
- `POST /api/auth/setup`: yalnızca ilk yönetici hesabını oluşturma
- `POST /api/auth/login`: güvenli oturum açma
- `POST /api/auth/logout`: oturumu sonlandırma
- `POST /api/projects/import`: CSV metinlerinden kalıcı proje grafiği oluşturma
- `POST /api/analyze`: seçilen düğümden dinamik etki analizi çalıştırma

## Test

```bash
python -m unittest discover -s tests -v
```

## Sonraki ürünleştirme adımları

- Jira, GitLab ve test yönetim araçları için gerçek bağlayıcılar
- Proje grafiği sürümleme ve değişiklik karşılaştırma
- Çok kullanıcılı rol ve proje bazlı yetkilendirme
- Müşteri verisiyle doğrulanan risk modeli
- Kurum içi veya özel bulut kurulumu

## Güvenlik ve veri yaklaşımı

Hedef ürün, müşteri verilerini müşteri ortamında tutacak şekilde kurum içi veya özel bulut kurulumu için tasarlanmaktadır. Bu depodaki bütün örnekler sentetik veridir ve gerçek kurum verisi içermez.

- Parolalar PBKDF2-HMAC-SHA256 ve kullanıcıya özel rastgele salt ile saklanır.
- Oturum belirteçlerinin yalnızca SHA-256 özeti veritabanına yazılır.
- Oturum çerezi `HttpOnly` ve `SameSite=Strict` özelliklerini kullanır.
- Giriş denemeleri IP başına sınırlandırılır.
- Proje ve analiz API'leri kimlik doğrulama olmadan kullanılamaz.

HTTPS arkasındaki üretim kurulumunda güvenli çerez zorunluluğunu etkinleştir:

```bash
NEXTRACE_SECURE_COOKIES=1 python backend/server.py
```

## Fikri mülkiyet

Bu proje açık kaynak lisansı altında yayımlanmamıştır. Tüm hakları saklıdır. Kaynak kodun kullanılması, kopyalanması, dağıtılması veya türev çalışmalarda kullanılması için hak sahibinden yazılı izin alınmalıdır.
