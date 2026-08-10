import pandas as pd
import urllib.request
import random
from datetime import datetime, timedelta
import ssl

print("1. Büyük veri seti oluşturuluyor ve orijinal verinle birleştiriliyor...")
ssl._create_default_https_context = ssl._create_unverified_context
gercek_saldirgan_ipler = [f"185.200.{i}.{random.randint(1,255)}" for i in range(30)]
try:
    url = "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req).read().decode('utf-8').split('\n')
    gercek_saldirgan_ipler = [line.split()[0] for line in data if not line.startswith("#") and len(line.strip())>0 and int(line.split()[1])>3][:30]
except:
    pass

normal_ipler = [f"{random.randint(10,250)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}" for _ in range(150)]
kullanicilar = ['root', 'admin', 'test', 'guest', 'ubuntu', 'oracle', 'postgres', 'user1']
log_listesi = []
baslangic_zamani = datetime(2026, 7, 20, 8, 0, 0)

for ip in normal_ipler:
    for _ in range(random.randint(1, 10)):
        log_listesi.append({'_time': baslangic_zamani + timedelta(days=random.randint(0, 5), hours=random.randint(0, 23), minutes=random.randint(0, 59)), 'rhost': ip, 'user': random.choice(kullanicilar[2:])})

for ip in gercek_saldirgan_ipler:
    saldiri_tipi = random.choice(['hizli_bruteforce', 'yavas_sinsi', 'sadece_root'])
    saldiri_zamani = baslangic_zamani + timedelta(days=random.randint(0, 5), hours=random.randint(0, 23))
    if saldiri_tipi == 'hizli_bruteforce':
        for i in range(random.randint(100, 400)): log_listesi.append({'_time': saldiri_zamani + timedelta(seconds=i*0.5), 'rhost': ip, 'user': random.choice(kullanicilar)})
    elif saldiri_tipi == 'yavas_sinsi':
        for i in range(random.randint(30, 80)): log_listesi.append({'_time': saldiri_zamani + timedelta(minutes=i*15), 'rhost': ip, 'user': random.choice(kullanicilar)})
    elif saldiri_tipi == 'sadece_root':
        for i in range(random.randint(80, 200)): log_listesi.append({'_time': saldiri_zamani + timedelta(seconds=i*2), 'rhost': ip, 'user': 'root'})

df_big = pd.DataFrame(log_listesi)
df_big['_time'] = df_big['_time'].dt.strftime('%Y-%m-%dT%H:%M:%S.000+0300')

try:
    df_orijinal = pd.read_csv("veriler.csv")
    df_birlesik = pd.concat([df_orijinal, df_big], ignore_index=True)
except:
    df_birlesik = df_big

df_birlesik['_time'] = pd.to_datetime(df_birlesik['_time'], utc=True)
df_birlesik = df_birlesik.sort_values('_time').reset_index(drop=True)
df_birlesik.to_csv("veriler_birlesik.csv", index=False)
print("2. İşlem tamam! 'veriler_birlesik.csv' dosyası klasöründe başarıyla oluşturuldu.")