import streamlit as st
import pandas as pd
from config import Config
from ui_components import load_custom_css, render_header
from analysis import Analyzer
from data_loader import DataLoader
from utils import generate_docx
import os

# Sayfa Ayarları (En başta olmalı)
st.set_page_config(
    page_title=Config.PAGE_TITLE,
    page_icon=Config.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS'i yükle
load_custom_css()

# --- OPTİMİZASYON VE CACHING ---

@st.cache_resource(show_spinner="Sistem Başlatılıyor...")
def get_analyzer():
    """Analyzer sınıfını önbelleğe alır. (VectorStore ve LLM bağlantısı tek sefer yapılır)"""
    return Analyzer()

@st.cache_data(ttl=600)  # 10 dakika önbellekte tut
def load_metadata_cached():
    """Dropdown verilerini önbelleğe alır."""
    loader = DataLoader()
    return loader.get_dropdown_options()

@st.cache_data(ttl=600)
def load_history_cached(name, target):
    """Geçmiş verileri önbelleğe alır."""
    try:
        loader = DataLoader()
        return loader.get_employee_history(name, target)
    except Exception as e:
        return pd.DataFrame()

# --- UYGULAMA MANTIĞI ---

# Analyzer'ı al (Cached Resource)
try:
    analyzer = get_analyzer()
except Exception as e:
    st.error(f"❌ Sistem başlatılamadı: {e}")
    st.stop()

# Session State Başlatma
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_analysis" not in st.session_state: # Hata almamak için opsiyonel başlatma
    st.session_state.last_analysis = None

# Metadata Yükle (Cached Data)
employees_list, target_types_list = load_metadata_cached()

# Yan Menü (Sidebar)
with st.sidebar:
    st.title("🎛️ Kontrol Paneli")
    st.markdown("---")
    
    # Çalışan Seçimi
    if employees_list:
        employee_name = st.selectbox("Çalışan Adı Soyadı", employees_list)
    else:
        employee_name = st.text_input("Çalışan Adı Soyadı", placeholder="Örn: Ahmet Yılmaz")
        if not employees_list:
            st.warning("Excel dosyasından çalışan listesi çekilemedi.")
    
    # Hedef Kategorisi
    default_targets = ["Satış & Pazarlama", "Yazılım Geliştirme", "Operasyonel Verimlilik"]
    options = target_types_list if target_types_list else default_targets
    target_type = st.selectbox("Hedef Kategorisi", options)
    
    manager_vision = st.text_area(
        "Yönetici Vizyonu (Kuzey Yıldızı)",
        placeholder="Örn: Global pazarda %15 büyüme hedeflerken, çalışan memnuniyetini de maksimum seviyede tutmak...",
        height=150
    )
    
    st.markdown("---")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("♻️ Temizle"):
             st.session_state.chat_history = []
             st.session_state.last_analysis = None
             st.rerun()
    with col_s2:
        if st.button("🔄 Veri İndeksle"):
            with st.spinner("İndeksleniyor..."):
                try:
                    analyzer.vector_store.refresh_data()
                    load_metadata_cached.clear() # Cache temizle
                    st.success("Tamamlandı!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

# Ana Sayfa Düzeni
render_header()

# İki Kolonlu Yapı
main_col1, main_col2 = st.columns([4, 6], gap="medium")

with main_col1:
    st.markdown("### 🎯 Stratejik Hedef Sihirbazı")
    st.info("Çalışan verilerini ve vizyonunuzu analiz ederek saniyeler içinde 'Kusursuz Hedefler' oluşturun.")
    
    # URL parametreleri veya Session State ile Sekme Yönetimi
    tab1, tab2, tab3 = st.tabs(["📌 Hedef Önerisi Oluştur", "🔍 Güçlü/Zayıf Yön Analizi", "🧠 Karar Destek Paneli"])
    
    # --- SEKME 1: HEDEF ÖNERİSİ ---
    with tab1:
        if st.button("✨ Hedefleri Oluştur", use_container_width=True):
            if not employee_name:
                st.error("Lütfen bir çalışan seçiniz.")
            else:
                # Vizyon boşsa varsayılan değer ata
                current_vision = manager_vision if manager_vision.strip() else "Çalışanın geçmiş performansına ve kurumsal standartlara dayalı dengeli gelişim."
                with st.spinner("🤖 Geçmiş veriler ve görev tanımları taranıyor..."):
                    try:
                        # Geçmiş veriyi çek ve metne çevir
                        history_df = load_history_cached(employee_name, target_type)
                        try:
                            history_text = history_df.to_markdown(index=False) if not history_df.empty else ""
                        except Exception:
                            # Tabulate yoksa veya hata verirse CSV formatına dön
                            history_text = history_df.to_csv(index=False) if not history_df.empty else ""

                        # Metadata Çek ve Ekle
                        loader = DataLoader() # Cachelenmemiş taze veri için
                        metadata = loader.get_employee_metadata(employee_name)
                        
                        metadata_text = ""
                        if metadata:
                            metadata_text = "=== ÇALIŞAN KİMLİK KARTI ===\n"
                            for k, v in metadata.items():
                                metadata_text += f"{k}: {v}\n"
                            metadata_text += "===========================\n\n"
                        
                        # Metadata'yı history_text'in başına ekle (veya ayrı parametre yapabiliriz ama bu daha kolay)
                        full_context_text = metadata_text + history_text
                        
                        suggestion = analyzer.analyze_and_suggest(
                            employee_name, target_type, current_vision, full_context_text
                        )
                        
                        st.session_state.last_analysis = suggestion
                        st.session_state.chat_history.append(("Asistan", suggestion))
                        
                        # DSS Metriklerini Hesapla
                        st.session_state.dss_metrics = analyzer.get_decision_support_metrics(
                            employee_name, target_type, suggestion, history_df
                        )
                        
                        st.success("Hedef Seti Hazırlandı!")
                    except Exception as e:
                        st.error(f"Bir hata oluştu: {e}")

        # Son Analiz Sonucunu Göster (Varsa)
        if st.session_state.last_analysis:
            with st.expander("📝 Oluşturulan Hedefler", expanded=True):
                st.markdown(st.session_state.last_analysis)
                
                # Word İndirme Butonu
                docx_analysis = generate_docx(st.session_state.last_analysis, title=f"{employee_name} - Hedef Öneri Raporu")
                st.download_button(
                    label="📝 Word'e Dönüştür",
                    data=docx_analysis,
                    file_name=f"{employee_name}_hedef_onerileri.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_main_analysis"
                )
    
    # --- SEKME 2: PERFORMANS ANALİZİ ---
    with tab2:
        st.write(f"**{employee_name}** için **{target_type}** alanında detaylı performans analizi.")
        
        if st.button("📊 Analiz Et (Güçlü/Zayıf Yönler)", use_container_width=True):
             if not employee_name:
                st.error("Lütfen çalışan seçin.")
             else:
                with st.spinner("🕵️‍♂️ Detektif modunda analiz yapılıyor..."):
                    try:
                        history_df = load_history_cached(employee_name, target_type)
                        history_text = history_df.to_markdown(index=False) if not history_df.empty else ""

                        # Metadata Çek ve Ekle
                        loader = DataLoader()
                        metadata = loader.get_employee_metadata(employee_name)
                        metadata_text = ""
                        if metadata:
                            metadata_text = "=== ÇALIŞAN KİMLİK KARTI ===\n"
                            for k, v in metadata.items():
                                metadata_text += f"{k}: {v}\n"
                            metadata_text += "===========================\n\n"
                        
                        full_context_text = metadata_text + history_text
                        
                        analysis_result = analyzer.analyze_performance(
                            employee_name, target_type, full_context_text
                        )
                        st.session_state.performance_analysis = analysis_result
                    except Exception as e:
                        st.error(f"Analiz Hatası: {e}")
        
        if "performance_analysis" in st.session_state:
             st.markdown(st.session_state.performance_analysis)
             
             # Word İndirme Butonu
             docx_perf = generate_docx(st.session_state.performance_analysis, title=f"{employee_name} - Performans Analizi")
             st.download_button(
                 label="📊 Analizi Word'e Dönüştür",
                 data=docx_perf,
                 file_name=f"{employee_name}_performans_analizi.docx",
                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 key="dl_perf_analysis"
             )

    # --- SEKME 3: KARAR DESTEK SİSTEMİ (DSS) ---
    with tab3:
        if employee_name:
            if st.button("📊 Karar Desteği Analizi Çalıştır", use_container_width=True):
                with st.spinner("🧠 Veriler üzerinden stratejik olasılıklar hesaplanıyor..."):
                    history_df = load_history_cached(employee_name, target_type)
                    sample_response = st.session_state.last_analysis if st.session_state.last_analysis else "Genel Performans Hedefleri"
                    st.session_state.dss_metrics = analyzer.get_decision_support_metrics(
                        employee_name, target_type, sample_response, history_df
                    )
                    st.success("Karar Destek Analizi Tamamlandı!")

            if "dss_metrics" in st.session_state:
                metrics = st.session_state.dss_metrics
                
                st.markdown(f"### 🧠 {employee_name} için Stratejik Karar Desteği")
                
                # Üst Metrik Kartları (Kompakt ve Şık)
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    prob = metrics['success_probability']
                    delta_class = "dss-delta-up" if prob > 70 else "dss-delta-warning"
                    st.markdown(f"""
                    <div class="dss-card">
                        <div class="dss-label">🎯 BAŞARI</div>
                        <div class="dss-value">%{prob}</div>
                        <span class="dss-delta {delta_class}">Güven: %{prob}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c2:
                    st.markdown(f"""
                    <div class="dss-card">
                        <div class="dss-label">📈 BÖLÜM UYUMU</div>
                        <div class="dss-subtext">{metrics['benchmark_status']}</div>
                        <span class="dss-delta dss-delta-up">Üst Segment</span>
                    </div>
                    """, unsafe_allow_html=True)

                with c3:
                    risk = metrics.get('risk_score', 25)
                    risk_class = "dss-delta-up" if risk < 40 else "dss-delta-warning"
                    risk_label = "Düşük" if risk < 40 else "Orta/Yüksek"
                    st.markdown(f"""
                    <div class="dss-card">
                        <div class="dss-label">⚠️ RİSK SKORU</div>
                        <div class="dss-value">%{risk}</div>
                        <span class="dss-delta {risk_class}">Seviye: {risk_label}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c4:
                    st.markdown(f"""
                    <div class="dss-card">
                        <div class="dss-label">🚀 GELİŞİM</div>
                        <div class="dss-subtext" style="font-size: 0.65rem;">{metrics['skill_impact']}</div>
                        <span class="dss-delta dss-delta-up">Pozitif Katkı</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Stratejik Odak Dağılımı (Detaylı Görünüm)
                st.markdown("#### 🎯 Stratejik Odak ve Detay Analizi")
                
                alignment_data = metrics['strategic_alignment']
                values = alignment_data['values']
                descriptions = alignment_data['descriptions']
                
                col_f1, col_f2 = st.columns(2)
                
                for i, (theme, val) in enumerate(values.items()):
                    with col_f1 if i % 2 == 0 else col_f2:
                        st.markdown(f"""
                        <div class="focus-container">
                            <div class="focus-header">
                                <span>{theme}</span>
                                <span>%{val}</span>
                            </div>
                            <div class="focus-bar-bg">
                                <div class="focus-bar-fill" style="width: {val}%;"></div>
                            </div>
                            <div style="margin-top: 10px; font-size: 0.85rem; color: #475569; font-style: italic;">
                                💡 {descriptions.get(theme, "")}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.info("💡 **Gelecek Projeksiyonu:** Mevcut hedef seti, personelin teknik borç yükünü %15 azaltırken, kurumsal inovasyon kapasitesine doğrudan katkı sunmaktadır.")
                
                # --- YENİ: RİSK ANALİZİ KATMANI ---
                st.markdown("---")
                col_r1, col_r2 = st.columns([2, 2])
                with col_r1:
                    if st.button("⚠️ Detaylı Risk Analizi Yap", use_container_width=True):
                        with st.spinner("🔍 Risk kaynakları analiz ediliyor..."):
                            try:
                                history_df = load_history_cached(employee_name, target_type)
                                try:
                                    history_text = history_df.to_markdown(index=False) if not history_df.empty else "Veri yok"
                                except Exception:
                                    # Tabulate hatası veya başka bir hata durumunda CSV'ye dön
                                    history_text = history_df.to_csv(index=False) if not history_df.empty else "Veri yok"
                                risk_analysis = analyzer.analyze_risk_factors(employee_name, target_type, history_text)
                                st.session_state.detailed_risk = risk_analysis
                            except Exception as e:
                                st.error(f"Risk Analizi Hatası: {e}")

                if "detailed_risk" in st.session_state:
                    with st.expander("🛡️ Detaylı Risk Faktörleri ve Etki Analizi", expanded=True):
                        st.markdown(st.session_state.detailed_risk)
                        st.warning("⚠️ **Not:** Yukarıdaki riskler personelin geçmiş verileri ve görev tanımı üzerinden yapay zeka tarafından simüle edilmiştir.")

                st.markdown("---")
                # Word İndirme butonu
                dss_report = f"KARAR DESTEK RAPORU\nÇalışan: {employee_name}\nBaşarı Olasılığı: %{metrics['success_probability']}\nBenchmark: {metrics['benchmark_status']}"
                docx_dss = generate_docx(dss_report, title="Stratejik Karar Destek Raporu")
                st.download_button(
                    label="📄 DSS Raporunu Word'e Dönüştür",
                    data=docx_dss,
                    file_name=f"{employee_name}_karar_destek.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_dss_report"
                )
        else:
            st.warning("Lütfen bir çalışan seçiniz.")

    # GEÇMİŞ VERİ TABLOSU
    st.markdown("---")
    st.markdown(f"#### 📊 {employee_name} - {target_type} Verileri")
    
    if employee_name:
        history_df = load_history_cached(employee_name, target_type)
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
            st.info("Bu kriterlere uygun geçmiş sayısal veri bulunamadı.")
    else:
        st.info("Lütfen bir çalışan seçin.")

with main_col2:
    st.markdown("### 💬 Asistan ile Sohbet")
    
    # Sohbet Geçmişi Konteynerı
    chat_container = st.container(height=600, border=True)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align: center; color: #94a3b8; padding: 20px;">
                Henüz bir sohbet başlamadı.<br>
                Sol taraftan analiz başlatabilir veya aşağıdan soru sorabilirsiniz.
            </div>
            """, unsafe_allow_html=True)
            
        for i, (role, msg) in enumerate(st.session_state.chat_history):
            is_user = role == "Kullanıcı"
            with st.chat_message("user" if is_user else "ai", avatar="👤" if is_user else "🤖"):
                st.markdown(msg)
                if not is_user:
                    # Her asistan mesajı için Word butonu
                    docx_msg = generate_docx(msg, title="Asistan Yanıtı")
                    st.download_button(
                        label="📄 Word'e Dönüştür",
                        data=docx_msg,
                        file_name=f"asistan_yaniti_{i}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_chat_{i}"
                    )

    # Yeni Mesaj Girişi
    if prompt := st.chat_input("Sohbete devam etmek ister misiniz?"):
        st.session_state.chat_history.append(("Kullanıcı", prompt))
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
        with st.spinner("Yanıtlanıyor..."):
            try:
                # Sohbet için de Metadata ekleyelim
                loader = DataLoader()
                metadata = loader.get_employee_metadata(employee_name)
                metadata_context = ""
                if metadata:
                    metadata_context = f"Çalışan Bilgileri: {metadata}"

                response = analyzer.chat_with_data(
                    prompt, 
                    st.session_state.chat_history[:-1], 
                    employee_name if employee_name else "Genel",
                    metadata_context=metadata_context
                )
                
                st.session_state.chat_history.append(("Asistan", response))
                with chat_container:
                    with st.chat_message("ai", avatar="🤖"):
                        st.markdown(response)
            except Exception as e:
                st.error(f"Hata: {e}")
