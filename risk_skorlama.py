import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10

df_ips = pd.read_csv("saldirgan_ip_raporu.csv")

def calculate_risk(row):
    if row['ip_is_attacker'] == 0: return 0 
    score = 10
    speed_score = min(40, row['attempts_per_minute'] * 1.5)
    target_score = row['targets_root_ratio'] * 30
    volume_score = min(20, row['total_attempts'] * 0.5)
    return min(100, round(score + speed_score + target_score + volume_score))

df_ips['risk_score'] = df_ips.apply(calculate_risk, axis=1)

def get_risk_level(score):
    if score == 0: return 'Güvenli'
    elif score < 40: return 'Düşük'
    elif score < 70: return 'Orta'
    elif score < 90: return 'Yüksek'
    else: return 'Kritik'

df_ips['risk_level'] = df_ips['risk_score'].apply(get_risk_level)

attackers = df_ips[df_ips['ip_is_attacker'] == 1].sort_values('risk_score', ascending=False)
rapor_sutunlar = ['rhost', 'risk_score', 'risk_level', 'total_attempts', 'attempts_per_minute', 'targets_root_ratio']
attackers[rapor_sutunlar].to_csv("risk_skorlari.csv", index=False)

# GRAFİK: Sadece En Riskli 10 IP
top_attackers = attackers.head(10)
fig, ax = plt.subplots(figsize=(9, 5))

renkler = {'Kritik': '#7f1d1d', 'Yüksek': '#dc2626', 'Orta': '#f59e0b', 'Düşük': '#fcd34d'}
bar_renkleri = [renkler[level] for level in top_attackers['risk_level']]

bars = ax.barh(top_attackers['rhost'], top_attackers['risk_score'], color=bar_renkleri)
ax.set_xlabel('Tehdit Risk Skoru (0-100)')
ax.set_title('Yapay Zeka Destekli Dinamik IP Tehdit Skorlaması\n(En Riskli 10 IP)')
ax.set_xlim(0, 110)
ax.invert_yaxis() 
ax.spines[['top', 'right']].set_visible(False)

for bar in bars:
    width = bar.get_width()
    ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
            ha='left', va='center', fontweight='bold')

legend_elements = [Patch(facecolor=renkler[k], label=k) for k in renkler.keys()]
ax.legend(handles=legend_elements, loc='lower right', frameon=False, title="Risk Seviyesi")

plt.tight_layout()
plt.savefig('gorsel_5_risk_skorlari.png', bbox_inches='tight')
plt.close()