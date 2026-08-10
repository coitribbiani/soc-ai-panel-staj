import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

# 1. Dosyaları Birleştir
df_orijinal = pd.read_csv("veriler.csv")
df_big = pd.read_csv("veriler_bigdata.csv")
df_birlesik = pd.concat([df_orijinal, df_big], ignore_index=True)

df_birlesik['_time'] = pd.to_datetime(df_birlesik['_time'], utc=True)
df_birlesik = df_birlesik.sort_values('_time').reset_index(drop=True)
df_birlesik.to_csv("veriler_birlesik.csv", index=False)
print(f"Birleştirme Başarılı! Toplam Log: {len(df_birlesik)}")

# 2. Pipeline'ı Birleşik Veride Çalıştır
df = df_birlesik.copy()
df['user'] = df['user'].fillna('unknown')
df['rhost'] = df['rhost'].fillna('unknown')

def compute_features(df, window_minutes=1):
    df['attempts_in_window'] = 0
    df['unique_users_in_window'] = 0
    df['seconds_since_last_attempt'] = np.nan
    
    for rhost, group in df.groupby('rhost'):
        group = group.sort_values('_time')
        times = group['_time'].values
        users = group['user'].values
        
        attempts_in_window = np.zeros(len(times))
        unique_users_in_window = np.zeros(len(times))
        seconds_since_last = np.full(len(times), np.nan)
        
        for i, t in enumerate(times):
            window_start = t - np.timedelta64(window_minutes, 'm')
            in_window = (times <= t) & (times > window_start)
            attempts_in_window[i] = in_window.sum()
            unique_users_in_window[i] = len(np.unique(users[in_window]))
            if i > 0:
                seconds_since_last[i] = (t - times[i - 1]) / np.timedelta64(1, 's')
                
        df.loc[group.index, 'attempts_in_window'] = attempts_in_window
        df.loc[group.index, 'unique_users_in_window'] = unique_users_in_window
        df.loc[group.index, 'seconds_since_last_attempt'] = seconds_since_last
    return df

df = compute_features(df)
df['seconds_since_last_attempt'] = df['seconds_since_last_attempt'].fillna(9999)
df['targets_root'] = (df['user'] == 'root').astype(int)

# 3. IP Özellikleri ve Yapay Zeka Modeli
ip_features = df.groupby('rhost').agg(
    total_attempts=('user', 'count'),
    unique_users_tried=('user', 'nunique'),
    first_seen=('_time', 'min'),
    last_seen=('_time', 'max'),
    max_burst_1min=('attempts_in_window', 'max'),
    targets_root_ratio=('targets_root', 'mean'),
).reset_index()

ip_features['duration_minutes'] = ((ip_features['last_seen'] - ip_features['first_seen']).dt.total_seconds() / 60)
ip_features['attempts_per_minute'] = np.where(
    ip_features['total_attempts'] > 1,
    ip_features['total_attempts'] / ip_features['duration_minutes'].clip(lower=1/60),
    0.0
)

X_ip = ip_features[['total_attempts', 'unique_users_tried', 'max_burst_1min', 'attempts_per_minute', 'targets_root_ratio']]
ip_model = IsolationForest(contamination=0.15, random_state=42)
ip_features['ip_anomaly'] = ip_model.fit_predict(X_ip)
ip_features['ip_anomaly'] = np.where((ip_features['ip_anomaly'] == -1) & (ip_features['total_attempts'] == 1), 1, ip_features['ip_anomaly'])
ip_features['ip_is_attacker'] = (ip_features['ip_anomaly'] == -1).astype(int)

ip_features.to_csv("saldirgan_ip_raporu.csv", index=False)

# 4. Risk Skorlama
def calculate_risk(row):
    if row['ip_is_attacker'] == 0: return 0 
    score = 10
    speed_score = min(40, row['attempts_per_minute'] * 1.5)
    target_score = row['targets_root_ratio'] * 30
    volume_score = min(20, row['total_attempts'] * 0.5)
    return min(100, round(score + speed_score + target_score + volume_score))

ip_features['risk_score'] = ip_features.apply(calculate_risk, axis=1)

def get_risk_level(score):
    if score == 0: return 'Güvenli'
    elif score < 40: return 'Düşük'
    elif score < 70: return 'Orta'
    elif score < 90: return 'Yüksek'
    else: return 'Kritik'

ip_features['risk_level'] = ip_features['risk_score'].apply(get_risk_level)
attackers = ip_features[ip_features['ip_is_attacker'] == 1].sort_values('risk_score', ascending=False)
rapor_sutunlar = ['rhost', 'risk_score', 'risk_level', 'total_attempts', 'attempts_per_minute', 'targets_root_ratio']
attackers[rapor_sutunlar].to_csv("risk_skorlari.csv", index=False)

print(f"Analiz Tamamlandı! Bulunan Saldırgan Sayısı: {len(attackers)}")