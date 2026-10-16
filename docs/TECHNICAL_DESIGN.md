# Teknik tasarım ve doğrulama sınırları

## Veri akışı

Tarayıcı aynı kaynaktaki Python HTTP API'ye oturum çereziyle erişir. API yetkiyi kontrol eder; CSV veya salt okunur Jira/GitLab verisi yönlü grafa dönüştürülür. SQLite her içe aktarmada ayrı grafik sürümü tutar. Analiz tek bir sürümün düğüm ve ilişkilerini bir okuma işlemi içinde alır; sonuç JSON'u grafik sürümü, kullanıcı kimliği ve UTC kayıt zamanı ile saklanır. Eşzamanlı yeni içe aktarma, devam eden analizin kaynak sürümünü değiştirmez.

## Etki hesabı

Motor makine öğrenmesi veya LLM kullanmaz. Başlangıç düğümünden yalnızca dışa yönlü ilişkiler üzerinde genişlik öncelikli arama (BFS) yapar. Azami derinlik 5'tir. Döngüler tekrar ziyaret edilmez. Her hedef için ilk bulunan en kısa yol tutulur; eşit uzunluktaki alternatif yolların tümü raporlanmaz. Girdi ilişkilerinin doğruluğu otomatik doğrulanmaz.

`score = max(35, min(99, 100 - 10 * depth + criticality))`

`criticality`, -100 ile 100 arasında bir tam sayı puan düzeltmesidir; olasılık değildir. Sentetik örnekte negatif değerler de vardır. Jira öncelikleri 0–10 aralığında dönüştürülür. 88 ve üzeri kritik, 75–87 yüksek, diğerleri orta sınıfıdır. Model müşteri sonuçlarıyla kalibre edilmemiştir. Mevcut/önerilen değer metinleri bağlam olarak saklanır; puanı veya graf aramasını değiştirmez.

Kanıt yolu sayısı, başlangıç hariç ulaşılan varlık sayısıdır. Metadata doluluğu, hem sahibi hem son ilişki gerekçesi dolu sonuçların oranıdır; sonuç yoksa null döner. Bu oran güven/başarı/tespit doğruluğu değildir. Bağlayıcının atadığı yer tutucu sahip adları da dolu metin sayılır; gerçek sahiplik doğrulaması yapılmaz.

Grafik çizimi ilk sekiz sonucu gösterir; tablo ve CSV tüm sonuçları içerir. Sunucu derinliği dışında kalan ilişkiler raporlanmaz. Durum sütunu bir inceleme önerisidir; görev atama veya onay kaydı değildir.

## CSV sözleşmesi

Başlıklar tam olarak README'deki alanlardan oluşmalıdır; sıraları değişebilir. UTF-8 BOM desteklenir. Eksik/fazla sütun, yinelenen başlık, yinelenen düğüm kimliği, aynı source/target/relation birleşimi, bilinmeyen hedef, boş zorunlu alan ve aralık dışı criticality reddedilir. Owner ve reason boş olabilir; bu eksiklik metadata oranına yansır. HTTP gövdesi en fazla 2 MiB'dir. Hatalı içe aktarma yeni sürüm oluşturmaz.

## Erişim ve saklama

Yönetici tüm projelere erişir. Analist hesabı proje üyeliğinde viewer veya analyst yetkisi alır; viewer analiz çalıştıramaz. Geçici parola değişimi zorunludur. Parola değişimi, sıfırlama ve hesap kapatma oturumları iptal eder. Son aktif yönetici kapatılamaz. GET/HEAD statik dosya izin listesi backend, ortam dosyaları ve veritabanının sunulmasını engeller.

SQLite dosyası şifrelenmez; dosyaya erişen yönetici kayıtları değiştirebilir. Grafik sürümlerini değiştiren uygulama uç noktası yoktur; bu, kriptografik değişmezlik garantisi değildir. Ekrandaki kayıt yalnızca son başarılı analiz özetidir; tam kurumsal denetim günlüğü değildir. Eski analizler geriye dönük sürüm bilgisi kazanmaz.

Sunucu 127.0.0.1'e bağlanan yerel prototiptir. İlk erişen kişi yönetici kurar; ilk kurulumu güvenilmeyen ağda yayımlama. Python http.server, internet ölçeğinde üretim sunucusu olarak doğrulanmamıştır. Giriş sınırı süreç belleğinde ve IP bazlıdır; ters vekil/çoklu süreç kurulumu ayrıca tasarlanmalıdır. SSO/MFA, hesap kurtarma, şifreli yedekleme ve yetki kaldırma arayüzü bu sürümde yoktur.

Bağlayıcı adresleri sunucu ortamından gelir. HTTPS, DNS adres kontrolü, yanıt boyutu ve yönlendirme sınırlaması uygulanır. DNS kontrolü ile gerçek bağlantı ayrı çözümlemeler kullanır; bu tam DNS-rebinding koruması değildir. Güvenilmeyen hedeflerde ağ çıkış izin listesi gerekir. Jira/GitLab canlı hesaplarıyla doğrulama yapılmadı; testler sahte yanıtlarla sözleşme ve dönüşümü sınar. Commit mesajında anahtar bulunması semantik uygulama kanıtı değildir; incelenmesi gereken bir ilişki adayıdır.

## Doğrulama

`python -m unittest discover -s tests -v`: motor, CSV hataları, döngüler, SQLite kalıcılığı ve sürüm farkları, parolalar/oturumlar, bağlayıcı dönüşümü ve gerçek yerel HTTP yetki kontrolleri.

`npm ci && npx playwright install chromium && npm run test:e2e`: ilk kurulum, analiz, gerçek kimlikle CSV indirme, geçersiz düğüm sonrası eski sonucun temizlenmesi ve çıkış. Node yalnızca tarayıcı testleri için gereklidir. Test veritabanı `test-results/` altındadır.

GitHub Actions, Python 3.10/3.12 testlerini ve Chromium akışını çalıştırır. Canlı Jira/GitLab, üretim yükü, harici güvenlik testi ve gerçek müşteri verisiyle risk doğrulaması bu kapsamda değildir.
