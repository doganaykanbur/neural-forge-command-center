# NEURAL FORGE: OTONOM YAZILIM FABRİKASI — MİMARİ RAPOR v1.0

Bu rapor, **Neural Forge** projesinin iç yapısını, bileşenler arası iletişimini ve bir kullanıcının "Hedef" (Goal) girmesiyle başlayan otonom sürecin tüm detaylarını içerir.

---

## 1. Sisteme Genel Bakış

Neural Forge, yapay zeka ajanlarını (AI Agents) bir yazılım geliştirme ekibi gibi koordine eden bir orkestrasyon sistemidir. İnternet bağımlılığı olmadan, yerel **Ollama** modelleri (Mistral, Llama vb.) ve özel bir **Claude Bridge** üzerinden çalışır.

### Ana Hedefler:
-   **Otonom Geliştirme**: Kod yazımı, test ve yayına alma süreçlerini insansız yönetmek.
-   **Yerel Güvenlik**: Verilerin dışarı çıkmaması için tamamen yerel LLM kullanımı.
-   **Hafıza (Persistence)**: Yapılan hatalardan ders çıkarıp NEXUS hafızasına kaydetme.

---

## 2. Ana Bileşenler

### A. Admin Panel (Frontend - Next.js)
Kullanıcı arayüzüdür. Buradan:
-   Yeni "Hedefler" (Goals) oluşturulur.
-   Mevcut "Node"ların (İşçilerin) sağlık durumu ve kapasiteleri (GPU, RAM) izlenir.
-   Ajanların yazdığı loglar ve oluşturulan dosyalar canlı olarak takip edilir.
-   **Kritik Onay Mekanizması (HITL)**: Architect planı bittiğinde veya Reviewer sonuç sunduğunda kullanıcıdan onay istenir.

### B. Nerve Center (Backend - FastAPI)
Sistemin beynidir. Şu alt birimleri yönetir:
1.  **Orchestrator**: LLM kullanarak planlama yapar. Bir hedefi parçalara böler.
2.  **Claude Bridge**: Yerel Ollama'yı standart bir "Claude API" gibi gösterir. Böylece en gelişmiş ajan araçları sistemle uyumlu çalışır.
3.  **Nexus Memory**: Şirket kurallarını (AGENTS.md) ve "Lesson Learned" (Öğrenilen Dersler) kayıtlarını saklar.
4.  **Task Queue**: Yapılacak işleri sıraya koyar ve uygun "Node"lara dağıtır.

### C. Node Agent (Worker - Python)
Gerçek işi yapan "işçidir". Kendi donanımınızda çalışır:
-   **Heartbeat**: Her 5 saniyede bir backend'e "ben buradayım ve şu kadar RAM boşta" mesajı gönderir.
-   **Task Poller**: Backend'den kendine uygun bir iş (Architect, Builder, Tester vb.) olup olmadığını kontrol eder.
-   **Executor**: Gelen talimatı alıp bilgisayarınızda dosya oluşturur veya komut çalıştırır.

---

## 3. Adım Adım İşleyiş Süreci (Lifecycle)

Bir kullanıcı arayüzden **"Basit bir Python hesap makinesi yap"** dediğinde tam olarak şunlar olur:

### 📥 Adım 1: Giriş ve Analiz
Orchestrator bu cümleyi alır ve **Ollama** modeline sorar: *"Bu bir yazılım projesi mi? Evet. Hangi adımlar lazım?"*

### 🗺️ Adım 2: Pipeline Planlama
Orchestrator şu görevleri (Tasks) oluşturur ve kuyruğa (Queue) atar:
1.  **Architect**: Plan hazırla.
2.  **Builder**: Kodu yaz.
3.  **Tester**: Kodu çalıştır ve hatayı kontrol et.
4.  **Reviewer**: Son kalite kontrolü yap.

### 🏗️ Adım 3: Architect Çalışıyor
-   Node Agent, `Architect` görevini kuyruktan çeker.
-   Yerel LLM'e projenin klasör yapısını ve kurallarını sordurur.
-   Sonuç olarak kök dizinde bir `AGENTS.md` (veya `ARCHITECTURE.md`) dosyası oluşturur.

### 💻 Adım 4: Builder (Kod Yazımı)
-   Node Agent, sıradaki `Builder` görevini alır.
-   `AGENTS.md` dosyasını okur.
-   LLM'den aldığı kod bloklarını `calculator.py` gibi dosyalara yazar.

### 🧪 Adım 5: Tester ve Reviewer
-   `Tester` ajanı kodu `python calculator.py` komutuyla çalıştırır.
-   Eğer hata (error) alırsa, hatayı loglar.
-   `Reviewer` logları inceler. Eğer hata varsa süreci `Builder`'a geri döndürür (Retry döngüsü).

### ✅ Adım 6: Tamamlanma
Tüm ajanlar "Pass" (Geçti) onayı verdiğinde ve kullanıcı son ürünü (Execute aşaması sonrası) onayladığında proje "Completed" olarak işaretlenir.

---

## 4. Kritik Özellikler

### 🧠 NEXUS Memory (Hafıza)
Her başarılı görevden sonra ajanlar **"Ne öğrendik?"** analizi yapar. 
-   *Örnek*: "Tkinter kütüphanesi Linux'ta ek paket ister."
-   Bu bilgi NEXUS'a yazılır. Bir sonraki projede Orchestrator bu bilgiyi ajana doğrudan "Ön Bilgi" olarak verir.

### 🚉 Smart Routing & Model Switching (YENİ)
Orchestrator, görev tipine göre en uygun modeli seçer:
-   **Architect & Reviewer**: Daha gelişmiş modeller (Mistral-Large / GPT4 dengi) kullanılır.
-   **Builder & Tester**: Daha hızlı ve kod odaklı modeller (DeepSeek / CodeLlama dengi) tercih edilir.

### 🛡️ Workspace Isolation & Sandboxing (YENİ)
Geliştirme yapılan bilgisayarı korumak için iki katmanlı izolasyon uygulanır:
1.  **Venv (Sanal Ortam)**: Her proje için `python -m venv` ile izole bir kütüphane havuzu oluşturulur. `requirements.txt` otomatik olarak buraya kurulur.
2.  **Docker Isolation**: `Tester` ve `Execute` gibi potansiyel olarak riskli komutların çalıştırılacağı aşamalar, ana sistemden tamamen izole bir **Docker Konteyneri** içinde koşturulur.

### 🚦 Human-in-the-Loop (HITL) (YENİ)
Sistem tam otonom olsa da, kritik eşiklerde (Örn: Kod yazılmadan önceki plan aşaması) sistem `PENDING_APPROVAL` durumuna geçer. Kullanıcı "Admin Panel" üzerinden onay vermeden bir sonraki aşamaya geçilmez.

### 🌉 Offline Claude Bridge
Ajanlar aslında `anthropic` kütüphanesini kullanır ancak aradaki köprü sayesinde istekler `localhost:8000`'e, oradan da `ollama`'ya gider. **Yani dış dünyaya tek bir byte bile çıkmaz.**

---

**Sonuç:** Neural Forge, sizin talimatlarınızı alıp, onları profesyonel bir yazılım ekibi disipliniyle (Mimari -> Kod -> Test -> Onay) hayata geçiren entegre bir ekosistemdir.
