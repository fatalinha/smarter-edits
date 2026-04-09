import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ── Load & prepare ────────────────────────────────────────────────────────────
df = pd.read_csv('data/data.csv', encoding='latin-1')  # adjust path if needed
df['productivity (chr/s)'] = pd.to_numeric(df['productivity (chr/s)'], errors='coerce')
df['keystrokes']           = pd.to_numeric(df['keystrokes'],           errors='coerce')
df['HT_DA']                = pd.to_numeric(df['HT_DA'],                errors='coerce')

conditions  = [1, 2, 3, 4]
x_pos       = [0, 1, 2, 3]
cond_labels = ['PE \n(baseline)', 'H-QE', 'H-APE', 'S-APE']
colors      = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
               '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

# Variables: (column name, y-axis label, plot title)
variables = [
    ('productivity (chr/s)', 'Productivity (chr/s)',  'Productivity'),
    ('keystrokes',           'Keystrokes',             'Keystrokes'),
    ('HT_DA',                'HT_DA score',            'Translation quality (HT_DA)'),
]


# ── Helper: build wide PET x condition table ──────────────────────────────────
def get_wide(col):
    pc = df.groupby(['PET', 'condition'])[col].mean().reset_index()
    pc.columns = ['PET', 'condition', 'value']
    return pc.pivot(index='PET', columns='condition', values='value')


# ── Helper: RM-ANOVA on log-transformed data ──────────────────────────────────
def rm_anova_log(wide):
    """One-way repeated measures ANOVA on log(wide).
    Returns F, df_cond, df_error, p, partial eta-squared, GG epsilon."""
    wide_log = np.log(wide)
    n, k = wide_log.shape

    grand_mean = wide_log.values.mean()
    cond_means = wide_log.mean(axis=0).values
    subj_means = wide_log.mean(axis=1).values

    SS_cond = n * np.sum((cond_means - grand_mean) ** 2)
    SS_subj = k * np.sum((subj_means - grand_mean) ** 2)
    SS_total = np.sum((wide_log.values - grand_mean) ** 2)
    SS_error = SS_total - SS_cond - SS_subj

    df_cond = k - 1
    df_error = (k - 1) * (n - 1)
    MS_cond = SS_cond / df_cond
    MS_error = SS_error / df_error
    F_stat = MS_cond / MS_error

    # Greenhouse-Geisser epsilon
    Y_c = wide_log.values - wide_log.values.mean(axis=1, keepdims=True) \
          - wide_log.values.mean(axis=0) + grand_mean
    S = np.cov(Y_c.T)
    eps = np.clip((np.trace(S)) ** 2 / ((k - 1) * np.sum(S ** 2)), 1 / (k - 1), 1.0)

    # Mauchly's test (approximate)
    C = np.zeros((k, k - 1))
    for j in range(k - 1):
        C[:j + 1, j] = 1 / (j + 1)
        C[j + 1, j] = -1.0
        C[:, j] /= np.linalg.norm(C[:, j])
    Z = wide_log.values @ C
    Sc = np.cov(Z.T)
    W = np.linalg.det(Sc) / (np.trace(Sc) / (k - 1)) ** (k - 1)
    f = 1 - (2 * (k ** 2 - 3 * k + 3)) / (6 * (k - 1) * (n - 1))
    df_m = int(k * (k - 1) / 2 - 1)
    chi2_m = -np.log(max(W, 1e-10)) * (n - 1) * f
    p_m = 1 - stats.chi2.cdf(chi2_m, df_m)

    # Apply GG correction if sphericity violated
    if p_m < 0.05:
        df_c_corr = df_cond * eps
        df_e_corr = df_error * eps
        p_val = 1 - stats.f.cdf(F_stat, df_c_corr, df_e_corr)
        df_label = f'{df_c_corr:.2f}, {df_e_corr:.2f}'
        corrected = True
    else:
        p_val = 1 - stats.f.cdf(F_stat, df_cond, df_error)
        df_label = f'{df_cond}, {df_error}'
        corrected = False

    eta2 = SS_cond / (SS_cond + SS_error)
    return F_stat, df_label, p_val, eta2, corrected


# ── Helper: draw one slope graph onto an axis ─────────────────────────────────
def draw_slope(ax, wide, ylabel, title):
    pets = wide.index.tolist()

    # Group stats (on raw scale for the plot)
    group_means, ci_lower, ci_upper = [], [], []
    for c in conditions:
        vals = wide[c].dropna()
        m = vals.mean()
        ci = vals.sem() * stats.t.ppf(0.975, df=len(vals) - 1)
        group_means.append(m)
        ci_lower.append(m - ci)
        ci_upper.append(m + ci)

    # Friedman (raw data) - No Needed since we do ANOVA
    #groups = [wide[c].dropna().values for c in conditions]
    #f_stat, f_p = stats.friedmanchisquare(*groups)
    #f_sig = ('***' if f_p < .001 else '**' if f_p < .01 else
    #'*' if f_p < .05 else 'ns')

    # RM-ANOVA (log-transformed)
    F_a, df_label, p_a, eta2, corrected = rm_anova_log(wide.dropna())
    a_sig = ('***' if p_a < .001 else '**' if p_a < .01 else
    '*' if p_a < .05 else 'ns')
    gg_note = ' GG' if corrected else ''

    # Baseline shading
    ax.axvspan(-0.25, 0.25, alpha=0.06, color='#555555', zorder=0)

    # Individual PET lines
    for i, pet in enumerate(pets):
        y = [wide.loc[pet, c] for c in conditions]
        col = colors[i]
        ax.plot(x_pos, y, color=col, linewidth=1.6, alpha=0.7,
                marker='o', markersize=5.5, zorder=3)
        ax.text(-0.12, y[0], f'PET {pet}',
                ha='right', va='center', fontsize=7.5, color=col, fontweight='bold')
        ax.text(3.12, y[-1], f'PET {pet}',
                ha='left', va='center', fontsize=7.5, color=col, fontweight='bold')

    # Group mean + CI ribbon
    ax.plot(x_pos, group_means, color='#111111', linewidth=2.4,
            linestyle='--', marker='D', markersize=7, zorder=5)
    ax.fill_between(x_pos, ci_lower, ci_upper,
                    color='#111111', alpha=0.12, zorder=2)

    # Two-line annotation: Friedman + RM-ANOVA
    annot_text = (
        #f'Friedman: $\\chi^2$(3) = {f_stat:.2f}, $p$ = {f_p:.3f} ({f_sig})\n'
        f'RM-ANOVA{gg_note} (log): $F$({df_label}) = {F_a:.2f}, '
        f'$p$ = {p_a:.3f} ({a_sig}), $\\eta^2_p$ = {eta2:.3f}'
    )
    ax.annotate(
        annot_text,
        xy=(0.5, 0.02), xycoords='axes fraction',
        ha='center', va='bottom', fontsize=8, color='#333333',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#f5f5f5',
                  edgecolor='#cccccc', linewidth=0.8)
    )

    # Formatting
    ax.set_xticks(x_pos)
    ax.set_xticklabels(cond_labels, fontsize=9.5)
    ax.set_ylabel(ylabel, fontsize=10.5)
    ax.set_title(title, fontsize=11.5, fontweight='bold', pad=10)
    ax.set_xlim(-0.55, 3.55)
    ax.spines[['top', 'right']].set_visible(False)
    ax.yaxis.grid(True, linestyle=':', alpha=0.45, zorder=0)
    ax.set_axisbelow(True)


# ── Legend handles (shared across all figures) ────────────────────────────────
wide0 = get_wide(variables[0][0])
pets = wide0.index.tolist()
mean_line = plt.Line2D([0], [0], color='#111111', linewidth=2.4,
                       linestyle='--', marker='D', markersize=6,
                       label='Group mean')
ci_patch = mpatches.Patch(facecolor='#111111', alpha=0.15,
                          label='95% CI (group mean)')
pet_lines = [plt.Line2D([0], [0], color=colors[i], linewidth=1.6,
                        marker='o', markersize=5, label=f'PET {p}')
             for i, p in enumerate(pets)]
legend_handles = [mean_line, ci_patch] + pet_lines

# ── One figure per variable ───────────────────────────────────────────────────
for col, ylabel, title in variables:
    wide = get_wide(col)
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.suptitle('Individual PET trajectories across conditions\n'
                 'Group mean (dashed) ± 95% CI (shaded) | Baseline = Condition 1',
                 fontsize=13, fontweight='bold')
    draw_slope(ax, wide, ylabel, title)
    ax.legend(handles=legend_handles, fontsize=8.5, loc='lower center', ncol=5,
              bbox_to_anchor=(0.5, -0.22), framealpha=0.9, columnspacing=1.2)

    filename = col.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
    plt.tight_layout()
    plt.savefig(f'slope_{filename}.png', dpi=150, bbox_inches='tight')
    plt.savefig(f'slope_{filename}.pdf', bbox_inches='tight')
    plt.close()
    print(f"Saved: slope_{filename}.png / .pdf")
