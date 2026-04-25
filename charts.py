#!/usr/bin/env python3
"""
Benchmark visualization for IoT time-series DB comparison (InfluxDB, TimescaleDB, IoTDB).

Usage:
  python3 charts.py [--source small|medium|large] [--language en-us|pt-br]

Dependencies: matplotlib numpy pandas
On NixOS/nix develop: matplotlib, numpy, pandas are included in the dev shell.
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

DBS = ['INFLUXDB', 'TIMESCALEDB', 'IOTDB']
DB_COLORS = {'INFLUXDB': '#E8734A', 'TIMESCALEDB': '#2E8BC0', 'IOTDB': '#3CB043'}
DB_LABELS = {'INFLUXDB': 'InfluxDB', 'TIMESCALEDB': 'TimescaleDB', 'IOTDB': 'IoTDB'}

# Consecutive scale pairs used by comparison charts (4 & 5)
SCALE_PAIRS = {
    'small':  ('small',  'medium'),
    'medium': ('small',  'medium'),
    'large':  ('medium', 'large'),
}

# ---------------------------------------------------------------------------
# Localisation strings
# ---------------------------------------------------------------------------
STRINGS = {
    'en-us': {
        # shared
        'log_scale':        '— log scale',
        'throughput_label': 'Throughput (pts/s)',
        'avg_lat_label':    'Average Latency (ms)',
        'mem_label':        'Memory (MB)',
        'small_label':      'Small',
        'medium_label':     'Medium',
        'large_label':      'Large',
        'saved':            'Saved',
        'done':             'Done! All charts saved to',
        'generating':       'Generating charts...\n',
        'skipping':         'Skipping charts 4 & 5: {} not found.',
        'avg_mem_legend':   'Average Memory',
        'peak_gap_legend':  'Peak − Average',
        'avg_lat_legend':   'Average Latency',
        'p99_gap_legend':   'Gap to P99',
        # chart 1
        'c1_title':   'Chart 1 — Write King: Throughput by Database',
        'c1_xlabel':  'Write Test Type',
        'c1_ylabel':  'Throughput (pts/s) — log scale',
        # chart 2
        'c2_title':   'Chart 2 — Efficiency Profile (WRITE test, {scale} scale)\n1 = best performance',
        'c2_axes':    ['Throughput', 'Avg Latency\n(↑=better)', 'P99 Latency\n(↑=better)',
                       'Avg CPU\n(↑=better)', 'Peak Mem\n(↑=better)'],
        # chart 3
        'c3_title':   'Chart 3 — Cost × Benefit: Memory vs Throughput ({scale} scale)',
        'c3_xlabel':  'Peak Memory (MB) — log scale',
        'c3_ylabel':  'Throughput (pts/s) — log scale',
        'c3_heroes':  '← Heroes\n(high perf., low resource)',
        'c3_villains':'Villains →\n(low perf., high resource)',
        # chart 4
        'c4_title':   'Chart 4 — Latency Heatmap: {scale_a} → {scale_b} scale\nGreen = stable  |  Red = high degradation',
        'c4_cbar':    'Avg latency increase (%)',
        # chart 5
        'c5_title':   'Chart 5 — Scalability: Avg Latency {scale_a} → {scale_b}',
        # chart 6
        'c6_title':   'Chart 6 — P99 Consistency: Average + Gap to P99 ({scale} scale)',
        'c6_ylabel':  'Latency (ms)',
        # chart 7
        'c7_title':   'Chart 7 — Memory Footprint by Test ({scale} scale)\nSolid = average  |  Dashed = peak',
    },
    'pt-br': {
        # shared
        'log_scale':        '— escala logarítmica',
        'throughput_label': 'Throughput (pts/s)',
        'avg_lat_label':    'Latência Média (ms)',
        'mem_label':        'Memória (MB)',
        'small_label':      'Small',
        'medium_label':     'Medium',
        'large_label':      'Large',
        'saved':            'Salvo',
        'done':             'Pronto! Todos os gráficos salvos em',
        'generating':       'Gerando gráficos...\n',
        'skipping':         'Pulando gráficos 4 e 5: {} não encontrado.',
        'avg_mem_legend':   'Memória Média',
        'peak_gap_legend':  'Pico − Média',
        'avg_lat_legend':   'Latência Média',
        'p99_gap_legend':   'Folga até P99',
        # chart 1
        'c1_title':   'Gráfico 1 — Rei da Escrita: Throughput por Banco de Dados',
        'c1_xlabel':  'Tipo de Teste de Escrita',
        'c1_ylabel':  'Throughput (pts/s) — escala logarítmica',
        # chart 2
        'c2_title':   'Gráfico 2 — Perfil de Eficiência (teste WRITE, escala {scale})\n1 = melhor desempenho',
        'c2_axes':    ['Throughput', 'Lat. Média\n(↑=melhor)', 'Lat. P99\n(↑=melhor)',
                       'CPU Média\n(↑=melhor)', 'Mem. Pico\n(↑=melhor)'],
        # chart 3
        'c3_title':   'Gráfico 3 — Custo × Benefício: Memória vs Throughput (escala {scale})',
        'c3_xlabel':  'Memória Pico (MB) — escala logarítmica',
        'c3_ylabel':  'Throughput (pts/s) — escala logarítmica',
        'c3_heroes':  '← Heróis\n(alta perf., baixo recurso)',
        'c3_villains':'Vilões →\n(baixa perf., alto recurso)',
        # chart 4
        'c4_title':   'Gráfico 4 — Heatmap de Latência: {scale_a} → {scale_b}\nVerde = estável  |  Vermelho = alta degradação',
        'c4_cbar':    'Aumento de latência média (%)',
        # chart 5
        'c5_title':   'Gráfico 5 — Escalabilidade: Latência Média {scale_a} → {scale_b}',
        # chart 6
        'c6_title':   'Gráfico 6 — Consistência P99: Média + Folga até P99 (escala {scale})',
        'c6_ylabel':  'Latência (ms)',
        # chart 7
        'c7_title':   'Gráfico 7 — Footprint de Memória por Teste (escala {scale})\nLinha sólida = média  |  Linha tracejada = pico',
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def t(strings, key, **fmt):
    """Return localised string, applying .format(**fmt) if kwargs given."""
    s = strings[key]
    return s.format(**fmt) if fmt else s


def load_csv(scale):
    path = os.path.join(RESULTS_DIR, f'{scale}.csv')
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def save_fig(fig, output_dir, name, strings):
    path = os.path.join(output_dir, name)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'{t(strings, "saved")}: {path}')


plt.rcParams.update({'font.size': 10, 'figure.dpi': 130})


# ---------------------------------------------------------------------------
# Chart 1 — Grouped bar: Write Throughput (log scale)
# ---------------------------------------------------------------------------
def chart1_write_throughput(df, output_dir, scale, strings):
    write_tests = ['BATCH-SMALL', 'WRITE', 'OUT-OF-ORDER', 'BATCH-LARGE']
    x = np.arange(len(write_tests))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, db in enumerate(DBS):
        vals = [
            df.loc[(df['db'] == db) & (df['test'] == tst), 'throughput_pts_s'].values[0]
            if len(df[(df['db'] == db) & (df['test'] == tst)]) > 0 else 0
            for tst in write_tests
        ]
        bars = ax.bar(x + (i - 1) * width, vals, width, label=DB_LABELS[db],
                      color=DB_COLORS[db], alpha=0.88, edgecolor='white', linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                        f'{val:,.0f}', ha='center', va='bottom', fontsize=7,
                        color=DB_COLORS[db], rotation=45)

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(write_tests, fontsize=11)
    ax.set_xlabel(t(strings, 'c1_xlabel'), fontsize=12)
    ax.set_ylabel(t(strings, 'c1_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c1_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(axis='y', alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '1_write_throughput.png', strings)


# ---------------------------------------------------------------------------
# Chart 2 — Radar: Efficiency Profile
# ---------------------------------------------------------------------------
def chart2_radar(df, output_dir, scale, strings):
    base = df[df['test'] == 'WRITE'].set_index('db')
    keys = ['throughput_pts_s', 'avg_lat_ms', 'p99_lat_ms', 'avg_cpu_pct', 'peak_mem_mb']
    higher_is_better = [True, False, False, False, False]
    N = len(keys)

    available = [db for db in DBS if db in base.index]
    raw = {db: [base.loc[db, k] for k in keys] for db in available}

    def normalize(idx, higher):
        vals = [raw[db][idx] for db in available]
        vmin, vmax = min(vals), max(vals)
        if vmax == vmin:
            return {db: 1.0 for db in available}
        return {
            db: (raw[db][idx] - vmin) / (vmax - vmin) if higher
            else (vmax - raw[db][idx]) / (vmax - vmin)
            for db in available
        }

    norms = [normalize(i, h) for i, h in enumerate(higher_is_better)]
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    for db in available:
        vals = [norms[i][db] for i in range(N)] + [norms[0][db]]
        ax.plot(angles, vals, 'o-', linewidth=2.2, label=DB_LABELS[db], color=DB_COLORS[db])
        ax.fill(angles, vals, alpha=0.15, color=DB_COLORS[db])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(t(strings, 'c2_axes'), fontsize=11)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(['0.25', '0.50', '0.75', '1.00'], fontsize=8, color='gray')
    ax.set_ylim(0, 1)
    ax.set_title(t(strings, 'c2_title', scale=scale), fontsize=12, fontweight='bold', pad=22)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.15), fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_fig(fig, output_dir, '2_radar_efficiency.png', strings)


# ---------------------------------------------------------------------------
# Chart 3 — Scatter: Cost vs. Benefit
# ---------------------------------------------------------------------------
def chart3_scatter(df, output_dir, scale, strings):
    fig, ax = plt.subplots(figsize=(12, 8))

    for db in DBS:
        sub = df[df['db'] == db]
        ax.scatter(sub['peak_mem_mb'], sub['throughput_pts_s'],
                   color=DB_COLORS[db], s=110, alpha=0.85,
                   edgecolors='white', linewidth=0.8, label=DB_LABELS[db], zorder=3)
        for _, row in sub.iterrows():
            ax.annotate(row['test'], (row['peak_mem_mb'], row['throughput_pts_s']),
                        textcoords='offset points', xytext=(6, 4),
                        fontsize=7, color=DB_COLORS[db], alpha=0.9)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel(t(strings, 'c3_xlabel'), fontsize=12)
    ax.set_ylabel(t(strings, 'c3_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c3_title', scale=scale), fontsize=13, fontweight='bold')
    ax.annotate(t(strings, 'c3_heroes'), xy=(0.04, 0.90), xycoords='axes fraction',
                fontsize=11, color='#2a7a2a', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#d4f0d4', alpha=0.7))
    ax.annotate(t(strings, 'c3_villains'), xy=(0.68, 0.04), xycoords='axes fraction',
                fontsize=11, color='#8b0000', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8d0d0', alpha=0.7))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '3_scatter_cost_benefit.png', strings)


# ---------------------------------------------------------------------------
# Chart 4 — Heatmap: Latency Degradation (scale_a → scale_b)
# ---------------------------------------------------------------------------
def chart4_heatmap(df_a, df_b, scale_a, scale_b, output_dir, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER', 'READ']
    matrix = np.zeros((len(DBS), len(tests)))

    for i, db in enumerate(DBS):
        for j, test in enumerate(tests):
            s = df_a.loc[(df_a['db'] == db) & (df_a['test'] == test), 'avg_lat_ms']
            m = df_b.loc[(df_b['db'] == db) & (df_b['test'] == test), 'avg_lat_ms']
            if len(s) > 0 and len(m) > 0 and s.values[0] > 0:
                matrix[i, j] = ((m.values[0] - s.values[0]) / s.values[0]) * 100

    fig, ax = plt.subplots(figsize=(12, 4))
    vmax = matrix.max() or 1
    im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=vmax)

    ax.set_xticks(range(len(tests)))
    ax.set_xticklabels(tests, fontsize=11)
    ax.set_yticks(range(len(DBS)))
    ax.set_yticklabels([DB_LABELS[db] for db in DBS], fontsize=11)

    for i in range(len(DBS)):
        for j in range(len(tests)):
            val = matrix[i, j]
            text_color = 'white' if val > vmax * 0.6 else 'black'
            ax.text(j, i, f'+{val:.0f}%', ha='center', va='center',
                    fontsize=12, fontweight='bold', color=text_color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label(t(strings, 'c4_cbar'), fontsize=10)
    ax.set_title(t(strings, 'c4_title', scale_a=scale_a.capitalize(),
                   scale_b=scale_b.capitalize()), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '4_heatmap_latency_degradation.png', strings)


# ---------------------------------------------------------------------------
# Chart 5 — Line: Scalability (scale_a → scale_b)
# ---------------------------------------------------------------------------
def chart5_scalability(df_a, df_b, scale_a, scale_b, output_dir, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER']
    label_a = t(strings, f'{scale_a}_label')
    label_b = t(strings, f'{scale_b}_label')

    fig, axes = plt.subplots(1, len(tests), figsize=(16, 5))

    for j, test in enumerate(tests):
        ax = axes[j]
        for db in DBS:
            a = df_a.loc[(df_a['db'] == db) & (df_a['test'] == test), 'avg_lat_ms']
            b = df_b.loc[(df_b['db'] == db) & (df_b['test'] == test), 'avg_lat_ms']
            if len(a) > 0 and len(b) > 0:
                ax.plot([label_a, label_b], [a.values[0], b.values[0]],
                        'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                        linewidth=2.5, markersize=9)
        ax.set_title(test, fontsize=11, fontweight='bold')
        ax.set_ylabel(t(strings, 'avg_lat_label') if j == 0 else '')
        ax.grid(axis='y', alpha=0.3)
        if j == 0:
            ax.legend(fontsize=9)

    fig.suptitle(t(strings, 'c5_title',
                   scale_a=scale_a.capitalize(), scale_b=scale_b.capitalize()),
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '5_line_scalability.png', strings)


# ---------------------------------------------------------------------------
# Chart 6 — Stacked bar: P99 Consistency
# ---------------------------------------------------------------------------
def chart6_p99_consistency(df, output_dir, scale, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER']
    fig, axes = plt.subplots(1, len(tests), figsize=(16, 6))

    for j, test in enumerate(tests):
        ax = axes[j]
        sub = df[df['test'] == test]
        db_labels, avgs, extras, colors = [], [], [], []

        for db in DBS:
            row = sub[sub['db'] == db]
            if len(row) > 0:
                avg = row['avg_lat_ms'].values[0]
                p99 = row['p99_lat_ms'].values[0]
                db_labels.append(DB_LABELS[db])
                avgs.append(avg)
                extras.append(max(p99 - avg, 0))
                colors.append(DB_COLORS[db])

        x = np.arange(len(db_labels))
        ax.bar(x, avgs, color=colors, alpha=0.9, edgecolor='white')
        ax.bar(x, extras, bottom=avgs, color=colors, alpha=0.35,
               edgecolor='white', hatch='//')
        ax.set_xticks(x)
        ax.set_xticklabels(db_labels, rotation=20, ha='right', fontsize=9)
        ax.set_title(test, fontsize=11, fontweight='bold')
        ax.set_ylabel(t(strings, 'c6_ylabel') if j == 0 else '')
        ax.grid(axis='y', alpha=0.3)

    legend_elements = [
        Patch(facecolor='gray', alpha=0.9, label=t(strings, 'avg_lat_legend')),
        Patch(facecolor='gray', alpha=0.35, hatch='//', label=t(strings, 'p99_gap_legend')),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
               bbox_to_anchor=(1.0, 1.0), fontsize=10)
    fig.suptitle(t(strings, 'c6_title', scale=scale), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '6_bar_p99_consistency.png', strings)


# ---------------------------------------------------------------------------
# Chart 7 — Area: Memory Footprint (Avg vs Peak)
# ---------------------------------------------------------------------------
def chart7_memory_area(df, output_dir, scale, strings):
    test_order = ['BATCH-SMALL', 'WRITE', 'OUT-OF-ORDER', 'BATCH-LARGE',
                  'READ', 'LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER']
    order_map = {tst: i for i, tst in enumerate(test_order)}

    fig, axes = plt.subplots(1, len(DBS), figsize=(16, 5), sharey=False)

    for i, db in enumerate(DBS):
        ax = axes[i]
        sub = df[df['db'] == db].copy()
        sub['_order'] = sub['test'].map(order_map)
        sub = sub.sort_values('_order')

        x = np.arange(len(sub))
        avg = sub['avg_mem_mb'].values
        peak = sub['peak_mem_mb'].values

        ax.fill_between(x, avg, peak, alpha=0.28, color=DB_COLORS[db])
        ax.fill_between(x, 0, avg, alpha=0.60, color=DB_COLORS[db])
        ax.plot(x, peak, 'o--', color=DB_COLORS[db], linewidth=1.5, markersize=5, alpha=0.8)
        ax.plot(x, avg, 'o-', color=DB_COLORS[db], linewidth=2.2, markersize=6)

        ax.set_xticks(x)
        ax.set_xticklabels(sub['test'].values, rotation=45, ha='right', fontsize=8)
        ax.set_title(DB_LABELS[db], fontsize=12, fontweight='bold', color=DB_COLORS[db])
        ax.set_ylabel(t(strings, 'mem_label') if i == 0 else '')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
        ax.grid(axis='y', alpha=0.3)

    legend_elements = [
        Patch(facecolor='gray', alpha=0.6, label=t(strings, 'avg_mem_legend')),
        Patch(facecolor='gray', alpha=0.28, label=t(strings, 'peak_gap_legend')),
    ]
    fig.legend(handles=legend_elements, loc='upper right', fontsize=10)
    fig.suptitle(t(strings, 'c7_title', scale=scale), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '7_area_memory.png', strings)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate benchmark charts for IoT time-series DB comparison.'
    )
    parser.add_argument(
        '--source', choices=['all', 'small', 'medium', 'large'], default='all',
        help='Data source scale (default: all). Reads from results/{source}.csv.',
    )
    parser.add_argument(
        '--language', choices=['en-us', 'pt-br'], default='en-us',
        help='Chart label language (default: en-us).',
    )
    return parser.parse_args()


def _run_scale(scale, lang_folder, strings):
    df = load_csv(scale)
    if df is None:
        print(f'Skipping {scale}: results/{scale}.csv not found.')
        return

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts', scale, lang_folder)
    os.makedirs(output_dir, exist_ok=True)

    print(t(strings, 'generating').strip() + f' [{scale}]\n')

    chart1_write_throughput(df, output_dir, scale, strings)
    chart2_radar(df, output_dir, scale, strings)
    chart3_scatter(df, output_dir, scale, strings)

    scale_a, scale_b = SCALE_PAIRS[scale]
    df_a = load_csv(scale_a)
    df_b = load_csv(scale_b)
    if df_a is not None and df_b is not None:
        chart4_heatmap(df_a, df_b, scale_a, scale_b, output_dir, strings)
        chart5_scalability(df_a, df_b, scale_a, scale_b, output_dir, strings)
    else:
        missing = scale_b if df_b is None else scale_a
        print(t(strings, 'skipping').format(f'results/{missing}.csv'))

    chart6_p99_consistency(df, output_dir, scale, strings)
    chart7_memory_area(df, output_dir, scale, strings)

    print(f'\n{t(strings, "done")}: {os.path.abspath(output_dir)}/\n')


def main():
    args = parse_args()
    strings = STRINGS[args.language]
    lang_folder = args.language.replace('-', '_')

    scales = ['small', 'medium', 'large'] if args.source == 'all' else [args.source]
    for scale in scales:
        _run_scale(scale, lang_folder, strings)


if __name__ == '__main__':
    main()
