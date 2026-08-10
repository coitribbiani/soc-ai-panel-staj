import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10

df = pd.read_csv("anomaliler_raporu_v2.csv", parse_dates=['_time'])
ip_df = pd.read_csv("saldirgan_ip_raporu.csv")

RENK_NORMAL = '#94a3b8'   
RENK_SALDIRGAN = '#dc2626'  
RENK_VURGU = '#2563eb'    

# GORSEL 1
fig, ax = plt.subplots(figsize=(9, 5.5))
top10 = ip_df.sort_values('total_attempts', ascending=True).tail(10)
colors = [RENK_SALDIRGAN if a else RENK_NORMAL for a in top10['ip_is_attacker']]
ax.barh(top10['rhost'], top10['total_attempts'], color=colors)
ax.set_xlabel('Toplam basarisiz giris denemesi')
ax.set_title('En Cok Deneme Yapan 10 IP\n(kirmizi = AI tarafindan saldirgan olarak isaretlendi)')
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('gorsel_1_top_ipler.png', bbox_inches='tight')
plt.close()

# GORSEL 2
fig, ax = plt.subplots(figsize=(11, 5))
normal = df[df['ip_is_attacker'] == 0]
saldirgan = df[df['ip_is_attacker'] == 1]
ax.scatter(normal['_time'], normal['attempts_in_window'], s=25, color=RENK_NORMAL, alpha=0.6, label='Normal IP trafiği')
ax.scatter(saldirgan['_time'], saldirgan['attempts_in_window'], s=35, color=RENK_SALDIRGAN, alpha=0.8, label='Saldırgan IP (AI)')
ax.set_ylabel('1 dakikalık pencerede deneme sayısı')
ax.set_title('Zaman İçinde Giriş Denemesi Yoğunluğu')
ax.legend(loc='upper left', frameon=False)
ax.spines[['top', 'right']].set_visible(False)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig('gorsel_2_zaman_serisi.png', bbox_inches='tight')
plt.close()

# GORSEL 3 (Sadece Top 5 Etiketi)
fig, ax = plt.subplots(figsize=(8, 6.5))
normal_ip = ip_df[ip_df['ip_is_attacker'] == 0]
saldirgan_ip = ip_df[ip_df['ip_is_attacker'] == 1]
ax.scatter(normal_ip['total_attempts'], normal_ip['attempts_per_minute'], s=80, color=RENK_NORMAL, alpha=0.7, edgecolors='white')
ax.scatter(saldirgan_ip['total_attempts'], saldirgan_ip['attempts_per_minute'], s=140, color=RENK_SALDIRGAN, alpha=0.9, edgecolors='white')

# Yazı karmaşasını önlemek için sadece en belirgin 5 saldırganı yaz
for _, row in saldirgan_ip.nlargest(5, 'total_attempts').iterrows():
    ax.annotate(row['rhost'][:20], (row['total_attempts'], row['attempts_per_minute']),
                textcoords="offset points", xytext=(8, 5), fontsize=8, color=RENK_SALDIRGAN)

ax.set_xlabel('Toplam deneme sayısı')
ax.set_ylabel('Saldırı hızı (deneme / dakika, log ölçek)')
ax.set_title('IP Davranış Haritası')
ax.set_yscale('symlog')
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('gorsel_3_davranis_haritasi.png', bbox_inches='tight')
plt.close()

# GORSEL 4 (Dinamik IP Sayısı)
kural_flag = ip_df['ip_rule_flag'].astype(bool)
ai_flag = ip_df['ip_is_attacker'].astype(bool)
kategoriler = {
    'Her ikisi de\nsaldırgan diyor': ((kural_flag) & (ai_flag)).sum(),
    'Sadece kural\nsaldırgan diyor': ((kural_flag) & (~ai_flag)).sum(),
    'Sadece AI\nsaldırgan diyor': ((~kural_flag) & (ai_flag)).sum(),
    'Her ikisi de\ntemiz diyor': ((~kural_flag) & (~ai_flag)).sum(),
}
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(kategoriler.keys(), kategoriler.values(), color=[RENK_VURGU, '#f59e0b', RENK_SALDIRGAN, RENK_NORMAL])
for bar, val in zip(bars, kategoriler.values()):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.5, str(val), ha='center', fontweight='bold')
ax.set_ylabel('IP sayısı')
ax.set_title(f'AI ve Kural Tabanlı Yöntemin IP Düzeyinde Uyumu\n(Toplam {len(ip_df)} IP)')
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('gorsel_4_yontem_karsilastirma.png', bbox_inches='tight')
plt.close()