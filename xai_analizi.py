import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10

# 1. VERİYİ YÜKLE
df = pd.read_csv("saldirgan_ip_raporu.csv")

# Sadece saldırganları (en şüpheli 10 IP) seç
attackers = df[df['ip_is_attacker'] == 1].sort_values('ip_anomaly_score').head(35)

# 2. ÖZELLİKLERİ NORMALİZE ET
ozellikler = ['attempts_per_minute', 'total_attempts', 'targets_root_ratio']
etiketler = ['Saldırı Hızı', 'Saldırı Hacmi', 'Root Hedefleme']

scaler = MinMaxScaler()
scaler.fit(df[ozellikler])
norm_data = scaler.transform(attackers[ozellikler])

norm_df = pd.DataFrame(norm_data, columns=etiketler, index=attackers['rhost'])
norm_df['Toplam'] = norm_df.sum(axis=1)
norm_df.replace(0, 0.001, inplace=True) 
yuzdelikler = norm_df[etiketler].div(norm_df['Toplam'], axis=0) * 100

# 3. GRAFİĞİ ÇİZ
fig, ax = plt.subplots(figsize=(11, 7)) # Boyut biraz genişletildi

renkler = ['#2563eb', '#94a3b8', '#dc2626']
yuzdelikler.plot(kind='barh', stacked=True, color=renkler, ax=ax, width=0.7)

ax.set_xlabel('Anomali Kararına Etki Oranı (%)', labelpad=15)
ax.set_title('Açıklanabilir Yapay Zeka (XAI) - Model Karar Faktörleri\n"Model bu IP\'yi neden seçti?"', pad=20, fontweight='bold')
ax.set_xlim(0, 100)
ax.spines[['top', 'right']].set_visible(False)

# Lejant çakışmayı önlemek için alta alındı
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)

plt.tight_layout()
plt.savefig('gorsel_6_xai_faktörleri.png', bbox_inches='tight')
plt.close()

print("Görsel 6 düzeltildi ve kaydedildi.")