import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

# ============================================================
# 1. VERIYI YUKLE VE HAZIRLA
# ============================================================
df = pd.read_csv("veriler_birlesik.csv")



pd.read_csv("veriler_birlesik.csv")

df['user'] = df['user'].fillna('unknown')
df['rhost'] = df['rhost'].fillna('unknown')
df['_time'] = pd.to_datetime(df['_time'])

# Kronolojik sıraya koy - zaman penceresi hesapları için sıra önemli
df = df.sort_values('_time').reset_index(drop=True)

# ============================================================
# 2. OZELLIK MUHENDISLIGI (asil gelistirme burada)
# Eski model sadece saat + kullanici adini kullaniyordu.
# Brute-force'u ele veren asil sinyal: AYNI IP'DEN KISA SUREDE
# COK DENEME ve FARKLI KULLANICI ADLARI DENEMESI.
# ============================================================

def compute_features_v2(df, window_minutes=1):
    """Her rhost (IP) icin, gecmis N dakika icindeki deneme sayisi,
    farkli kullanici adi sayisi ve son denemeden bu yana gecen sureyi hesaplar."""
    df = df.copy()
    df['attempts_in_window'] = 0
    df['unique_users_in_window'] = 0
    df['seconds_since_last_attempt'] = np.nan

    for rhost, group in df.groupby('rhost'):
        group = group.sort_values('_time')
        times = group['_time']
        users = group['user']

        attempts_in_window = []
        unique_users_in_window = []
        seconds_since_last = []

        for i, t in enumerate(times):
            window_start = t - pd.Timedelta(minutes=window_minutes)
            in_window = (times <= t) & (times > window_start)
            attempts_in_window.append(in_window.sum())
            unique_users_in_window.append(users[in_window].nunique())
            if i == 0:
                seconds_since_last.append(np.nan)
            else:
                seconds_since_last.append(
                    (t - times.iloc[i - 1]).total_seconds()
                )

        df.loc[group.index, 'attempts_in_window'] = attempts_in_window
        df.loc[group.index, 'unique_users_in_window'] = unique_users_in_window
        df.loc[group.index, 'seconds_since_last_attempt'] = seconds_since_last

    return df


df = compute_features_v2(df, window_minutes=1)

# Eksik "ilk deneme" değerlerini pencerenin üstünde bir değerle doldur
# (ilk deneme kimseyi tehdit etmiyor, o yüzden yüksek bir "sakin" değer veriyoruz)
df['seconds_since_last_attempt'] = df['seconds_since_last_attempt'].fillna(9999)

# Saat bilgisi (0-23) - mesai dışı saatler daha şüpheli olabilir
df['hour'] = df['_time'].dt.hour

# root kullanıcı hedefleniyor mu (yaygın bir saldırı hedefi)
df['targets_root'] = (df['user'] == 'root').astype(int)

# ============================================================
# 3. MODELIN KULLANACAGI OZELLIKLER
# Eski: ['date_hour', 'user_encoded']  -> anlamsiz siralama + zayif sinyal
# Yeni: davranissal, zaman pencereli, güvenlik mantığına dayalı özellikler
# ============================================================
FEATURES = [
    'attempts_in_window',
    'unique_users_in_window',
    'seconds_since_last_attempt',
    'hour',
    'targets_root',
]
X = df[FEATURES]

# ============================================================
# 4. KURAL TABANLI REFERANS ETIKET
# Once bunu hesapliyoruz cunku contamination kalibrasyonunda
# "zayif/gurultulu referans etiket" olarak kullanacagiz.
# Literaturde yaygin brute-force esigi: ayni IP'den 1 dakikada 5+ deneme
# ============================================================
RULE_THRESHOLD = 5
df['rule_flag'] = (df['attempts_in_window'] >= RULE_THRESHOLD).astype(int)

# ============================================================
# 5. CONTAMINATION KALIBRASYONU (veri odakli, sabit %5 varsayimi yerine)
# Eski kodda contamination=0.05 rastgele/sabit bir varsayimdi.
# Burada farkli contamination degerlerini deneyip, kural tabanli
# etikete en yakin sonucu veren degeri otomatik seciyoruz.
# NOT: rule_flag mukemmel bir "gercek" etiket degil (o da bir varsayim),
# ama sabit bir sayidan cok daha guclu bir referans noktasi.
# ============================================================
from sklearn.metrics import f1_score, precision_score, recall_score

# sklearn IsolationForest contamination icin ust sinir 0.5'tir
# (yani "verinin en fazla yarisi anomali" varsayimini asamiyoruz)
candidate_values = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
calibration_results = []

for c in candidate_values:
    trial_model = IsolationForest(contamination=c, random_state=42)
    trial_pred = trial_model.fit_predict(X)
    trial_flag = (trial_pred == -1).astype(int)

    f1 = f1_score(df['rule_flag'], trial_flag)
    prec = precision_score(df['rule_flag'], trial_flag, zero_division=0)
    rec = recall_score(df['rule_flag'], trial_flag, zero_division=0)
    calibration_results.append({'contamination': c, 'f1': f1, 'precision': prec, 'recall': rec})

calibration_df = pd.DataFrame(calibration_results)
best_row = calibration_df.loc[calibration_df['f1'].idxmax()]
BEST_CONTAMINATION = best_row['contamination']

print("=" * 60)
print("CONTAMINATION KALIBRASYON TABLOSU")
print("=" * 60)
print(calibration_df.to_string(index=False))
print(f"\nSecilen contamination degeri: {BEST_CONTAMINATION} "
      f"(F1={best_row['f1']:.3f}, kural tabanli etikete gore)")

if BEST_CONTAMINATION == max(candidate_values):
    print("\n[ONEMLI BULGU] F1 skoru, denenen ust sinira (0.5) kadar artmaya devam etti.")
    print("Bu, IsolationForest'in 'anomaliler azinliktadir' varsayiminin bu veri seti")
    print("icin gecerli olmadigini gosteriyor: kayitlarin buyuk bir kismi zaten")
    print("aktif/surekli bir saldiri kampanyasina ait olabilir, tekil/seyrek bir")
    print("anomaliye degil. Bu durum raporda bir 'model siniri' olarak belirtilmeli.")

# ============================================================
# 6. ISOLATION FOREST MODELI (kalibre edilmis contamination ile)
# ============================================================
model = IsolationForest(contamination=BEST_CONTAMINATION, random_state=42)
df['ml_anomaly'] = model.fit_predict(X)
# skoru da tutalim - "ne kadar anormal" bilgisi rapor icin degerli
df['ml_anomaly_score'] = model.decision_function(X)

ml_flagged = df[df['ml_anomaly'] == -1]
rule_flagged = df[df['rule_flag'] == 1]
both_flagged = df[(df['ml_anomaly'] == -1) & (df['rule_flag'] == 1)]
only_ml = df[(df['ml_anomaly'] == -1) & (df['rule_flag'] == 0)]
only_rule = df[(df['ml_anomaly'] != -1) & (df['rule_flag'] == 1)]

# ============================================================
# 7. RAPOR CIKTISI
# ============================================================
print("=" * 60)
print("BRUTE-FORCE ANOMALI TESPIT RAPORU (v2)")
print("=" * 60)
print(f"Toplam incelenen log sayisi        : {len(df)}")
print(f"AI (Isolation Forest) ile isaretlenen : {len(ml_flagged)}")
print(f"Kural tabanli ile isaretlenen        : {len(rule_flagged)} (esik: {RULE_THRESHOLD}+ deneme/dk)")
print(f"Her iki yontemin ortak isaretledigi  : {len(both_flagged)}")
print(f"Sadece AI'nin yakaladigi             : {len(only_ml)}")
print(f"Sadece kuralin yakaladigi            : {len(only_rule)}")

print("\nEn supheli 10 IP (rhost) - toplam deneme sayisina gore:")
print(df['rhost'].value_counts().head(10))

print("\nOrnek AI tarafindan isaretlenen supheli islemler:")
print(ml_flagged[['_time', 'rhost', 'user', 'attempts_in_window',
                   'unique_users_in_window', 'ml_anomaly_score']].head(10))

# ============================================================
# 9. IP-DUZEYINDE ANOMALI TESPITI (mimari duzeltme)
# Onceki bolumlerde ortaya cikan bulgu: satir bazli yaklasimda
# veri neredeyse tamamen "anomali" gorunuyordu, cunku dogru birim
# tek bir log satiri degil, bir IP'nin GENEL DAVRANISI'dir.
# Burada her rhost (IP) icin BIR ozet satir cikarip, IsolationForest'i
# 47 IP uzerinde calistiriyoruz - bu da "anomaliler azinliktadir"
# varsayimini gecerli kilan dogru birim secimidir.
# ============================================================
print("\n" + "=" * 60)
print("IP-DUZEYINDE ANOMALI TESPITI (asil mimari duzeltme)")
print("=" * 60)

ip_features = df.groupby('rhost').agg(
    total_attempts=('user', 'count'),
    unique_users_tried=('user', 'nunique'),
    first_seen=('_time', 'min'),
    last_seen=('_time', 'max'),
    max_burst_1min=('attempts_in_window', 'max'),
    targets_root_ratio=('targets_root', 'mean'),
).reset_index()

ip_features['duration_minutes'] = (
    (ip_features['last_seen'] - ip_features['first_seen']).dt.total_seconds() / 60
)

# saldiri hizi: dakikada ortalama kac deneme
# ONEMLI DUZELTME: tek denemelik IP'lerde "hiz" kavrami anlamsizdir
# (bir tek basarisiz giriş, hizli/yavas diye siniflandirilamaz). Bunlari
# 0'a sabitliyoruz, aksi halde suresi ~0 olan tek-deneme kayitlari
# yapay olarak "cok hizli" gorunup yanlis pozitif uretiyor.
ip_features['attempts_per_minute'] = np.where(
    ip_features['total_attempts'] > 1,
    ip_features['total_attempts'] / ip_features['duration_minutes'].clip(lower=1/60),
    0.0
)

IP_FEATURES = [
    'total_attempts',
    'unique_users_tried',
    'max_burst_1min',
    'attempts_per_minute',
    'targets_root_ratio',
]
X_ip = ip_features[IP_FEATURES]

# Artik dogru birimdeyiz (IP), o yuzden "gercekci" bir contamination
# varsayimina donebiliyoruz: 47 IP'nin kucuk bir kismi gercekten
# yogun/otomatik saldiri paterni gosteriyor olmali.
ip_model = IsolationForest(contamination=0.15, random_state=42)
ip_features['ip_anomaly'] = ip_model.fit_predict(X_ip)
ip_features['ip_anomaly_score'] = ip_model.decision_function(X_ip)

# DOMAIN FILTRESI: tek bir basarisiz giris denemesi, tanim olarak bir
# "davranis paterni" olusturamaz - IsolationForest kucuk ornek boyutunda
# (48 IP) hem cok yuksek hem cok DUSUK aktiviteyi "anormal" sayabiliyor.
# Brute-force acisindan bizi ilgilendiren sadece yuksek uctaki anomaliler,
# o yuzden tek-denemelik IP'leri saldirgan etiketinden manuel olarak disliyoruz.
ip_features['ip_anomaly'] = np.where(
    (ip_features['ip_anomaly'] == -1) & (ip_features['total_attempts'] == 1),
    1,  # tek deneme varsa, model ne derse desin "saldirgan degil" say
    ip_features['ip_anomaly']
)

flagged_ips = ip_features[ip_features['ip_anomaly'] == -1].sort_values(
    'ip_anomaly_score'
)

print(f"Toplam farkli IP (rhost) sayisi      : {len(ip_features)}")
print(f"Saldirgan olarak isaretlenen IP sayisi : {len(flagged_ips)}")
print("\nEn supheli IP'ler (siniralanmis skora gore, en supheliden basliyor):")
print(flagged_ips[['rhost', 'total_attempts', 'unique_users_tried',
                    'attempts_per_minute', 'duration_minutes',
                    'ip_anomaly_score']].to_string(index=False))

# Bu IP-duzeyi sonucu, orijinal satir-bazli df'e geri isle
# (her log satirina, o satirin ait oldugu IP'nin saldirgan olup olmadigi bilgisini ekle)
df = df.merge(
    ip_features[['rhost', 'ip_anomaly', 'ip_anomaly_score']],
    on='rhost', how='left'
)
df.rename(columns={'ip_anomaly': 'ip_is_attacker'}, inplace=True)
df['ip_is_attacker'] = (df['ip_is_attacker'] == -1).astype(int)

print(f"\nBu {len(flagged_ips)} saldirgan IP, toplam {df['ip_is_attacker'].sum()} "
      f"log satirinin kaynagi (tum satirlarin %{100*df['ip_is_attacker'].mean():.0f}'i).")

# ============================================================
# 11. IP-DUZEYINDE KARSILASTIRMA: AI vs KURAL TABANLI
# Kural tabanli yöntemin IP-duzeyi karsiligi: bir IP, herhangi bir
# anda (herhangi bir log satirinda) esigi (5+ deneme/dk) gecmisse
# o IP "kural tabanli" olarak saldirgan sayilir.
# ============================================================
ip_rule_flag = df.groupby('rhost')['rule_flag'].max().rename('ip_rule_flag')
ip_features = ip_features.merge(ip_rule_flag, on='rhost', how='left')
ip_features['ip_is_attacker'] = (ip_features['ip_anomaly'] == -1).astype(int)

ip_both = ip_features[(ip_features['ip_is_attacker'] == 1) & (ip_features['ip_rule_flag'] == 1)]
ip_only_ai = ip_features[(ip_features['ip_is_attacker'] == 1) & (ip_features['ip_rule_flag'] == 0)]
ip_only_rule = ip_features[(ip_features['ip_is_attacker'] == 0) & (ip_features['ip_rule_flag'] == 1)]
ip_neither = ip_features[(ip_features['ip_is_attacker'] == 0) & (ip_features['ip_rule_flag'] == 0)]

ip_f1 = f1_score(ip_features['ip_rule_flag'], ip_features['ip_is_attacker'])
ip_prec = precision_score(ip_features['ip_rule_flag'], ip_features['ip_is_attacker'], zero_division=0)
ip_rec = recall_score(ip_features['ip_rule_flag'], ip_features['ip_is_attacker'], zero_division=0)

print("\n" + "=" * 60)
print("IP-DUZEYINDE KARSILASTIRMA: AI vs KURAL TABANLI")
print("=" * 60)
print(f"Toplam IP sayisi                         : {len(ip_features)}")
print(f"Kural tabanli saldirgan sayan IP sayisi   : {int(ip_features['ip_rule_flag'].sum())}")
print(f"AI'nin saldirgan sayidigi IP sayisi        : {int(ip_features['ip_is_attacker'].sum())}")
print(f"Her iki yontemin ortak isaretledigi        : {len(ip_both)}")
print(f"Sadece AI'nin yakaladigi                   : {len(ip_only_ai)}")
print(f"Sadece kuralin yakaladigi                  : {len(ip_only_rule)}")
print(f"Her ikisinin de temiz saydigi               : {len(ip_neither)}")
print(f"\nUyum metrikleri (kural tabanli 'referans' sayilirsa):")
print(f"  Precision : {ip_prec:.3f}   (AI'nin saldirgan dedigi IP'lerin ne kadari kural ile de ortusuyor)")
print(f"  Recall    : {ip_rec:.3f}   (Kuralin yakaladigi IP'lerin ne kadarini AI de yakaladi)")
print(f"  F1        : {ip_f1:.3f}")

if len(ip_only_rule) > 0:
    print("\nSadece kural tabanli yontemin yakaladigi, AI'nin kacirdigi IP'ler:")
    print(ip_only_rule[['rhost', 'total_attempts', 'attempts_per_minute',
                         'duration_minutes']].to_string(index=False))
    print("(Not: bunlar genellikle kisa bir aninda esigi gecip sonra duran,")
    print(" ama GENEL ORTALAMASI dusuk kalan IP'ler olabilir - anlik patlama")
    print(" ile genel davranis ortalamasi arasindaki farktir bu.)")

if len(ip_only_ai) > 0:
    print("\nSadece AI'nin yakaladigi, kuralin kacirdigi IP'ler:")
    print(ip_only_ai[['rhost', 'total_attempts', 'attempts_per_minute',
                       'duration_minutes']].to_string(index=False))

# ============================================================
# 10. DOSYAYA KAYDET
# ============================================================
df.to_csv("anomaliler_raporu_v2.csv", index=False)
ip_features.to_csv("saldirgan_ip_raporu.csv", index=False)
print("\nSatir bazli tum sonuclar 'anomaliler_raporu_v2.csv' dosyasina kaydedildi.")
print("IP bazli ozet sonuclar  'saldirgan_ip_raporu.csv' dosyasina kaydedildi.")
print("(Kolonlar: attempts_in_window, unique_users_in_window, ml_anomaly, rule_flag, ip_is_attacker vb.)")
