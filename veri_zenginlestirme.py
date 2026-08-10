import pandas as pd
import numpy as np
import urllib.request
import random
from datetime import datetime, timedelta

print("1. GitHub üzerinden küresel Tehdit İstihbaratı (Threat Intel) listesi indiriliyor...")
url = "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req)
data = response.read().decode('utf-8').split('\n')

# Yorum satırlarını atla ve en tehlikeli gerçek saldırgan IP'leri al
gercek_saldirgan_ipler = []
for line in data:
    if not line.startswith("#") and len(line.strip()) > 0:
        parts = line.split()
        if len(parts) >= 2 and int(parts[1]) > 3: # Güven skoru düşük olanlar
            gercek_saldirgan_ipler.append(parts[0])
    if len(gercek_saldirgan_ipler) >= 30: # 30 farklı gerçek saldırgan yeterli
        break

print(f"Başarılı! Dünyaca bilinen {len(gercek_saldirgan_ipler)} gerçek saldırgan IP adresi çekildi.")

print("2. Büyük Veri (Big Data) seti oluşturuluyor (15.000+ Log Satırı)...")
normal_ipler = [f"{random.randint(10,250)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}" for _ in range(150)]
kullanicilar = ['root', 'admin', 'test', 'guest', 'ubuntu', 'oracle', 'postgres', 'user1']

log_listesi = []
baslangic_zamani = datetime(2026, 7, 20, 8, 0, 0)

# Normal trafik simülasyonu (Dağınık ve seyrek)
for ip in normal_ipler:
    deneme_sayisi = random.randint(1, 10)
    for _ in range(deneme_sayisi):
        zaman_sapmasi = timedelta(days=random.randint(0, 5), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        zaman = baslangic_zamani + zaman_sapmasi
        log_listesi.append({'_time': zaman, 'rhost': ip, 'user': random.choice(kullanicilar[2:])})

# Saldırgan trafik simülasyonu (Agresif ve yoğun)
for ip in gercek_saldirgan_ipler:
    saldiri_tipi = random.choice(['hizli_bruteforce', 'yavas_sinsi', 'sadece_root'])
    saldiri_zamani = baslangic_zamani + timedelta(days=random.randint(0, 5), hours=random.randint(0, 23))
    
    if saldiri_tipi == 'hizli_bruteforce':
        # 1 dakika içinde yüzlerce deneme
        for i in range(random.randint(100, 400)):
            log_listesi.append({'_time': saldiri_zamani + timedelta(seconds=i*0.5), 'rhost': ip, 'user': random.choice(kullanicilar)})
    
    elif saldiri_tipi == 'yavas_sinsi':
        # Saatlere yayılmış seyrek denemeler (Low and slow)
        for i in range(random.randint(30, 80)):
            log_listesi.append({'_time': saldiri_zamani + timedelta(minutes=i*15), 'rhost': ip, 'user': random.choice(kullanicilar)})
            
    elif saldiri_tipi == 'sadece_root':
        # Sadece root hesabını hızlıca zorlama
        for i in range(random.randint(80, 200)):
            log_listesi.append({'_time': saldiri_zamani + timedelta(seconds=i*2), 'rhost': ip, 'user': 'root'})

# Listeyi DataFrame'e çevir ve kronolojik sıraya diz
df_yeni = pd.DataFrame(log_listesi)
df_yeni = df_yeni.sort_values('_time').reset_index(drop=True)

# formatı veriler.csv'ye benzet
df_yeni['_time'] = df_yeni['_time'].dt.strftime('%Y-%m-%dT%H:%M:%S.000+0300')

print(f"3. İşlem tamamlandı! Toplam {len(df_yeni)} log satırı ve {df_yeni['rhost'].nunique()} farklı IP içeren devasa veri seti hazır.")
df_yeni.to_csv("veriler_bigdata.csv", index=False)
print("Veri 'veriler_bigdata.csv' olarak kaydedildi.")