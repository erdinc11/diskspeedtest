# Disk Hız Testi — Uygulama Tanımı

Linux masaüstünde çalışan **Disk Hız Testi** uygulamasını aşağıdaki ürün ve davranış tanımına bütünüyle uygun oluştur. Çıktı, kullanıcıya sıralı disk yazma ve okuma hızlarını ölçme, seçili diskin kapasite ve donanım bilgilerini görüntüleme olanağı veren tamamlanmış bir masaüstü uygulaması olmalıdır. Arayüz dili Türkçe olmalıdır. Sonuç mevcut referans uygulamayla ekran, metin, akış ve davranış bakımından olabildiğince aynı görünmelidir.

## Uygulama kimliği ve çalışma ortamı

- Uygulama adı ve pencere başlığı: **Disk Hız Testi**.
- Linux masaüstü uygulamasıdır; standart pencere başlığı ve masaüstü pencere kontrollerini kullanır.
- Uygulama kimliği: `org.diskspeedtest.Gtk4`.
- Ana pencere başlangıç boyutu yaklaşık **700 × 250 px**, yeniden boyutlandırılabilir olmalıdır.
- Yerelleştirme Türkçedir. Ondalık ayırıcı virgül, binlik ayırıcı nokta olmalıdır. Kullanıcıya gösterilen depolama boyutları ikinin kuvvetlerine göre B, KB, MB, GB, TB birimleriyle yazılmalıdır.
- Temel ölçüm ve uygulama kullanımı için yönetici yetkisi isteme. SMART/disk sağlığı gibi yetki gerektiren bilgiler yalnızca kullanıcı açıkça ilgili isteği yaptığında yetki istemelidir.
- Masaüstünden başlatılabilir olmalı; adı, kategorileri ve açıklaması uygulamayla tutarlı bir `.desktop` başlatıcısı sağlanmalıdır. Kategoriler: System, Filesystem, Utility. Anahtar sözcükler disk, hız, speed, test, benchmark, yazma ve okuma kavramlarını kapsamalıdır.

## Görsel tasarım

Kompakt, sade ve yerel KDE Breeze/Dolphin görünümü kullan. Fazladan gezinme çubuğu, tanıtım ekranı, logo, grafik veya iş akışı ekleme. Ana yüzey, pencere içinde kenar boşlukları olan tek beyaz/tema kartı gibi düzenlenmelidir. Ana pencere içeriği dikey ve sıkı aralıklı; kontrol satırı, iki ölçüm sütunu, boş alan özeti ve durum/not satırından oluşur.

### Renkler ve tipografi

Sistemin KDE renk şeması koyuysa koyu, değilse açık paleti kullan. Açık palet:

- Pencere `#f7f7f7`, kart `#ffffff`, kenarlık `#d8dadd`.
- Ana yazı `#232629`, ikincil yazı `#707d8a`.
- Vurgu `#3daee9`, vurgu üstüne gelme `#299dd4`, vurgu yazısı beyaz.
- Normal düğme zemini `#eff0f1`, kenarlığı `#bdc3c7`, hover zemini `#dfe1e3`.
- İlerleme izi `#dcdfe3`, yol metni `#2980b9`, uyarı `#da4453`.

Koyu palet:

- Pencere `#31363b`, kart `#232629`, kenarlık `#4a4f54`.
- Ana yazı `#eff0f1`, ikincil yazı `#a0a6ad`.
- Vurgu `#3daee9`, hover `#58b9e9`, vurgu yazısı `#1b1e20`.
- Normal düğme `#3a3f45`, kenarlık `#545a60`, hover `#454b52`.
- İlerleme izi `#41474d`, yol metni `#3daee9`, uyarı `#da4453`.

Kartların köşeleri yaklaşık 8 px, alan dolgusu 12 px ve ince kenarlığı olmalıdır. Düğmeler ve seçim alanları 4 px köşeli, yaklaşık 30 px yüksekliğinde olmalıdır. Ana hız değeri 22 px, kalın; pencere/alan başlıkları 11–15 px; yardımcı metinler 11 px civarıdır. Yazı ölçümleri yerel GTK görünümüne uyumlu olmalıdır. Vurgu rengi ilerleme çubuklarında ve birincil **Başlat** düğmesinde kullanılır. **İptal** düğmesi yıkıcı eylem kırmızısını kullanır. Etkileşimli kontrollerde hover ve odak durumu görünür olmalıdır.

## Ana pencere düzeni ve içerik

Ana gövde bir kart içinde, yaklaşık 8 px dikey boşlukla sıralanır. Kart ve içeriğin çevresinde küçük, dengeli kenar boşlukları bulunur.

### 1. Kontrol satırı

Soldan sağa:

1. Genişleyebilen, düzenlenemeyen fakat odaklanabilir hedef klasör alanı. İlk değer kullanıcının ev dizinidir (`~` açılmış tam yol olarak gösterilir). Yol mavi bağlantı renginde gösterilir; uzun yol kırpılır.
2. **Seç…** düğmesi. Klasör seçici açar; başlığı **Test klasörü seç**. Seçim sonrası yolu günceller ve boş alan özetini yeniler. İptal edilirse mevcut seçim değişmez.
3. Test boyutu açılır listesi; seçenekler bu sırayla: **128 MB**, **256 MB**, **512 MB**, **1 GB**, **2 GB**, **4 GB**, **8 GB**, **16 GB**, **Özel**. İlk açılışta **1 GB** seçilidir.
4. Sadece **Özel** seçiliyken görünen sayısal boyut alanı. Aralık 0,1–2048,0 GB; adım 0,1 GB; iki ondalık basamak. İlk değeri 1,00 GB'dır. Seçim/değer değişince alan gereksinimi güncellenir.
5. **Bırak** onay kutusu. Araç ipucu: **Test dosyasını silme**. Varsayılanı kapalıdır.
6. **Detaylar…** düğmesi. Araç ipucu: **Seçili diskin ayrıntılarını göster**.

Kontroller dar pencere boyutlarında taşmadan yeniden boyutlanmalı; yol alanı kalan alanı almalıdır.

### 2. Ölçüm alanı ve eylemler

İki eşit/benzer genişlikte sütun yan yana yer alır: **Yazma** ve **Okuma**. Her sütunda bu sırayla:

- Küçük, ikincil renkli metrik başlığı.
- Başlangıçta `—`, işlem sırasında büyük hız sayısı, ölçüm henüz başlamadıysa veya sıfırlanmışsa `—`.
- Küçük ikincil satır; ölçüm boyunca `ort. {hız}` biçiminde ortalama hızı gösterir. Henüz başlamadıysa boş bırakılır.
- İnce yatay ilerleme çubuğu; başlangıçta sıfır, tamamlanan bayt oranına göre dolar.

Ölçüm sütunlarının sağ tarafında yan yana **İptal** ve **Başlat** düğmeleri yer alır. Normalde **Başlat** etkin ve birincil vurgulu, **İptal** devre dışıdır. Test sürerken **Başlat** devre dışı ve **İptal** etkin olur. Düğmeler dikey olarak ölçüm alanıyla hizalıdır.

### 3. Boş alan ve durum satırları

Ölçüm alanının altında, sol hizalı, küçük ve ikincil renkli tek satırda şu bilgiler bu sırayla gösterilir:

`{aygıt veya bilinmiyor} · {dosya sistemi veya ?} · boş: {boş alan} · gerekli: ~{gereken alan} · {I/O modu}`

- Ayar değişince ve uygulama açılınca güncellenir.
- Gerekli alan, test boyutunun %105'i olarak hesaplanır.
- Kullanılabilir alan gerekenden azsa bu satır uyarı/kırmızı rengini alır.
- I/O modu, destek varsa **doğrudan I/O**, yoksa **önbellekli I/O** olarak gösterilir.

En altta sol hizalı, tek satırlık durum/not metni yer alır. Uzunsa sonu üç nokta ile kısaltılır. Başlangıçta boş olabilir. Test sırasında aşama, tamamlanan/toplam MB miktarı ve sonuç modu burada gösterilir.

## Test davranışı

- Kullanıcı **Başlat** dediğinde hedefin mevcut bir klasör olup olmadığını ve yazılabilirliğini doğrula. Geçersiz hedef için **Geçersiz klasör** uyarısı ve **Seçilen konum bir klasör değil.** mesajı; yazma izni yoksa **Yazma izni yok** başlığıyla, klasör yolunu içeren ve yazılabilir konum seçilmesini isteyen mesaj göster.
- Dosya adı hedef klasör içindeki gizli `.disk_hiz_testi.tmp` dosyasıdır. Boyut 4 KiB hizasına yuvarlanır. Başlamadan önce önceki geçici dosyanın kalıntısını temizle.
- Yetersiz boş alanda testi başlatma. Boyutun yaklaşık %105'ini **Gereken: ~{boyut}**, mevcut boş alanı **Boş: {boyut}** şeklinde belirten hata göster.
- Önce sıralı yazma, ardından aynı geçici dosyadan sıralı okuma ölçümü yap. Varsayılan test boyutu 1 GiB'dır. Ölçüm sonuçları hem anlık/kararlı hız hem tüm koşunun ortalama hızı olarak gösterilmelidir.
- I/O blok boyutu normal aygıtlarda 8 MiB; USB aygıtlarında 256 KiB olmalıdır. Rastgele içerik kullan; test dosyasının sıkıştırma/seyrek dosya nedeniyle yapay olarak hızlı görünmesini önle. Yazma tamamlanınca veriyi diske eşitle. Okumadan önce dosya önbelleğini mümkünse düşür; okuma ölçümünü önbellek hızına dönüştürme.
- Desteklenen ve USB olmayan aygıtlarda doğrudan I/O (`O_DIRECT`) dene; açılamazsa önbellekli I/O'ya geri dön. USB/UAS köprülerinde doğrudan I/O kullanma. Hız birimi 1024 tabanlı eşiklerle otomatik seçilsin: GB/s, MB/s, KB/s. GB/s iki ondalık, MB/s ve KB/s tam sayı; Türkçe sayı biçimi kullan.
- Anlık hız kısa, yaklaşık 0,75 saniyelik kayan pencerede yumuşatılır. Arayüz ilerlemesi saniyede en fazla yaklaşık dört kez yenilenir. Anlık hız büyük değer; küçük satırdaki `ort.` tüm aşama ortalamasıdır.
- Test durumu örnekleri: başlangıçta **Test başladı…**; yazarken **Yazma: {tamamlanan MB} / {toplam MB} MB**; okurken **Okuma: {tamamlanan MB} / {toplam MB} MB**; iptal basıldıktan sonra **İptal ediliyor…**.
- Aşama bittiğinde ana değer kararlı hız, `ort.` değeri tüm aşamanın ortalaması olur. Son not satırında yazma ve okuma süreleri `{aşama}: {saniye, 2 basamak} sn` biçiminde, tamamlanan aşama sırasıyla listelenir. Sonuna kullanılan yöntemi ekle: doğrudan I/O ise **doğrudan I/O ile ölçüldü (önbellek hariç)**; değilse **önbellekli I/O; yazma hızı diske yazma beklemesini içerir**.
- İptal, hem yazma hem okuma sırasında hızlı ve güvenli biçimde çalışır. **İptal edildi.** sonucu gösterilir; henüz tamamlanmamış değerler `—` olur, tamamlanmış aşamanın sonucu korunur ve çubuklar sıfırlanır.
- Başarılı test bittiğinde eylem düğmelerini normal duruma getir ve ölçüm sonuçlarını ekranda bırak.
- **Bırak** kapalıysa geçici test dosyasını iptal, hata ve başarı dahil her çıkış yolunda sil. Açıksa dosyayı koru. Uygulama sonraki testin başında önceki dosyayı yine güvenle ele almalıdır.
- Disk I/O, disk tespiti ve SMART sorguları pencereyi dondurmamalı; arayüz yanıt vermeye devam etmelidir.
- Disk hatalarını **Test başarısız** başlıklı uyarıyla bildir; hata metninde **Disk hatası: {sistem mesajı}** biçimini kullan. Beklenmeyen hatada **Beklenmeyen hata: {mesaj}** göster. Başarısızlıkta hızları ve çubukları temizle, eylemleri başlangıç durumuna al.
- Yazma sırasında fiziksel disk yazma sayaçları okunabiliyorsa önbellekli yazmada geçici dosya hızı yerine fiziksel yazma hızını anlık gösterebilirsin. Sayaç veya özellik bulunmaması testi engellememelidir.

## Disk özeti penceresi

**Detaylar…** seçilince ayrı, ana pencereye bağlı ve modal **Disk Özeti** penceresi açılır. Başlangıç boyutu yaklaşık **650 × 650 px**, içerik dikey kaydırılabilir ve seçilebilir metinlerden oluşur. Pencere açılırken düğme **Yükleniyor…** olur ve devre dışı kalır; sonuç gelince **Detaylar…** olarak geri döner. Bilgi toplama sırasında ana arayüz donmaz.

Pencere içeriği yukarıdan aşağıya:

1. Büyük ve kalın başlık: disk modeli; model bilinmiyorsa aygıt adı, o da yoksa **Disk**. Altında varsa `{disk türü} · {arayüz} · {dosya sistemi}`; yoksa **Disk bilgileri**.
2. Kart biçiminde **Kapasite** özeti. Solunda başlık, karşısında toplam kapasite veya **Kullanılamıyor**. Altında kullanım yüzdesini gösteren vurgu renkli yatay çubuk. En altta kullanılan miktar ve yüzde (`●  Kullanılan  {miktar} · {yüzde}%`) ile sağda `Boş  {miktar}`. Bilgi yoksa `—`/uygun boş değer göster.
3. Eşit genişlikli üç kart: **Sağlık**, **Sıcaklık**, **Çalışma süresi**. Değerler büyük/kalın; bilinmiyorsa **Veri yok**. SMART sağlığı **Geçti** ise yeşil, olumsuz sağlık uyarısı varsa kırmızı, bilinmiyorsa ikincil renktedir. Uzun değer kırpılır, tam değer araç ipucuyla erişilebilir.
4. Hedef klasör yolu, ikincil renkte, ortadan kısaltılarak gösterilir; üzerine gelince tam yol araç ipucunda ve metin seçilebilir olmalıdır.
5. Kaydırılabilir teknik alan. Başlık **TÜM AYRINTILAR · {alan sayısı}**. Her bölüm ayrı kart/grup; bölüm başlığı vurgu renginde, altı ince çizgili. Alanlar ikişerli ızgarada; her değer üstünde küçük ikincil renkli alan adı, altında kalın değer. Uzun metin sarılır, değer seçilebilir/kopyalanabilir. Açılırken metin seçimi kalmamalıdır.
6. Alt sağda, gerekiyorsa **Root olarak göster**, sonra **Kapat** düğmeleri. Pencere zaten yetkili verilerle yüklendiyse Root düğmesi bulunmaz.

### Disk ayrıntılarının kapsamı

En az aşağıdaki grupları ve erişilebilen alanları göster. Alan bulunamazsa uygulama çökmemeli; `—`, `bilinmiyor`, `Bilinmiyor` veya **Veri yok** gibi uygun değer göster. Ağ diski/sanal dosya sistemi gibi bir blok aygıt bulunamazsa **Bağlantı** grubunda hedef konum, aygıt, dosya sistemi ve boş alan; **Aygıt** grubunda `Blok aygıt eşleştirilemedi (ağ diski, sanal dosya sistemi vb.)` durumu göster.

**Bağlantı:** Hedef konum, Aygıt, Dosya sistemi, Toplam alan, Kullanılan (yüzdeyle), Boş alan.

**Donanım:** Tür (SSD/HDD/USB veya uygun aygıt türü), Model, Model ailesi, Üretici, Seri numarası, Yazılım sürümü, Form faktörü, dönen diskte Dönüş hızı (RPM), Kapasite.

**Bağlantı tipi:** Arayüz ve aygıt adı; gerektiğinde SATA sürümü, NVMe sürümü veya USB sürümü ve USB hız sınırı; USB bağlantısında **USB bağlantısında ölçülen hız bu tavanın altındadır** notu, dahili bağlantıda **USB: Bağlı değil (dahili bağlantı)**.

**Performans:** Dönen medya (Evet/Hayır), Mantıksal blok bayt, Fiziksel blok bayt, TRIM/DISCARD (Destekliyor/Desteklemiyor), erişilebiliyorsa I/O zamanlayıcı ve alternatifleri, erişilebiliyorsa sıcaklık.

**Sağlık:** SMART, Çalışma süresi, varsa SMART notu, Yazma önbelleği açıksa **Açık**, erişilebiliyorsa aygıt Durumu.

SMART sağlık/öznitelik verisi yetki gerektiriyorsa ilk detay açılışında güvenli, mevcut bilgileri göster ve kilitli alanlara **Root izni gerekli** yaz. Kullanıcı **Root olarak göster** dediğinde sistemin standart yetkilendirme diyaloğunu bir kez açarak gereken SMART verilerini sorgula; iptal veya yetki hatası durumunu anlaşılır biçimde göster, uygulama çalışmaya devam etsin. Bekleme sırasında düğme **Yetki bekleniyor…** olur ve devre dışı kalır. Başarılı/başarısız sonuç geldiğinde detay penceresini güncel verilerle yenile; yetki alınmadıysa Root düğmesi tekrar kullanılabilir olmalıdır. Kullanıcı bu düğmeye basmadıkça SMART için yetki isteme.

## Metin biçimlendirme ve hata durumları

- Ondalık ve binlik biçim Türkçeye uygun olmalıdır: örneğin `1.234,5`.
- Hız formatı: 1 GiB/s ve üstünde iki basamakla `GB/s`; 1 MiB/s ve üstünde tam sayıyla `MB/s`; altında tam sayıyla `KB/s`.
- Kapasite ve boş alan biçimi örneğin `512 GB`; test ilerlemesi MB cinsinden tam sayılı gösterilir.
- Pencere uyarıları anlaşılır Türkçe başlık ve mesaj içerir; çok satırlı hata metni ana durum satırında tek satır gösterilecekse ayırıcı ` · ` ile düzleştirilir.
- Boş, erişilemeyen veya desteklenmeyen donanım bilgileri arayüzü bozmamalı; eksik veri için ayrı hata pencereleri yağdırılmamalıdır.

## Tamamlanma ölçütü

İlk çalıştırmada açılan ana pencere, klasör ve boyut seçimi, canlı sıralı yazma/okuma ölçümü, iptal, dosyayı koruma seçeneği, boş alan uyarısı, hata yönetimi, koyu/açık KDE teması ve ayrıntılı disk özeti birlikte çalışır. Türkçe metinler, başlangıç değerleri, boyutlar, sıralama, durum geçişleri ve görsel hiyerarşi bu tanımla tutarlı olmalıdır. Uygulamaya bu kapsam dışında özellik ekleme.
