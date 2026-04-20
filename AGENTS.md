# AGENTS.md — Neural Forge Pipeline Contract

> Sabit, tek yönlü akış: **Architect → Builder → Reviewer → Tester → Executor**
> Her aşama bir öncekinin çıktısına bağımlıdır. Geri atlama sadece hata/retry durumunda olur.

---

## 1. Architect (Sistem Mimarı)

**Görev:** Projenin yapısını tasarlar. `ARCHITECTURE.md` üretir: klasör yapısı, type tanımları, teknoloji kararları, modül sınırları.

**Çıktılar:**
- `ARCHITECTURE.md` — Ana yapısal blueprint
- **Atomik Görev Biletleri** — `task_1_db_schema.json`, `task_2_auth_api.json` gibi küçük, spesifik iş paketleri

**Kural:** Diğer tüm roller bu blueprint'e bağlıdır. Architect sadece plan yapar, kod yazmaz.

> 💡 Builder devasa bir metin yerine, spesifik biletleri eriterek ilerler.

---

## 2. Builder (İşçi / Geliştirici)

**Görev:** Architect'in ürettiği blueprint'i ve görev biletlerini okur, kodu yazar. Modülleri, API'leri, UI bileşenlerini oluşturur.

**Altın Kural:** Kendi başına karar almaz — sadece blueprint'e uyar. Mimari sapma (architectural drift) sıfıra indirilir.

**İtiraz Hakkı (Exception Flag):**
Builder aşağıdaki durumlarda süreci durdurup Architect'e `BLUEPRINT_ERROR` uyarısı gönderebilir:
- Belirtilen kütüphane deprecated ise
- Blueprint'te mantıksal çelişki varsa
- Teknik olarak imkansız bir istek varsa

> ⚠️ Builder rastgele kod uydurmak yerine, süreci durdurur ve revize talep eder.

---

## 3. Reviewer (Gatekeeper / Statik Analiz)

**Görev:** Builder'ın yazdığı kodu çalıştırmadan (Static Analysis) denetler.

**Kontrol Listesi:**
- [ ] OWASP Top 10 uyumluluğu
- [ ] Hardcoded secret taraması
- [ ] Type safety doğrulama
- [ ] Mimari uyumluluk (ARCHITECTURE.md ile tutarlılık)

**Actionable Feedback:**
Reviewer sadece "Hata var" demez. GitHub tarzı **Satır İçi Yorum** formatında geri bildirim verir:

```
// File: src/auth/login.ts:42
// ❌ ISSUE: API key is hardcoded
// ✅ FIX: Move to environment variable → process.env.API_KEY
```

> 🛡️ Geçmezse Builder'a tam düzeltme talimatıyla birlikte geri gönderir.

---

## 4. Tester (Red Team / Dinamik Analiz)

**Görev:** Uygulamanın sadece "çalışmasını" değil, "yıkılamaz" olmasını sağlar.

**Test Türleri:**
- **Unit Test** — Modül bazlı, kapsam hedefi >%80
- **Integration Test** — Modüller arası iletişim doğrulama
- **Fuzz Testing** — API endpoint'lerine rastgele/zararlı veri gönderme
- **Stress Testing** — Yük altında davranış analizi

**Performans Denetimi:**
Docker içinde ayağa kaldırırken CPU/RAM tüketimini izler:
- Memory Leak tespit edilirse → test başarılı olsa bile `PERFORMANCE_VIOLATION` ile iptal
- Endpoint yanıt süresi eşiği aşarsa → uyarı

> 🔴 Hata bulursa retry döngüsü başlar (max 3 deneme).

---

## 5. Executor (DevOps / Canlıya Alma)

**Görev:** Tüm aşamalardan geçmiş, onaylı kodu deploy eder.

**İşlem Sırası:**
1. Container'ı ayağa kaldır
2. Environment variable'ları güvenli şekilde enjekte et (Zero-Trust)
3. Sağlık kontrolü (health check) yap
4. Canlıya al

**Rollback Mekanizması:**
Uygulama canlıya alındıktan sonra 10 saniye içinde çökerse:
- Executor bir önceki stabil Docker imajına (veya commit'e) **otonom olarak geri döner**
- Hata logu NEXUS'a raporlanır

> 🔒 Zero-Trust: Executor hiçbir zaman doğrudan kaynak koduna erişmez, sadece onaylı artifact'leri çalıştırır.

---

## Akış Diyagramı

```
[Architect] ──→ [Builder] ──→ [Reviewer] ──→ [Tester] ──→ [Executor]
     │               ↑              │              │             │
     │          BLUEPRINT_ERROR      │         RETRY (3x)    ROLLBACK
     │               │              │              │             │
     └───────────────┘              └──── Builder ─┘             └── Önceki stabil imaj
```
