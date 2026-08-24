import streamlit as st
import pandas as pd
import time
import requests
import os
import json
from PIL import Image

# Sayfa Ayarları
st.set_page_config(page_title="SOC AI Dashboard", layout="wide", page_icon="🛡️")
st.title("🛡️ SOC Yapay Zeka Tehdit Analiz Paneli")

# Veriyi Yükle
@st.cache_data
def load_data():
    try:
        return pd.read_csv("risk_skorlari.csv")
    except:
        return None

df_risk = load_data()

if df_risk is None:
    st.error("Veri bulunamadı. Lütfen önce risk_skorlama.py kodunu çalıştırın.")
    st.stop()

# Sol Menü
sekme = st.sidebar.radio("Analiz Menüsü", [
    "🚨 Canlı Tehdit Akışı", 
    "🌍 Saldırı Haritası",
    "📂 Geçmiş AI Alarmları", 
    "📊 Risk Skorları", 
    "📈 Analiz Grafikleri",
    "🧠 Açıklanabilir AI (XAI)"
])

if sekme == "🚨 Canlı Tehdit Akışı":
    st.subheader("🚨 Canlı Saldırı Bildirimleri")
    
    # Ngrok üzerinden veriyi çekiyoruz
    try:
        response = requests.get("https://autistic-pliable-grueling.ngrok-free.dev/alarms.json", headers={"ngrok-skip-browser-warning": "true"}, timeout=3)
        if response.status_code == 200:
            alarmlar = response.json()
            if alarmlar:
                for alarm in reversed(alarmlar[-50:]):
                    kaynak = alarm.get('kaynak', 'Bilinmiyor')
                    alarm_tipi = alarm.get('type', '')
                    
                    if alarm_tipi == 'INFO':
                        if 'portal' in kaynak.lower() or 'web' in kaynak.lower():
                            st.success(f"**🟢 Başarılı Portal Girişi:** \n\n **IP:** {alarm.get('ip', '')} | **Kullanıcı:** {alarm.get('user', '')} | **Hedef:** {kaynak}")
                        else:
                            st.success(f"**🟢 KRİTİK: SİSTEME SIZILDI! (Başarılı Oturum)** \n\n **IP:** {alarm.get('ip', '')} | **Kullanıcı:** {alarm.get('user', '')} | **Şifre:** {alarm.get('password', '')} | **Hedef:** {kaynak} | **AI Kararı:** {alarm.get('ai_risk_seviyesi', 'Bilinmiyor')}")
                    elif alarm_tipi == 'FAILED_LOGIN':
                        st.warning(f"**🟠 Hatalı Giriş Denemesi (Tekil):** \n\n **IP:** {alarm.get('ip', '')} | **Kullanıcı:** {alarm.get('user', '')} | **Şifre:** {alarm.get('password', '')} | **Hedef:** {kaynak} | **AI Kararı:** {alarm.get('ai_risk_seviyesi', 'Bilinmiyor')}")
                    elif alarm_tipi == 'SUCCESSFUL_LOGIN':
                        st.markdown(f"""
                        <div style="
                            background-color: #2b0000;
                            border: 2px solid #ff0000;
                            border-left: 10px solid #ff0000;
                            padding: 15px;
                            border-radius: 5px;
                            animation: siren_efekti 1s infinite;
                            margin-bottom: 10px;
                            color: #ffffff;
                        ">
                            <h3 style="color: #ff3333; margin-top: 0; text-shadow: 0 0 10px #ff0000;">
                                🚨 KRİTİK UYARI: SİSTEME SIZILDI! 🚨
                            </h3>
                            <div style="font-size: 15px;">
                                <strong>Hedef Sistem:</strong> {kaynak}<br>
                                <strong>Saldırgan IP:</strong> <code style="color: #ff6666; font-size: 16px;">{alarm.get('ip', '')}</code><br>
                                <strong>Ele Geçirilen Kimlik:</strong> {alarm.get('user', '')} / {alarm.get('password', '')}<br>
                                <div style="margin-top: 12px;">
                                    <span style="background-color: #cc0000; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid white;">
                                        AI Kararı: {alarm.get('ai_risk_seviyesi', 'Bilinmiyor')}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <style>
                        @keyframes siren_efekti {{
                            0% {{ box-shadow: 0 0 5px #ff0000; }}
                            50% {{ box-shadow: 0 0 25px #ff0000, inset 0 0 10px #ff0000; }}
                            100% {{ box-shadow: 0 0 5px #ff0000; }}
                        }}
                        </style>
                        """, unsafe_allow_html=True)
                    elif alarm_tipi == 'BRUTE_FORCE':
                        st.error(f"**🔴 Brute-Force Tehdidi Algılandı (Başarısız):** \n\n **IP:** {alarm.get('ip', '')} | **Kullanıcı:** {alarm.get('user', '')} | **Şifre:** {alarm.get('password', '')} | **Hedef:** {kaynak} | **AI Kararı:** {alarm.get('ai_risk_seviyesi', 'Kritik Risk')}")
                    elif alarm.get("type") == "COMMAND_EXECUTED":
                        st.info(f"💻 Komut Çalıştırıldı:\nIP: {alarm.get('ip')} | Komut: {alarm.get('password')} | Hedef: {alarm.get('kaynak')}")
                    else:
                        st.error(f"**🔴 Tanımlanamayan Tehdit Algılandı:** \n\n **IP:** {alarm.get('ip', '')} | **Kullanıcı:** {alarm.get('user', '')} | **Şifre:** {alarm.get('password', '')} | **Hedef:** {kaynak} | **AI Kararı:** {alarm.get('ai_risk_seviyesi', 'Bilinmiyor')}")
    except requests.exceptions.RequestException:
        st.warning("Ubuntu veri köprüsü (Ngrok) bekleniyor...")

    time.sleep(5)
    st.rerun()

elif sekme == "🌍 Saldırı Haritası":
    st.subheader("🌍 Saldırı Konumları (Dünya Haritası)")
    
    @st.cache_data
    def get_lat_lon(ip):
        try:
            res = requests.get(f"http://ip-api.com/json/{ip}").json()
            if res.get("status") == "success":
                return res["lat"], res["lon"]
        except:
            return None, None

    try:
        response = requests.get("https://autistic-pliable-grueling.ngrok-free.dev/alarms.json", headers={"ngrok-skip-browser-warning": "true"}, timeout=5)
        if response.status_code == 200:
            alarmlar = response.json()
            harita_verisi = []
            islenen_ipler = set()

            for alarm in alarmlar:
                ip = alarm.get("ip")
                if ip and ip != "Bilinmiyor" and ip not in islenen_ipler:
                    lat, lon = get_lat_lon(ip)
                    if lat and lon:
                        harita_verisi.append({"lat": lat, "lon": lon})
                    islenen_ipler.add(ip)

            if harita_verisi:
                df_map = pd.DataFrame(harita_verisi)
                st.map(df_map)
            else:
                st.info("Haritada gösterilecek geçerli konum bulunamadı.")
        else:
            st.error("Alarmlar dosyasına ulaşılamadı.")
    except requests.exceptions.RequestException:
        st.warning("Ubuntu veri köprüsü (Ngrok) bekleniyor...")

elif sekme == "📂 Geçmiş AI Alarmları":
    st.subheader("📂 Geçmiş AI Alarmları (CSV Verisi)")
    
    st.markdown("""
    <style>
    .yeni-etiket { display: inline-block; background-color: #ff4b4b; color: white; font-size: 11px; font-weight: bold; padding: 1px 7px; border-radius: 10px; margin-left: 8px; vertical-align: middle; }
    .akis-kutusu::-webkit-scrollbar { width: 6px; }
    .akis-kutusu::-webkit-scrollbar-thumb { background: #888; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)
    
    durum_alani = st.empty()
    akis_alani = st.empty()
    
    gosterilen_alarmlar = []
    
    for i in range(len(df_risk)):
        satir = df_risk.iloc[i]
        ikon = "🔴" if satir['risk_level'] in ['Kritik', 'Yüksek'] else "🟠"
        kenar_renk = "#ff4b4b" if satir['risk_level'] in ['Kritik', 'Yüksek'] else "#ffa421"
        
        veri = {
            "ikon": ikon,
            "renk": kenar_renk,
            "ip": satir['rhost'],
            "skor": satir['risk_score'],
            "seviye": satir['risk_level'],
            "hiz": round(satir['attempts_per_minute'], 1)
        }
        
        gosterilen_alarmlar.insert(0, veri)
        
        benzersiz_stil = f"""<style>
@keyframes slideIn_{i} {{
    0% {{ transform: translateX(60px) scale(0.95); opacity: 0; }}
    60% {{ transform: translateX(-4px) scale(1.02); opacity: 1; }}
    100% {{ transform: translateX(0) scale(1); opacity: 1; }}
}}
@keyframes flashHighlight_{i} {{
    0% {{ background-color: rgba(255, 75, 75, 0.55); }}
    100% {{ background-color: rgba(255, 75, 75, 0.1); }}
}}
@keyframes badgeFadeOut_{i} {{
    0% {{ opacity: 1; }}
    70% {{ opacity: 1; }}
    100% {{ opacity: 0; }}
}}
</style>
"""
        html_icerik = benzersiz_stil + '<div class="akis-kutusu" style="max-height: 500px; overflow-y: auto; overflow-x: hidden; padding-right: 10px;">\n'
        
        for idx, bildirim in enumerate(gosterilen_alarmlar):
            if idx == 0:
                anim_stil = (f'animation: slideIn_{i} 0.45s ease-out forwards, '
                             f'flashHighlight_{i} 1.6s ease-out forwards;')
                badge_anim_stil = f'animation: badgeFadeOut_{i} 4s ease-out forwards;'
                yeni_etiket_html = f'<span class="yeni-etiket" style="{badge_anim_stil}">YENİ</span>'
            else:
                anim_stil = 'animation: none;'
                yeni_etiket_html = ''

            html_icerik += f'<div style="{anim_stil} background-color: rgba(255, 75, 75, 0.1); border-left: 5px solid {bildirim["renk"]}; padding: 12px; margin-bottom: 10px; border-radius: 4px;">\n'
            html_icerik += f'<div style="font-weight: bold; font-size: 15px; margin-bottom: 5px;">{bildirim["ikon"]} ALARM TESPİT EDİLDİ!{yeni_etiket_html}</div>\n'
            html_icerik += f'<div style="font-size: 14px;"><strong>Saldırgan IP:</strong> <code>{bildirim["ip"]}</code> | <strong>AI Kararı:</strong> {bildirim["seviye"]} Risk (Skor: {bildirim["skor"]}) | <strong>Saldırı Hızı:</strong> {bildirim["hiz"]} deneme/dk</div>\n'
            html_icerik += '</div>\n'
            
        html_icerik += '</div>'
        
        akis_alani.markdown(html_icerik, unsafe_allow_html=True)
        time.sleep(0.5)
        
    durum_alani.success("✅ Tüm kuyruk incelendi. Sistem güvende.")

elif sekme == "📊 Risk Skorları":
    st.subheader("Yapay Zeka Tehdit Önceliklendirme Tablosu")
    st.dataframe(df_risk, use_container_width=True, height=300)
    
    try:
        st.image(Image.open("gorsel_5_risk_skorlari.png"), caption="Risk Skoru Sıralaması")
    except:
        pass

elif sekme == "📈 Analiz Grafikleri":
    st.subheader("Davranışsal Analiz ve IP Profilleri")
    col1, col2 = st.columns(2)
    
    try:
        col1.image(Image.open("gorsel_1_top_ipler.png"), use_container_width=True)
        col2.image(Image.open("gorsel_2_zaman_serisi.png"), use_container_width=True)
        col1.image(Image.open("gorsel_3_davranis_haritasi.png"), use_container_width=True)
        col2.image(Image.open("gorsel_4_yontem_karsilastirma.png"), use_container_width=True)
    except:
        st.warning("Grafik dosyaları klasörde bulunamadı.")

elif sekme == "🧠 Açıklanabilir AI (XAI)":
    st.subheader("Model Karar Faktörleri (Kara Kutu Analizi)")
    st.write("Sistemimiz bir kara kutu değildir. Aşağıdaki grafik, modelin bir IP'yi neden 'saldırgan' olarak işaretlediğini (hız, hacim veya kritik hedef seçimi) kanıtlamaktadır.")
    
    try:
        st.image(Image.open("gorsel_6_xai_faktörleri.png"), use_container_width=True)
    except:
        st.warning("gorsel_6_xai_faktörleri.png dosyası bulunamadı.")
