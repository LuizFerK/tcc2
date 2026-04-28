#!/usr/bin/env python3
"""
Benchmark visualization for IoT time-series DB comparison (InfluxDB, TimescaleDB, IoTDB).

Usage:
  python3 charts.py [--source small|medium|large|mixed|all] [--language en-us|pt-br]

Dependencies: matplotlib numpy pandas
On NixOS/nix develop: matplotlib, numpy, pandas are included in the dev shell.
"""

import argparse
import os
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
        'avg_mem_legend':   'Average Memory',
        'peak_gap_legend':  'Peak − Average',
        'avg_lat_legend':   'Average Latency',
        'p99_gap_legend':   'Gap to P99',
        # test name labels (identity for en-us)
        'test_labels': {
            'BATCH-SMALL':  'BATCH-SMALL',
            'WRITE':        'WRITE',
            'OUT-OF-ORDER': 'OUT-OF-ORDER',
            'BATCH-LARGE':  'BATCH-LARGE',
            'READ':         'READ',
            'LATEST-POINT': 'LATEST-POINT',
            'DOWNSAMPLE':   'DOWNSAMPLE',
            'RANGE-QUERY':  'RANGE-QUERY',
            'VALUE-FILTER': 'VALUE-FILTER',
        },
        # chart 1 — per-scale
        'c1_title':   'Chart 1 — Write Throughput by Database',
        'c1_xlabel':  'Write Test Type',
        'c1_ylabel':  'Throughput (pts/s) — log scale',
        # chart 2 — per-scale
        'c2_title':   'Chart 2 — Efficiency Profile (WRITE test, {scale} scale)\n1 = best performance',
        'c2_axes':    ['Throughput', 'Avg Latency\n(↑=better)', 'P99 Latency\n(↑=better)',
                       'Avg CPU\n(↑=better)', 'Peak Mem\n(↑=better)'],
        # chart 3 — per-scale
        'c3_title':   'Chart 3 — Cost × Benefit: Memory vs Throughput ({scale} scale)',
        'c3_xlabel':  'Peak Memory (MB) — log scale',
        'c3_ylabel':  'Throughput (pts/s) — log scale',
        'c3_favorable':   '← Favorable\n(high perf., low resource)',
        'c3_unfavorable': 'Unfavorable →\n(low perf., high resource)',
        # chart 4 — per-scale
        'c4_title':   'Chart 4 — P99 Consistency: Average + Gap to P99 ({scale} scale)',
        'c4_ylabel':  'Latency (ms)',
        # chart 5 — per-scale
        'c5_title':   'Chart 5 — Memory Footprint by Test ({scale} scale)\nSolid = average  |  Dashed = peak',
        # chart 6 — mixed
        'c6_title':       'Chart 6 — Latency Degradation Heatmap: Small→Medium  |  Medium→Large\nGreen = stable  |  Red = high degradation',
        'c6_subtitle_sm': 'Small → Medium',
        'c6_subtitle_ml': 'Medium → Large',
        'c6_cbar':        'Avg latency increase (%)',
        # chart 7 — mixed
        'c7_title':   'Chart 7 — Scalability: Avg Latency Small → Medium → Large',
        # chart 8 — mixed
        'c8_title':   'Chart 8 — Write Throughput Scaling: Small → Medium → Large',
        'c8_ylabel':  'WRITE Throughput (pts/s) — log scale',
        # chart 9 — mixed
        'c9_title':   'Chart 9 — Latest-Point Latency: O(1) vs Linear Scaling',
        'c9_ylabel':  'Avg Latency (ms)',
        'c9_note':    'InfluxDB grows linearly\n(TSM tail-seek cost)\n\nTimescaleDB & IoTDB stay flat\n(index / last-value cache)',
        # chart 10 — mixed
        'c10_title':  'Chart 10 — Value-Filter Latency Scaling (100× data growth)',
        'c10_ylabel': 'Avg Latency (ms) — log scale',
        'c10_ratio':  '{ratio}× (S→L)',
        # chart 11 — mixed
        'c11_title':    'Chart 11 — CPU Usage: READ Workload Across Scales',
        'c11_ylabel':   'CPU Usage (%)',
        'c11_avg_leg':  'Avg CPU',
        'c11_peak_leg': 'Peak − Avg gap',
        # chart 12 — mixed
        'c12_title':    'Chart 12 — Batch-Small JIT Warmup: All Databases',
        'c12_sub_thr':  'Throughput (pts/s)',
        'c12_sub_lat':  'Avg Latency (ms)',
        # chart 13 — mixed
        'c13_title':  'Chart 13 — Memory Footprint Scaling: Small → Medium → Large',
        'c13_ylabel': 'Peak Memory (MB)',
        # chart 14 — mixed
        'c14_title':  'Chart 14 — READ Workload: Avg & P99 Latency Across Scales',
        'c14_ylabel': 'Latency (ms) — log scale',
        # chart 15 — mixed
        'c15_title':  'Chart 15 — Out-of-Order Write Degradation vs Sequential',
        'c15_ylabel': 'Throughput Degradation (%)\n(OOO vs sequential WRITE)',
    },
    'pt-br': {
        # shared
        'log_scale':        '— escala logarítmica',
        'throughput_label': 'Taxa de Transferência (pts/s)',
        'avg_lat_label':    'Latência Média (ms)',
        'mem_label':        'Memória (MB)',
        'small_label':      'Pequena',
        'medium_label':     'Média',
        'large_label':      'Grande',
        'saved':            'Salvo',
        'done':             'Pronto! Todos os gráficos salvos em',
        'generating':       'Gerando gráficos...\n',
        'avg_mem_legend':   'Memória Média',
        'peak_gap_legend':  'Pico − Média',
        'avg_lat_legend':   'Latência Média',
        'p99_gap_legend':   'Folga até P99',
        # test name labels (Portuguese translation + original in parentheses)
        'test_labels': {
            'BATCH-SMALL':  'LOTE-PEQUENO (BATCH-SMALL)',
            'WRITE':        'ESCRITA (WRITE)',
            'OUT-OF-ORDER': 'FORA DE ORDEM (OUT-OF-ORDER)',
            'BATCH-LARGE':  'LOTE-GRANDE (BATCH-LARGE)',
            'READ':         'LEITURA (READ)',
            'LATEST-POINT': 'ÚLTIMO PONTO (LATEST-POINT)',
            'DOWNSAMPLE':   'SUBAMOSTRAGEM (DOWNSAMPLE)',
            'RANGE-QUERY':  'CONSUL. INTERVALO (RANGE-QUERY)',
            'VALUE-FILTER': 'FILTRO DE VALOR (VALUE-FILTER)',
        },
        # chart 1 — per-scale
        'c1_title':   'Gráfico 1 — Taxa de Transferência de Escrita por Banco de Dados',
        'c1_xlabel':  'Tipo de Teste de Escrita',
        'c1_ylabel':  'Taxa de Transferência (pts/s) — escala logarítmica',
        # chart 2 — per-scale
        'c2_title':   'Gráfico 2 — Perfil de Eficiência (teste WRITE, escala {scale})\n1 = melhor desempenho',
        'c2_axes':    ['Taxa de Transf.', 'Lat. Média\n(↑=melhor)', 'Lat. P99\n(↑=melhor)',
                       'CPU Média\n(↑=melhor)', 'Mem. Pico\n(↑=melhor)'],
        # chart 3 — per-scale
        'c3_title':   'Gráfico 3 — Custo × Benefício: Memória vs Taxa de Transferência (escala {scale})',
        'c3_xlabel':  'Memória Pico (MB) — escala logarítmica',
        'c3_ylabel':  'Taxa de Transferência (pts/s) — escala logarítmica',
        'c3_favorable':   '← Favorável\n(alta perf., baixo recurso)',
        'c3_unfavorable': 'Desfavorável →\n(baixa perf., alto recurso)',
        # chart 4 — per-scale
        'c4_title':   'Gráfico 4 — Consistência P99: Média + Folga até P99 (escala {scale})',
        'c4_ylabel':  'Latência (ms)',
        # chart 5 — per-scale
        'c5_title':   'Gráfico 5 — Footprint de Memória por Teste (escala {scale})\nLinha sólida = média  |  Linha tracejada = pico',
        # chart 6 — mixed
        'c6_title':       'Gráfico 6 — Heatmap de Degradação: Pequena→Média  |  Média→Grande\nVerde = estável  |  Vermelho = alta degradação',
        'c6_subtitle_sm': 'Pequena → Média',
        'c6_subtitle_ml': 'Média → Grande',
        'c6_cbar':        'Aumento de latência média (%)',
        # chart 7 — mixed
        'c7_title':   'Gráfico 7 — Escalabilidade: Latência Média Pequena → Média → Grande',
        # chart 8 — mixed
        'c8_title':   'Gráfico 8 — Escalonamento da Taxa de Transferência de Escrita: Pequena → Média → Grande',
        'c8_ylabel':  'Taxa de Transf. WRITE (pts/s) — escala logarítmica',
        # chart 9 — mixed
        'c9_title':   'Gráfico 9 — Latência Latest-Point: O(1) vs Escalonamento Linear',
        'c9_ylabel':  'Latência Média (ms)',
        'c9_note':    'InfluxDB cresce linearmente\n(busca no final do TSM)\n\nTimescaleDB & IoTDB ficam constantes\n(índice / cache de último valor)',
        # chart 10 — mixed
        'c10_title':  'Gráfico 10 — Escalonamento de Latência Value-Filter (crescimento 100× nos dados)',
        'c10_ylabel': 'Latência Média (ms) — escala logarítmica',
        'c10_ratio':  '{ratio}× (P→G)',
        # chart 11 — mixed
        'c11_title':    'Gráfico 11 — Uso de CPU: Carga de Leitura por Escala',
        'c11_ylabel':   'Uso de CPU (%)',
        'c11_avg_leg':  'CPU Média',
        'c11_peak_leg': 'Folga Pico − Média',
        # chart 12 — mixed
        'c12_title':    'Gráfico 12 — Aquecimento JIT (Batch-Small): Todos os Bancos',
        'c12_sub_thr':  'Taxa de Transferência (pts/s)',
        'c12_sub_lat':  'Latência Média (ms)',
        # chart 13 — mixed
        'c13_title':  'Gráfico 13 — Escalonamento do Footprint de Memória: Pequena → Média → Grande',
        'c13_ylabel': 'Memória Pico (MB)',
        # chart 14 — mixed
        'c14_title':  'Gráfico 14 — Carga de Leitura: Latência Média e P99 por Escala',
        'c14_ylabel': 'Latência (ms) — escala logarítmica',
        # chart 15 — mixed
        'c15_title':  'Gráfico 15 — Degradação de Escrita Fora de Ordem vs Sequencial',
        'c15_ylabel': 'Degradação da Taxa de Transferência (%)\n(OOO vs WRITE sequencial)',
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def t(strings, key, **fmt):
    """Return localised string, applying .format(**fmt) if kwargs given."""
    s = strings[key]
    return s.format(**fmt) if fmt else s


def test_label(strings, test):
    """Return localised display name for a test identifier."""
    return strings['test_labels'].get(test, test)


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


def get_val(df, db, test, col, default=0):
    row = df[(df['db'] == db) & (df['test'] == test)]
    return row[col].values[0] if len(row) > 0 else default


plt.rcParams.update({'font.size': 10, 'figure.dpi': 130})


# ===========================================================================
# Per-scale charts (1–5)
# ===========================================================================

# ---------------------------------------------------------------------------
# Chart 1 — Grouped bar: Write Throughput (log scale)
# ---------------------------------------------------------------------------
def chart1_write_throughput(df, output_dir, scale, strings):
    write_tests = ['BATCH-SMALL', 'WRITE', 'OUT-OF-ORDER', 'BATCH-LARGE']
    x = np.arange(len(write_tests))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, db in enumerate(DBS):
        vals = [get_val(df, db, tst, 'throughput_pts_s') for tst in write_tests]
        bars = ax.bar(x + (i - 1) * width, vals, width, label=DB_LABELS[db],
                      color=DB_COLORS[db], alpha=0.88, edgecolor='white', linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.15,
                        f'{val:,.0f}', ha='center', va='bottom', fontsize=7,
                        color=DB_COLORS[db], rotation=45)

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels([test_label(strings, tst) for tst in write_tests], fontsize=10)
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
            ax.annotate(test_label(strings, row['test']),
                        (row['peak_mem_mb'], row['throughput_pts_s']),
                        textcoords='offset points', xytext=(6, 4),
                        fontsize=7, color=DB_COLORS[db], alpha=0.9)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel(t(strings, 'c3_xlabel'), fontsize=12)
    ax.set_ylabel(t(strings, 'c3_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c3_title', scale=scale), fontsize=13, fontweight='bold')
    ax.annotate(t(strings, 'c3_favorable'), xy=(0.04, 0.90), xycoords='axes fraction',
                fontsize=11, color='#2a7a2a', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#d4f0d4', alpha=0.7))
    ax.annotate(t(strings, 'c3_unfavorable'), xy=(0.68, 0.04), xycoords='axes fraction',
                fontsize=11, color='#8b0000', fontstyle='italic',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8d0d0', alpha=0.7))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '3_scatter_cost_benefit.png', strings)


# ---------------------------------------------------------------------------
# Chart 4 — Stacked bar: P99 Consistency
# ---------------------------------------------------------------------------
def chart4_p99_consistency(df, output_dir, scale, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER']
    fig, axes = plt.subplots(1, len(tests), figsize=(16, 6))

    for j, test in enumerate(tests):
        ax = axes[j]
        db_labels, avgs, extras, colors = [], [], [], []

        for db in DBS:
            avg = get_val(df, db, test, 'avg_lat_ms')
            p99 = get_val(df, db, test, 'p99_lat_ms')
            if avg > 0 or p99 > 0:
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
        ax.set_title(test_label(strings, test), fontsize=10, fontweight='bold')
        ax.set_ylabel(t(strings, 'c4_ylabel') if j == 0 else '')
        ax.grid(axis='y', alpha=0.3)

    legend_elements = [
        Patch(facecolor='gray', alpha=0.9, label=t(strings, 'avg_lat_legend')),
        Patch(facecolor='gray', alpha=0.35, hatch='//', label=t(strings, 'p99_gap_legend')),
    ]
    fig.legend(handles=legend_elements, loc='upper right',
               bbox_to_anchor=(1.0, 1.0), fontsize=10)
    fig.suptitle(t(strings, 'c4_title', scale=scale), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '4_bar_p99_consistency.png', strings)


# ---------------------------------------------------------------------------
# Chart 5 — Area: Memory Footprint (Avg vs Peak)
# ---------------------------------------------------------------------------
def chart5_memory_area(df, output_dir, scale, strings):
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
        ax.set_xticklabels(
            [test_label(strings, tst) for tst in sub['test'].values],
            rotation=45, ha='right', fontsize=7,
        )
        ax.set_title(DB_LABELS[db], fontsize=12, fontweight='bold', color=DB_COLORS[db])
        ax.set_ylabel(t(strings, 'mem_label') if i == 0 else '')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
        ax.grid(axis='y', alpha=0.3)

    legend_elements = [
        Patch(facecolor='gray', alpha=0.6, label=t(strings, 'avg_mem_legend')),
        Patch(facecolor='gray', alpha=0.28, label=t(strings, 'peak_gap_legend')),
    ]
    fig.legend(handles=legend_elements, loc='upper right', fontsize=10)
    fig.suptitle(t(strings, 'c5_title', scale=scale), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '5_area_memory.png', strings)


# ===========================================================================
# Mixed charts (6–15) — all use data from all 3 scales
# ===========================================================================

def _scale_labels(strings):
    return [t(strings, 'small_label'), t(strings, 'medium_label'), t(strings, 'large_label')]


# ---------------------------------------------------------------------------
# Chart 6 — Heatmap: Latency Degradation (combined Small→Medium | Medium→Large)
# ---------------------------------------------------------------------------
def chart6_heatmap(df_s, df_m, df_l, output_dir, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER', 'READ']

    def degradation_matrix(df_a, df_b):
        matrix = np.zeros((len(DBS), len(tests)))
        for i, db in enumerate(DBS):
            for j, test in enumerate(tests):
                a = get_val(df_a, db, test, 'avg_lat_ms')
                b = get_val(df_b, db, test, 'avg_lat_ms')
                if a > 0:
                    matrix[i, j] = ((b - a) / a) * 100
        return matrix

    matrix_sm = degradation_matrix(df_s, df_m)
    matrix_ml = degradation_matrix(df_m, df_l)
    vmax = max(matrix_sm.max(), matrix_ml.max()) or 1

    fig, axes = plt.subplots(1, 2, figsize=(20, 4))

    last_im = None
    for ax, matrix, subtitle_key in zip(
        axes,
        [matrix_sm, matrix_ml],
        ['c6_subtitle_sm', 'c6_subtitle_ml'],
    ):
        last_im = ax.imshow(matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=vmax)
        ax.set_xticks(range(len(tests)))
        ax.set_xticklabels(
            [test_label(strings, tst) for tst in tests],
            fontsize=9, rotation=20, ha='right',
        )
        ax.set_yticks(range(len(DBS)))
        ax.set_yticklabels([DB_LABELS[db] for db in DBS], fontsize=10)
        for i in range(len(DBS)):
            for j in range(len(tests)):
                val = matrix[i, j]
                text_color = 'white' if val > vmax * 0.6 else 'black'
                ax.text(j, i, f'+{val:.0f}%', ha='center', va='center',
                        fontsize=12, fontweight='bold', color=text_color)
        ax.set_title(t(strings, subtitle_key), fontsize=12, fontweight='bold', pad=8)

    cbar = fig.colorbar(last_im, ax=axes.tolist(), fraction=0.012, pad=0.04)
    cbar.set_label(t(strings, 'c6_cbar'), fontsize=10)
    fig.suptitle(t(strings, 'c6_title'), fontsize=13, fontweight='bold', y=1.06)
    fig.subplots_adjust(top=0.82, wspace=0.15)
    save_fig(fig, output_dir, '6_heatmap_latency_degradation.png', strings)


# ---------------------------------------------------------------------------
# Chart 7 — Line: Scalability across Small → Medium → Large
# ---------------------------------------------------------------------------
def chart7_scalability(df_s, df_m, df_l, output_dir, strings):
    tests = ['LATEST-POINT', 'DOWNSAMPLE', 'RANGE-QUERY', 'VALUE-FILTER']
    labels = _scale_labels(strings)
    dfs = [df_s, df_m, df_l]

    fig, axes = plt.subplots(1, len(tests), figsize=(16, 5))

    for j, test in enumerate(tests):
        ax = axes[j]
        for db in DBS:
            vals = [get_val(df, db, test, 'avg_lat_ms') for df in dfs]
            if any(v > 0 for v in vals):
                ax.plot(labels, vals,
                        'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                        linewidth=2.5, markersize=9)
        ax.set_title(test_label(strings, test), fontsize=10, fontweight='bold')
        ax.set_ylabel(t(strings, 'avg_lat_label') if j == 0 else '')
        ax.grid(axis='y', alpha=0.3)
        if j == 0:
            ax.legend(fontsize=9)

    fig.suptitle(t(strings, 'c7_title'), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '7_line_scalability.png', strings)


# ---------------------------------------------------------------------------
# Chart 8 — Line: WRITE Throughput Scaling
# ---------------------------------------------------------------------------
def chart8_write_scaling(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)

    fig, ax = plt.subplots(figsize=(10, 6))

    for db in DBS:
        vals = [get_val(df, db, 'WRITE', 'throughput_pts_s') for df in dfs]
        ax.plot(labels, vals, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                linewidth=2.5, markersize=10)
        for lbl, v in zip(labels, vals):
            ax.annotate(f'{v:,.0f}', (lbl, v), textcoords='offset points',
                        xytext=(0, 10), ha='center', fontsize=8, color=DB_COLORS[db])

    ax.set_yscale('log')
    ax.set_ylabel(t(strings, 'c8_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c8_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(axis='y', alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '8_write_scaling.png', strings)


# ---------------------------------------------------------------------------
# Chart 9 — Line: Latest-Point Latency (O(1) vs linear)
# ---------------------------------------------------------------------------
def chart9_latest_point_scaling(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)

    fig, ax = plt.subplots(figsize=(10, 6))

    for db in DBS:
        vals = [get_val(df, db, 'LATEST-POINT', 'avg_lat_ms') for df in dfs]
        ax.plot(labels, vals, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                linewidth=2.5, markersize=10)
        for lbl, v in zip(labels, vals):
            ax.annotate(f'{v:.2f}ms', (lbl, v), textcoords='offset points',
                        xytext=(0, 10), ha='center', fontsize=9, color=DB_COLORS[db])

    ax.set_ylabel(t(strings, 'c9_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c9_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    ax.annotate(t(strings, 'c9_note'), xy=(0.97, 0.50), xycoords='axes fraction',
                fontsize=9, ha='right', va='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#fff9c4', alpha=0.85))
    fig.tight_layout()
    save_fig(fig, output_dir, '9_latest_point_scaling.png', strings)


# ---------------------------------------------------------------------------
# Chart 10 — Line: Value-Filter Latency Scaling
# ---------------------------------------------------------------------------
def chart10_value_filter_scaling(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)

    fig, ax = plt.subplots(figsize=(10, 6))

    for db in DBS:
        vals = [get_val(df, db, 'VALUE-FILTER', 'avg_lat_ms') for df in dfs]
        ax.plot(labels, vals, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                linewidth=2.5, markersize=10)
        s, l_ = vals[0], vals[2]
        if s > 0 and l_ > 0:
            ratio = l_ / s
            ax.annotate(t(strings, 'c10_ratio', ratio=f'{ratio:.1f}'),
                        xy=(labels[2], l_), textcoords='offset points',
                        xytext=(8, 0), ha='left', fontsize=9,
                        color=DB_COLORS[db], fontweight='bold')

    ax.set_yscale('log')
    ax.set_ylabel(t(strings, 'c10_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c10_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.1f}'))
    ax.grid(axis='y', alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '10_value_filter_scaling.png', strings)


# ---------------------------------------------------------------------------
# Chart 11 — Grouped bar: CPU Usage for READ across scales
# ---------------------------------------------------------------------------
def chart11_cpu_saturation(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)
    x = np.arange(len(dfs))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, db in enumerate(DBS):
        avgs = [get_val(df, db, 'READ', 'avg_cpu_pct') for df in dfs]
        peaks = [get_val(df, db, 'READ', 'peak_cpu_pct') for df in dfs]
        gaps = [max(p - a, 0) for p, a in zip(peaks, avgs)]
        offset = (i - 1) * width
        ax.bar(x + offset, avgs, width, color=DB_COLORS[db], alpha=0.85,
               edgecolor='white', label=DB_LABELS[db])
        ax.bar(x + offset, gaps, width, bottom=avgs, color=DB_COLORS[db],
               alpha=0.30, edgecolor='white', hatch='//')
        for j, (a, p) in enumerate(zip(avgs, peaks)):
            ax.text(x[j] + offset, p + 1, f'{p:.0f}%', ha='center', va='bottom',
                    fontsize=7, color=DB_COLORS[db])

    ax.axhline(100, color='red', linestyle='--', linewidth=1.2, alpha=0.6, label='100%')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel(t(strings, 'c11_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c11_title'), fontsize=13, fontweight='bold')
    ax.set_ylim(0, 120)
    legend_elements = [
        *[Patch(facecolor=DB_COLORS[db], alpha=0.85, label=DB_LABELS[db]) for db in DBS],
        Patch(facecolor='gray', alpha=0.85, label=t(strings, 'c11_avg_leg')),
        Patch(facecolor='gray', alpha=0.30, hatch='//', label=t(strings, 'c11_peak_leg')),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save_fig(fig, output_dir, '11_cpu_saturation.png', strings)


# ---------------------------------------------------------------------------
# Chart 12 — Batch-Small: Throughput & Latency (JIT warmup)
# ---------------------------------------------------------------------------
def chart12_batch_small_jit(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for db in DBS:
        thrpts = [get_val(df, db, 'BATCH-SMALL', 'throughput_pts_s') for df in dfs]
        lats = [get_val(df, db, 'BATCH-SMALL', 'avg_lat_ms') for df in dfs]

        ax1.plot(labels, thrpts, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                 linewidth=2.5, markersize=9)
        for lbl, v in zip(labels, thrpts):
            ax1.annotate(f'{v:,.0f}', (lbl, v), textcoords='offset points',
                         xytext=(0, 9), ha='center', fontsize=7, color=DB_COLORS[db])

        ax2.plot(labels, lats, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                 linewidth=2.5, markersize=9)
        for lbl, v in zip(labels, lats):
            ax2.annotate(f'{v:.2f}ms', (lbl, v), textcoords='offset points',
                         xytext=(0, 9), ha='center', fontsize=7, color=DB_COLORS[db])

    ax1.set_yscale('log')
    ax1.set_ylabel(t(strings, 'c12_sub_thr'), fontsize=11)
    ax1.set_title(t(strings, 'c12_sub_thr'), fontsize=11, fontweight='bold')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax1.legend(fontsize=9)
    ax1.grid(axis='y', alpha=0.3, which='both')

    ax2.set_ylabel(t(strings, 'c12_sub_lat'), fontsize=11)
    ax2.set_title(t(strings, 'c12_sub_lat'), fontsize=11, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    fig.suptitle(t(strings, 'c12_title'), fontsize=13, fontweight='bold')
    fig.tight_layout()
    save_fig(fig, output_dir, '12_batch_small_jit.png', strings)


# ---------------------------------------------------------------------------
# Chart 13 — Line: Memory Footprint Scaling
# ---------------------------------------------------------------------------
def chart13_memory_scaling(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)

    fig, ax = plt.subplots(figsize=(10, 6))

    for db in DBS:
        peaks = [df[df['db'] == db]['peak_mem_mb'].max() for df in dfs]
        ax.plot(labels, peaks, 'o-', color=DB_COLORS[db], label=DB_LABELS[db],
                linewidth=2.5, markersize=10)
        for lbl, v in zip(labels, peaks):
            ax.annotate(f'{v:,.0f}MB', (lbl, v), textcoords='offset points',
                        xytext=(0, 10), ha='center', fontsize=9, color=DB_COLORS[db])

    ax.set_ylabel(t(strings, 'c13_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c13_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save_fig(fig, output_dir, '13_memory_scaling.png', strings)


# ---------------------------------------------------------------------------
# Chart 14 — Grouped bar: READ Avg & P99 Latency Across Scales
# ---------------------------------------------------------------------------
def chart14_p99_tail(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)
    x = np.arange(len(dfs))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, db in enumerate(DBS):
        avgs = [get_val(df, db, 'READ', 'avg_lat_ms') for df in dfs]
        p99s = [get_val(df, db, 'READ', 'p99_lat_ms') for df in dfs]
        gaps = [max(p - a, 0) for p, a in zip(p99s, avgs)]
        offset = (i - 1) * width
        ax.bar(x + offset, avgs, width, color=DB_COLORS[db], alpha=0.85,
               edgecolor='white', label=DB_LABELS[db])
        ax.bar(x + offset, gaps, width, bottom=avgs, color=DB_COLORS[db],
               alpha=0.30, edgecolor='white', hatch='//')

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel(t(strings, 'c14_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c14_title'), fontsize=13, fontweight='bold')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}'))
    legend_elements = [
        *[Patch(facecolor=DB_COLORS[db], alpha=0.85, label=DB_LABELS[db]) for db in DBS],
        Patch(facecolor='gray', alpha=0.85, label=t(strings, 'avg_lat_legend')),
        Patch(facecolor='gray', alpha=0.30, hatch='//', label=t(strings, 'p99_gap_legend')),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3, which='both')
    fig.tight_layout()
    save_fig(fig, output_dir, '14_p99_tail.png', strings)


# ---------------------------------------------------------------------------
# Chart 15 — Grouped bar: Out-of-Order Degradation vs Sequential
# ---------------------------------------------------------------------------
def chart15_ooo_degradation(df_s, df_m, df_l, output_dir, strings):
    dfs = [df_s, df_m, df_l]
    labels = _scale_labels(strings)
    x = np.arange(len(dfs))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, db in enumerate(DBS):
        writes = [get_val(df, db, 'WRITE', 'throughput_pts_s') for df in dfs]
        ooos = [get_val(df, db, 'OUT-OF-ORDER', 'throughput_pts_s') for df in dfs]
        degradation = [
            max((w - o) / w * 100, 0) if w > 0 else 0
            for w, o in zip(writes, ooos)
        ]
        offset = (i - 1) * width
        bars = ax.bar(x + offset, degradation, width, color=DB_COLORS[db], alpha=0.85,
                      edgecolor='white', label=DB_LABELS[db])
        for bar, d in zip(bars, degradation):
            if d >= 0.5:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f'{d:.1f}%', ha='center', va='bottom', fontsize=8,
                        color=DB_COLORS[db], fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel(t(strings, 'c15_ylabel'), fontsize=12)
    ax.set_title(t(strings, 'c15_title'), fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save_fig(fig, output_dir, '15_ooo_degradation.png', strings)


# ===========================================================================
# Runners
# ===========================================================================

def _run_scale(scale, lang_folder, strings):
    df = load_csv(scale)
    if df is None:
        print(f'Skipping {scale}: results/{scale}.csv not found.')
        return

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts', scale, lang_folder)
    os.makedirs(output_dir, exist_ok=True)

    print(t(strings, 'generating').strip() + f' [{scale}]\n')

    loc_scale = t(strings, f'{scale}_label')
    chart1_write_throughput(df, output_dir, loc_scale, strings)
    chart2_radar(df, output_dir, loc_scale, strings)
    chart3_scatter(df, output_dir, loc_scale, strings)
    chart4_p99_consistency(df, output_dir, loc_scale, strings)
    chart5_memory_area(df, output_dir, loc_scale, strings)

    print(f'\n{t(strings, "done")}: {os.path.abspath(output_dir)}/\n')


def _run_mixed(lang_folder, strings):
    df_s = load_csv('small')
    df_m = load_csv('medium')
    df_l = load_csv('large')

    missing = [s for s, d in [('small', df_s), ('medium', df_m), ('large', df_l)] if d is None]
    if missing:
        print(f'Skipping mixed charts: results/{missing[0]}.csv not found.')
        return

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts', 'mixed', lang_folder)
    os.makedirs(output_dir, exist_ok=True)

    print(t(strings, 'generating').strip() + ' [mixed]\n')

    chart6_heatmap(df_s, df_m, df_l, output_dir, strings)
    chart7_scalability(df_s, df_m, df_l, output_dir, strings)
    chart8_write_scaling(df_s, df_m, df_l, output_dir, strings)
    chart9_latest_point_scaling(df_s, df_m, df_l, output_dir, strings)
    chart10_value_filter_scaling(df_s, df_m, df_l, output_dir, strings)
    chart11_cpu_saturation(df_s, df_m, df_l, output_dir, strings)
    chart12_batch_small_jit(df_s, df_m, df_l, output_dir, strings)
    chart13_memory_scaling(df_s, df_m, df_l, output_dir, strings)
    chart14_p99_tail(df_s, df_m, df_l, output_dir, strings)
    chart15_ooo_degradation(df_s, df_m, df_l, output_dir, strings)

    print(f'\n{t(strings, "done")}: {os.path.abspath(output_dir)}/\n')


# ===========================================================================
# Entry point
# ===========================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate benchmark charts for IoT time-series DB comparison.'
    )
    parser.add_argument(
        '--source', choices=['all', 'small', 'medium', 'large', 'mixed'], default='all',
        help='Data source scale (default: all). Reads from results/{source}.csv.',
    )
    parser.add_argument(
        '--language', choices=['en-us', 'pt-br'], default='en-us',
        help='Chart label language (default: en-us).',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    strings = STRINGS[args.language]
    lang_folder = args.language.replace('-', '_')

    if args.source == 'all':
        for scale in ['small', 'medium', 'large']:
            _run_scale(scale, lang_folder, strings)
        _run_mixed(lang_folder, strings)
    elif args.source == 'mixed':
        _run_mixed(lang_folder, strings)
    else:
        _run_scale(args.source, lang_folder, strings)


if __name__ == '__main__':
    main()
