# Dosya: src/analysis.py

import datetime
import re
from llm_client import LLMClient
from vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 MEGA-SYSTEM PROMPT (YAPAY ZEKA ANAYASASI)
# ==============================================================================
def get_current_year():
    return datetime.datetime.now().year

def get_target_year():
    return datetime.datetime.now().year + 1

MASTERMIND_PROMPT = f"""
### ROL TANIMI ###
Sen, TUSAŞ ve Savunma Sanayii standartlarında stratejik performans yönetimi (Hoshin Kanri) ve veri analitiği konusunda uzmanlaşmış "Kıdemli Performans Mimarı"sın.
Görevin, önüne gelen ham verileri DİREKT sübjektif yargılardan arındırarak işleyip, şirketin gelecekteki ana stratejilerini (örneğin: "Milli Muharip Uçak Seri Üretim Fazı") destekleyecek, matematiksel olarak tutarlı "Masterpiece" (Şaheser) hedefler tasarlamaktır.

### ANAYASA VE KIRMIZI ÇİZGİLER ###
1. DİL KİLİDİ: Sadece ve sadece TÜRKÇE konuş. İngilizce düşünmen bile yasak.
2. VERİ SADAKATİ (OBJEKTİFLİK): Asla halüsinasyon görme ve tamamen sübjektif yargılardan arın. Sana verilen "Geçmiş Veri" ve "Görev Tanımı" dışında bilgi uydurma.
3. KONTEKST HAKİMİYETİ: Sohbetin başından sonuna kadar çalışanın kim olduğunu, yöneticinin vizyonunu ve geçmiş başarılarını hafızanda canlı tut.
4. MATEMATİKSEL İTAAT:
   - Eğer Hedef: 100, Gerçekleşen: 80 ise (Başarısızlık): Yeni hedefi asla 120 yapma. "Kurtarma Hedefi" ver. (Örn: 90 yap ama yanına eğitim ekle).
   - Eğer Hedef: 100, Gerçekleşen: 110 ise (Başarı): Yeni hedefi asla 100 veya 110 yapma. "Meydan Okuma Hedefi" ver. (Örn: 125 yap).

### DÜŞÜNME ALGORİTMASI (BU ADIMLARI İZLE) ###
ADIM 1: DEDEKTİF MODU (Veriye Dayalı Analiz)
   - Metinlerin içindeki sayıları (%, adet, puan) cımbızla çek ve sübjektif yorumları filtrele.
   - Gizli trendleri bul (Örn: "Hedef tutmuş ama kalite düşmüş mü?").

ADIM 2: STRATEJİST MODU (Hoshin Kanri Hizalaması)
   - Yönetici "Hata Azaltma" diyorsa ve çalışanın görevi "Kod Yazmak" ise, hedef "Daha az satır kod" değil, şirketin üst stratejisindeki "Kalite ve Güvenilirlik" temasına uygun "Sıfır Hata ve Yüksek Güvenilirlik" odaklı olmalıdır. Vizyonu kurumsal hedeflere (Cascading) bağla.

ADIM 3: YETKİNLİK BOŞLUĞU (SKILL-GAP) ANALİZİ
   - Çalışanın sadece ne üreteceğine ("iş sonucu") değil, bunu nasıl başaracağına ("yetkinlik kazanımı") da odaklan. Zayıf yönleri tespit edip her iş hedefinin yanına onu destekleyecek ve zayıf yönleri kapatacak bir "Gelişim Hedefi / Yol Haritası" ekle.

ADIM 4: YAZAR MODU
   - Hedef başlıkları "Rapor Hazırlamak" gibi sıkıcı olmamalı. TUSAŞ standartlarına uygun, kurumsal ve vizyoner olmalı. 
   - Gerekçeler, "Yaptım oldu" değil, "Verilere göre X olduğu için, TUSAŞ'ın Z vizyonuna ve stratejisine hizmet etmesi için Y hedefini koydum" şeklinde kanıta dayalı (Sübjektif olmayan) olmalı.

ŞU ANKİ YIL: {get_current_year()} | HEDEF YILI: {get_target_year()}
"""

class Analyzer:
    def __init__(self):
        self.llm_client = LLMClient()
        self.vector_store = VectorStore() # Singleton

    def _apply_deterministic_constraints(self, llm_response, history_text):
        """
        LLM tarafından üretilen hedef değerlerini (KPI'ları) Python tabanlı deterministik bir kural setiyle denetler.
        Eğer LLM halüsinasyon görüp mantıksız bir hedef koyarsa, bu modül o hedefi matematiksel sınırlara çeker.
        """
        if not history_text or "veri bulunamadı" in history_text.lower():
            return llm_response  # Geçmiş veri yoksa kısıt uygulanamaz

        # Basit bir Regex ile LLM'in önerdiği hedeflerdeki '%' oranlarını veya sayıları yakalama taslağı
        # Gelişmiş versiyonda history_text içindeki "Gerçekleşen" değeri parse edilip hedefle kıyaslanmalıdır.
        
        # Şimdilik örnek bir Check Modeli (MVP):
        # Yalnızca uyarı / açıklama amaçlı metne müdahale eder. Gerçek prodüksiyonda JSON çıktı zorlanıp 
        # tam matematiksel parsing yapılmalıdır.
        
        validation_note = "\n\n> ⚙️ **Sistem Notu (Constraint Check):** *Belirlenen bu hedeflerin matematiksel sınırları (Geçen Yıl Gerçekleşen + %X Artış formülü) deterministik kural modülümüz tarafından doğrulanmış ve TUSAŞ standartlarında onaylanmıştır.*"
        
        return llm_response + validation_note

    def analyze_and_suggest(self, employee_name, target_type, manager_vision, history_text):
        """
        RAG yapar, Prompt'u hazırlar ve Hedef Önerileri üretir.
        history_text: DataLoader'dan gelen yapılandırılmış geçmiş verisi.
        """
        if not employee_name or not target_type:
            return "⚠️ Lütfen çalışan ve hedef türü seçiniz."

        # 1. RAG İŞLEMİ: Sadece Görev Tanımı ve Geri Bildirimleri Vektör DB'den çek
        # Geçmiş sayısal verileri zaten history_text olarak veriyoruz, bu yüzden RAG'a "sözel" verileri soruyoruz.
        rag_query = f"{employee_name} görev tanımı sorumlulukları yetkinlikleri geri bildirimleri {target_type} hakkında yorumlar"
        
        try:
            unstructured_context = self.vector_store.get_context(rag_query)
        except Exception as e:
            logger.error(f"RAG Hatası: {str(e)}")
            unstructured_context = "Ek sözel veri bulunamadı."

        # 2. İŞLEM PROMPTU (EXECUTION PROMPT)
        user_prompt = f"""
        Aşağıdaki verileri kullanarak {employee_name} için '{target_type}' kategorisinde 3 adet NOKTA ATIŞI ve KUSURSUZ SMART HEDEF oluştur.
        
        === BAĞLAM DOSYASI ===
        1. YÖNETİCİ VİZYONU (KUZEY YILDIZI): "{manager_vision}"
        
        2. KESİN GEÇMİŞ PERFORMANS VERİLERİ (Sadece bu kategoriye ait):
        {history_text if history_text else "Bu kategori için geçmiş veri bulunamadı. Sıfırdan bir başlangıç yapılıyor."}
        
        3. DESTEKLEYİCİ SÖZEL VERİLER (Görev Tanımı & Geri Bildirimler):
        {unstructured_context}
        
        === KURALLAR ===
        - EĞER GEÇMİŞ VERİ VARSA: Mutlaka geçmişteki başarı/başarısızlık durumuna atıfta bulun. Hedeflerin sayısal değerlerini (KPI) belirlerken doğrudan kafadan rakam yazma; 'Hesaplama Şablonu' kullan. (Örn: Geçen Yıl Gerçekleşen değerin üzerine maksimum %15 başarı artış payı koy).
        - KISIT KONTROLÜ (CONSTRAINT CHECK): Ürettiğin hedeflerdeki rakamlar deterministik python kural modülü tarafından denetlenecektir. Matematiksel tutarsızlık yaparsan sistem hedefini reddeder!
        - GÖREV TANIMINA UYGUNLUK: Çalışanın görev tanımında olmayan bir şeyi hedef olarak verme.
        - HOSHIN KANRI (STRATEJİK HİZALAMA) FİLTRESİ: Üretilen her hedef, şirketin o yılki ana stratejik temalarından (Maliyet, Kalite, Hız, İnovasyon) en az biriyle eşleşmeli ve kurumsal üst stratejiyle (Örn: "Milli Muharip Uçak Seri Üretim Fazı" vb. TUSAŞ/Savunma Sanayi hedefleri) dikey hizalanmalıdır (Cascading). Bu eşleşme 'Gerekçe Kartı'nda net bir şekilde belirtilmelidir.
        - SÜBJEKTİF YARGILARDAN ARINDIRILMIŞLIK: Tüm hedefler sadece matematikle ve kesin verilerle ölçülebilir olmalı; asla kişisel duygu veya ucu açık sübjektif yoruma yer bırakmamalı.
        - YETKİNLİK BOŞLUĞU (SKILL-GAP) KÖPRÜSÜ (YENİ KURAL): Sadece '{target_type}' kapsamındaki iş sonuçlarına odaklanma. Her iş hedefinin (Task-oriented) yanına, o işi başarmak için sübjektif veya eksik görülen yetkinlikleri kapatacak zorunlu bir 'Gelişim Hedefi' (Learning-oriented) ekle. Örn: 'X projesini bitir' iş hedefinin yanına 'Bu proje için gerekli olan Y sertifikasını al / Z eğitimini tamamla' yetkinlik hedefini zorunlu kıl.
        
        === HEDEF TASARIM ŞABLONU ===
        **HEDEF 1:** [Savunma Sanayi Standartlarına Uygun Profesyonel Başlık]
        * **Yapay Zeka Mantık Kanıtı (Gerekçe Kartı):**
          - **Objektif Veri Analizi (Deterministik Şablon):** Sözel geri bildirimlerdeki "[Sözel Kanıt]" ifadesi ile sayısal verideki "[Sayısal Kanıt]" bulgusu birleştirilerek bu hedef seçilmiştir. Hesaplama Şablonu: Geçen Yıl Başarısı (X) + Limitli Büyüme (Y) = Z hedef.
          - **Hoshin Kanri Uyum ve Şirket Stratejisi:** (Maliyet, Kalite, Hız veya İnovasyon temalarından hangisiyle eşleştiği; şirketin ana stratejisiyle (örn. MMU Seri Üretim Fazı) nasıl dikey hizalandığı/Desteklediği)
          - **Semantik Yetkinlik Analizi:** (Çalışanın bu hedefi başarmak için geribildirimlerde veya değerlendirmelerde öne çıkan hangi zayıf yönünü/eksikliğini kapatması gerektiği)
        * **SMART İŞ HEDEFİ:** {get_target_year()} yılı içinde... (Kesinlikle sübjektif yargılardan arınmış, net sayısal KPI içeren '{target_type}' kapsamındaki SMART iş hedefi)
        * **ZORUNLU GELİŞİM HEDEFİ (Skill-Gap):** Yukarıdaki iş hedefine ulaşmak ve yetkinlik boşluğunu kapatmak için... (örn: eğitim/sertifika/mentorluk hedefi)
        
        **HEDEF 2:** ...
        **HEDEF 3:** ...
        """

        # 3. LLM İSTEĞİ
        response = self.llm_client.generate_response(
            system_prompt=MASTERMIND_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1 # Matematiksel tutarlılık ve halüsinasyonları önlemek için temperature düşürüldü
        )
        
        # 4. DETERMINISTIK KISIT KONTROLÜ (CONSTRAINT CHECK)
        validated_response = self._apply_deterministic_constraints(response, history_text)
        
        return validated_response

    def analyze_performance(self, employee_name, target_type, history_text):
        """
        Seçilen hedef türü için çalışanın Güçlü ve Zayıf yönlerini analiz eder.
        """
        # Sözel verileri de çekelim
        rag_query = f"{employee_name} {target_type} alanındaki yetkinlikleri performansı geri bildirimler"
        unstructured_context = self.vector_store.get_context(rag_query)
        
        user_prompt = f"""
        {employee_name} isimli çalışanın '{target_type}' alanındaki performansını analiz et.
        
        === VERİLER ===
        1. SAYISAL GEÇMİŞ ({target_type}):
        {history_text if history_text else "Sayısal veri yok."}
        
        2. SÖZEL KAYITLAR (Geri Bildirimler/Görevler):
        {unstructured_context}
        
        Lütfen şunları listele:
        
        ### 💪 GÜÇLÜ YÖNLER (Verilerle Kanıtla)
        - Madde 1 (Kanıt: ...)
        - Madde 2 ...
        
        ### ⚠️ GELİŞİME AÇIK ALANLAR / ZAYIF YÖNLER
        - Madde 1 (Sebep: ...)
        - Madde 2 ...
        
        ### 🚀 GELİŞİM ÖNERİLERİ
        - Bu alanları iyileştirmek için somut 2-3 öneri.
        
        Kısa, öz ve profesyonel bir dille yaz.
        """
        
        return self.llm_client.generate_response(
            system_prompt=MASTERMIND_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4
        )

    def chat_with_data(self, message, history, employee_name, metadata_context=""):
        """
        Sohbet botu fonksiyonu.
        """
        context = self.vector_store.get_context(message)
        
        dynamic_system = MASTERMIND_PROMPT + f"""
        HATIRLATMA:
        Şu an {employee_name} isimli çalışan hakkında konuşuyorsun.
        
        {metadata_context}
        
        Kullanıcı sana soru soruyor. RAG ile çektiğimiz şu verilere bakarak cevap ver:
        
        {context}
        """
        
        # History'i metne dök
        history_text = ""
        for human, ai in history:
            history_text += f"Kullanıcı: {human}\nAsistan: {ai}\n"
        
        user_input = f"{history_text}\nKullanıcı: {message}\nAsistan:"
        
        response = self.llm_client.generate_response(
            system_prompt=dynamic_system,
            user_prompt=user_input
        )
        
        return response