# İşletim ve sürüm doğrulama — Graf tabanlı mühendislik etki analizi

Son inceleme: **16 Ekim 2026**. Bu belge kurulum, veri akışı, sürüm kapıları, geri dönüş ve doğrulama kapsamını birlikte kaydeder. Bir yayın adresinin açılması, tüm üretim koşullarının tamamlandığı anlamına gelmez.

## Sürüm kanıtı

- Denetlenen uygulama commit’i: `3c7d65b3428022dabb8fd8637448242afc25c4ba`.
- [Bu commit için başarılı CI kaydı](https://github.com/busrabuseucar/nextrace/actions/runs/38902092388).
- Doğrulanan otomatik kapsam: 29 Python + 1 tarayıcı akışı.
- Testlerin gerçek servis, veri veya donanım yerine taklit kullandığı noktalar aşağıda açıkça ayrılmıştır.

## Kurulum ve çalışma

Depo kökünde, README’deki çalışma zamanı sürümüyle:

```sh
python -m unittest discover -s tests -v
python backend/server.py
```

Veri akışı: Proje yetkili oturum → SQLite graf sürümü → derinliği sınırlı BFS → açıklanabilir risk ve analiz kaydı.

Yapılandırma: Jira URL/e-posta/token ve GitLab URL/token yalnızca sunucu ortamında. Değerler .env dosyasından otomatik okunmaz. HTTPS ve genel ağ sınırı korunmalı.

## Yayın ve geri dönüş

1. Temiz checkout ve kilitli bağımlılıklarla yukarıdaki kontrolleri çalıştır. İlgili CI başarısını commit SHA ile eşleştir.
2. Yayın paketine yalnızca çalışma zamanı dosyalarını koy. Secret, ham kullanıcı verisi, yerel veritabanı ve kişisel hazırlık notları pakete girmemeli.
3. Hedef proje, kaynak commit, ortam ve yayın sürümünü kaydet. Önceki çalışan sürüm kimliğini geri dönüş için koru.
4. Yayından sonra ana kullanıcı akışını, hata durumunu ve varsa kalıcılığı doğrula. Sunucu hatası/yanlış sonuçta yeni yazmaları durdur; önceki doğrulanmış yayını geri al.
5. Şema değiştiyse yalnızca kodu geri almak yeterli değildir. Yedekten ayrı ortamda doğrulama yapmadan canlı veri üzerine yazma.

## Veri saklama ve kurtarma

SQLite tutarlı backup API kopyası; ayrı ortamda integrity_check ve proje/kullanıcı/graf/analiz sayımları. Geri yüklemeyi canlı dosyanın üzerine deneme. Yeni migration gerekiyorsa geri dönüş uyumluluğunu doğrula.

## Gerçek servis, model ve cihaz doğrulaması

Gerçek Jira/GitLab hesaplarıyla senkronizasyon doğrulanmadı. Eğitilmiş AI modeli yok; BFS ve açık puanlama var. Sites yayını ayrı hazırlanmış arayüz senaryosudur, Python API yayını değildir.

## Yayın sonrası gözlem

Önce küçük ve sentetik girdilerle temel akışı kontrol et. Beklenmeyen hata, boş ekran, yanlış hesap, yetkisiz erişim veya veri kaybında tarih, uygulama commit’i, ortam ve yeniden üretme adımlarını kaydet; kişisel veri ve secret ekleme. Statik araçlarda tarayıcı konsolu/ağ hatalarını; backend bulunan projelerde durum kodu, gecikme ve hata oranını incele. Bu belgede sürekli izleme veya otomatik geri dönüş kurulmuş olduğu iddia edilmez.

## Kabul kaydı

Her yeni sürümün kaydı; test komutu/sonucu, kaynak SHA, yayın sürümü, gerçek servis/model sürümü, cihaz/işletim sistemi, veri kümesi özeti ve geri dönüş denemesini içermeli. Erişim veya fiziksel donanım yoksa ilgili satır **çalıştırılmadı** olarak tutulur; otomatik test başarısı yerine geçirilmez.
