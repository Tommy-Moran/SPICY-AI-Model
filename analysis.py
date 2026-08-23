"""SPICY-AI vs Physician vs GPT-4o — analysis script (n=50, 150 plans).

The de-identified score file is not in the public repository. Place
`data/scores_long.csv` (from the corresponding author) in this folder,
then run:

    python3 analysis.py

`--source-xlsx` is for the authors only and is not needed to use SPICY-AI.

Statistical methods
-------------------
For every case (`rin`), all three plans (Physician/SPICY-AI/GPT-4o) are
from the same clinical case and scored together (matched/repeated-measures).

- **Primary analysis**: pairwise Wilcoxon signed-rank, paired by `rin`,
  for four Likert domains (12 tests), Holm-Bonferroni across all 12.
  McNemar exact, paired by `rin`, for error rates.
- **Sensitivity**: Mann-Whitney U and Fisher exact (independent samples).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats as sps
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

# ── Paths (all relative to this script) ──────────────────────────────────────
HERE       = Path(__file__).resolve().parent
DATA_DIR   = HERE / "data"
FIG_DIR    = HERE / "figures"
SCORES_CSV = DATA_DIR / "scores_long.csv"

DATA_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)

GROUPS  = ["Physician", "SPICY-AI", "GPT-4o"]
DOMAINS = [("diag", "Diagnostic accuracy"),
           ("mgmt", "Management appropriateness"),
           ("comp", "Completeness"),
           ("clar", "Clarity")]
COLORS  = {"Physician": "#4C72B0", "SPICY-AI": "#55A868", "GPT-4o": "#C44E52"}
PAIRS   = [("Physician", "SPICY-AI"),
           ("Physician", "GPT-4o"),
           ("SPICY-AI", "GPT-4o")]


# ── Source-xlsx mode (authors only) ──────────────────────────────────────────
def load_scored_wb(path: Path, alloc_sheet_name: str) -> list[dict]:
    """Unblind a scoring workbook via its allocation key sheet."""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    ws, ak = wb["Scoring"], wb[alloc_sheet_name]

    alloc: dict[int, dict[str, str]] = {}
    for row in ak.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        try:
            alloc[int(row[0])] = {"A": row[1], "B": row[2], "C": row[3]}
        except (TypeError, ValueError):
            continue

    records, current_rin = [], None
    for row in ws.iter_rows(min_row=2, values_only=True):
        val = row[0]
        if val is None:
            continue
        if isinstance(val, (int, float)) or (isinstance(val, str) and str(val).strip().isdigit()):
            current_rin = int(float(val))
            continue
        if str(val).strip() in ("A", "B", "C") and current_rin in alloc:
            plan = str(val).strip()
            diag, mgmt, comp, clar, minor, major = row[2:8]
            if any(not isinstance(s, (int, float)) for s in (diag, mgmt, comp, clar, minor, major)):
                continue
            records.append(dict(
                rin=current_rin, label=plan, group=alloc[current_rin][plan],
                diag=int(diag), mgmt=int(mgmt), comp=int(comp), clar=int(clar),
                minor=int(minor), major=int(major),
            ))
    return records


def rebuild_from_xlsx(xlsx_dir: Path) -> pd.DataFrame:
    wb1 = xlsx_dir / "CSANZ_Cases_Scored_1-10.xlsx"
    wb2 = xlsx_dir / "CSANZ_Cases_Scored_11-50.xlsx"
    if not wb1.exists() or not wb2.exists():
        sys.exit(f"--source-xlsx mode: workbooks not found in {xlsx_dir}\n"
                 f"  expected: {wb1.name} and {wb2.name}")
    recs = (load_scored_wb(wb1, "Allocation Key (Cases 1-10)") +
            load_scored_wb(wb2, "Allocation Key (DO NOT OPEN WHILE SCORING)"))
    df = pd.DataFrame(recs)
    df.to_csv(SCORES_CSV, index=False)
    print(f"Rebuilt {SCORES_CSV} from raw xlsx ({len(df)} rows)")
    return df


# ── Holm-Bonferroni helper ──────────────────────────────────────────────────
def holm_bonferroni(pvals: list[float]) -> list[float]:
    """Step-down Holm adjustment. Returns adjusted p-values in input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, pvals[idx] * (m - rank))
        adj[idx] = min(running, 1.0)
    return adj


def mcnemar_exact(n10: int, n01: int) -> float:
    """Exact McNemar test p-value via the binomial distribution on the
    discordant pairs (equivalent to statsmodels' exact McNemar test,
    implemented directly with scipy to avoid an extra dependency)."""
    n = n10 + n01
    if n == 0:
        return 1.0
    return sps.binomtest(min(n10, n01), n, 0.5, alternative="two-sided").pvalue


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source-xlsx", action="store_true",
                    help="Rebuild scores_long.csv from raw scoring workbooks "
                         "(authors only; requires the two .xlsx files).")
    ap.add_argument("--xlsx-dir", type=Path,
                    default=Path(os.environ.get("SPICY_XLSX_DIR", HERE.parent)),
                    help="Directory containing CSANZ_Cases_Scored_*.xlsx "
                         "(default: parent of this script, or $SPICY_XLSX_DIR).")
    args = ap.parse_args()

    if args.source_xlsx:
        df = rebuild_from_xlsx(args.xlsx_dir)
    else:
        if not SCORES_CSV.exists():
            sys.exit(f"Missing {SCORES_CSV}. The public repository does not "
                     f"include the score file. Request it from the corresponding "
                     f"author (TommyMoran@gmail.com), place it at that path, "
                     f"and re-run.")
        df = pd.read_csv(SCORES_CSV)

    # ── Validation ──────────────────────────────────────────────────────────
    n_plans = len(df)
    group_counts = df.groupby("group").size().to_dict()
    print(f"Loaded {n_plans} plan rows; group counts: {group_counts}")
    assert n_plans == 150, f"Expected 150 rows, got {n_plans}"
    assert group_counts == {"Physician": 50, "SPICY-AI": 50, "GPT-4o": 50}, \
        f"Unexpected group counts: {group_counts}"

    # ── Summary statistics ──────────────────────────────────────────────────
    summary = []
    for dom, _ in DOMAINS:
        for g in GROUPS:
            v = df.loc[df.group == g, dom]
            summary.append(dict(domain=dom, group=g, n=len(v),
                                mean=v.mean(), sd=v.std(ddof=1),
                                median=v.median(),
                                q1=v.quantile(0.25), q3=v.quantile(0.75)))
    sdf = pd.DataFrame(summary)
    sdf.to_csv(DATA_DIR / "summary.csv", index=False)
    print("\n=== Summary statistics (n=50/group) ===")
    print(sdf.to_string(index=False))

    # ── PRIMARY: Wilcoxon signed-rank (paired by case) with Holm-Bonferroni ──
    # Every `rin` has all three groups scored as a set, so this is a
    # matched/repeated-measures design at the case level.
    wil_rows = []
    for dom, label in DOMAINS:
        piv = df.pivot(index="rin", columns="group", values=dom)
        for a, b in PAIRS:
            x, y = piv[a].values, piv[b].values
            stat, p = sps.wilcoxon(x, y, alternative="two-sided", zero_method="wilcox",
                                    mode="auto")
            wil_rows.append(dict(domain=dom, label=label, groupA=a, groupB=b,
                                 medA=float(np.median(x)), medB=float(np.median(y)),
                                 meanA=float(np.mean(x)), meanB=float(np.mean(y)),
                                 n_pairs=len(x), W=stat, p=p))
    wil = pd.DataFrame(wil_rows)
    wil["p_holm"] = holm_bonferroni(wil["p"].tolist())
    wil.to_csv(DATA_DIR / "wilcoxon_primary.csv", index=False)

    print("\n=== PRIMARY: Wilcoxon signed-rank, paired by case (Holm-Bonferroni across 12 tests) ===")
    print(wil[["domain", "groupA", "groupB", "meanA", "meanB", "W", "p", "p_holm"]].to_string(index=False))

    # ── SENSITIVITY: Mann-Whitney U (independent-samples; retained for ─────
    # comparison to demonstrate the paired-test correction does not change
    # any significance conclusion) ───────────────────────────────────────────
    mw_rows = []
    for dom, label in DOMAINS:
        for a, b in PAIRS:
            x = df.loc[df.group == a, dom].values
            y = df.loc[df.group == b, dom].values
            u, p = sps.mannwhitneyu(x, y, alternative="two-sided")
            mw_rows.append(dict(domain=dom, label=label, groupA=a, groupB=b,
                                medA=float(np.median(x)), medB=float(np.median(y)),
                                meanA=float(np.mean(x)), meanB=float(np.mean(y)),
                                U=u, p=p))
    mw = pd.DataFrame(mw_rows)
    mw["p_holm"] = holm_bonferroni(mw["p"].tolist())
    mw.to_csv(DATA_DIR / "sensitivity_mannwhitney.csv", index=False)

    print("\n=== SENSITIVITY: Mann-Whitney U, independent-samples (Holm-Bonferroni across 12 tests) ===")
    print(mw[["domain", "groupA", "groupB", "meanA", "meanB", "U", "p", "p_holm"]].to_string(index=False))

    agree = ((wil["p_holm"] < 0.05) == (mw["p_holm"] < 0.05)).all()
    print(f"\nPrimary (paired) vs sensitivity (unpaired) significance conclusions "
          f"{'AGREE on all 12 comparisons' if agree else 'DISAGREE on at least one comparison'}.")

    # ── Kruskal-Wallis case-block heterogeneity ────────────────────────────────
    # Divided-cohort design: reviewer_id 1=RINs 1-10, 2=RINs 11-30,
    # 3=RINs 31-40, 4=RINs 41-50. ICC cannot be computed (no shared cases).
    # KW tests whether the 4 analysis blocks produced systematically different
    # composite Likert scores (composite = mean of 4 domain scores per plan).
    kw_rows = []
    dom_cols = [d for d, _ in DOMAINS]
    df["composite"] = df[dom_cols].mean(axis=1)
    for dom in dom_cols + ["composite"]:
        groups_by_rev = [
            df.loc[df["reviewer_id"] == rid, dom].values
            for rid in sorted(df["reviewer_id"].unique())
        ]
        h, p = sps.kruskal(*groups_by_rev)
        kw_rows.append(dict(domain=dom, H=h, p=p,
                            n_reviewers=len(groups_by_rev)))
    kw = pd.DataFrame(kw_rows)
    kw.to_csv(DATA_DIR / "kruskal_wallis_reviewers.csv", index=False)
    print("\n=== Kruskal-Wallis reviewer consistency (4 reviewer subsets) ===")
    print(kw.to_string(index=False))

    # ── PRIMARY: Error rates via McNemar's exact test (paired by case) ──────
    def error_tests_paired(col: str) -> list[dict]:
        piv = df.pivot(index="rin", columns="group", values=col)
        rows = []
        for a, b in PAIRS:
            xa, xb = piv[a].values, piv[b].values
            n10 = int(((xa == 1) & (xb == 0)).sum())
            n01 = int(((xa == 0) & (xb == 1)).sum())
            p = mcnemar_exact(n10, n01)
            rows.append(dict(error=col, groupA=a, rateA=xa.mean(),
                             groupB=b, rateB=xb.mean(),
                             n_discordant=n10 + n01, p_mcnemar=p))
        return rows

    err_paired = pd.DataFrame(error_tests_paired("minor") + error_tests_paired("major"))
    err_paired.to_csv(DATA_DIR / "error_rates_mcnemar_primary.csv", index=False)
    print("\n=== PRIMARY: Error rates, McNemar's exact test (paired by case) ===")
    print(err_paired.to_string(index=False))

    # ── SENSITIVITY: Fisher exact (independent-samples; retained for ───────
    # comparison) ────────────────────────────────────────────────────────────
    def error_tests(col: str, n_per_group: int = 50) -> list[dict]:
        rows = []
        for a, b in PAIRS:
            xa = int(df.loc[df.group == a, col].sum())
            xb = int(df.loc[df.group == b, col].sum())
            _, p = sps.fisher_exact([[xa, n_per_group - xa], [xb, n_per_group - xb]])
            rows.append(dict(error=col, groupA=a, rateA=xa / n_per_group,
                             groupB=b, rateB=xb / n_per_group, p_fisher=p))
        return rows

    err = pd.DataFrame(error_tests("minor") + error_tests("major"))
    err.to_csv(DATA_DIR / "sensitivity_error_rates_fisher.csv", index=False)
    print("\n=== SENSITIVITY: Error rates, Fisher exact (independent-samples) ===")
    print(err.to_string(index=False))

    err_summary = df.groupby("group")[["minor", "major"]].agg(["sum", "mean"])
    err_summary.to_csv(DATA_DIR / "error_summary.csv")
    print("\n=== Error rates by group ===")
    print(err_summary)

    # ── Figures ─────────────────────────────────────────────────────────────
    make_figure_1()
    make_figure_2a(df, wil)
    make_figure_2b(df)
    make_figure_3(df)

    # ── Stats summary text ──────────────────────────────────────────────────
    with open(DATA_DIR / "stats_output.txt", "w") as f:
        f.write("=== SPICY-AI extended statistics (cases 1-50, n=50/group) ===\n\n")
        f.write("Total plans: 150 (50 per group)\n\n")
        f.write("Summary statistics:\n")
        f.write(sdf.to_string(index=False) + "\n\n")
        f.write("PRIMARY: Wilcoxon signed-rank, paired by case (Holm-Bonferroni across 12 tests):\n")
        f.write(wil[["domain", "groupA", "groupB", "meanA", "meanB", "W", "p", "p_holm"]].to_string(index=False) + "\n\n")
        f.write("SENSITIVITY: Mann-Whitney U, independent-samples (Holm-Bonferroni across 12 tests):\n")
        f.write(mw[["domain", "groupA", "groupB", "meanA", "meanB", "U", "p", "p_holm"]].to_string(index=False) + "\n\n")
        f.write(f"Primary vs sensitivity significance conclusions "
                f"{'AGREE on all 12 comparisons' if agree else 'DISAGREE on at least one comparison'}.\n\n")
        f.write("Kruskal-Wallis reviewer consistency (4 divided-cohort subsets):\n")
        f.write(kw.to_string(index=False) + "\n\n")
        f.write("PRIMARY: Error rates, McNemar's exact test (paired by case):\n")
        f.write(err_paired.to_string(index=False) + "\n\n")
        f.write("SENSITIVITY: Error rates, Fisher exact (independent-samples):\n")
        f.write(err.to_string(index=False) + "\n\n")
        f.write("Error rates by group:\n")
        f.write(err_summary.to_string() + "\n\n")
        f.write("Note: study is not powered to detect differences in major-error rates "
                "(observed counts 2-5 per arm); the null McNemar/Fisher results should be "
                "interpreted as a feasibility signal, not as evidence of equivalence.\n")

    print(f"\nAll outputs written under {DATA_DIR} and {FIG_DIR}")


# ── Figure 2A ───────────────────────────────────────────────────────────────
# No in-figure title: the figure legend/caption lives in the manuscript.
def make_figure_2a(df: pd.DataFrame, wil: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    x, width = np.arange(len(DOMAINS)), 0.25
    for i, g in enumerate(GROUPS):
        means = [df.loc[df.group == g, d[0]].mean() for d in DOMAINS]
        sds = [df.loc[df.group == g, d[0]].std(ddof=1) for d in DOMAINS]
        ax.bar(x + (i - 1) * width, means, width, yerr=sds, capsize=4,
               label=g, color=COLORS[g], edgecolor="black", linewidth=0.7,
               error_kw=dict(lw=1.1))

    ax.set_xticks(x)
    ax.set_xticklabels([d[1] for d in DOMAINS], fontsize=11)
    ax.set_ylabel("Mean Likert score (1\u20135)", fontsize=12)
    ax.set_ylim(0, 6.9)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    # Legend sits above the axes so it can never collide with the
    # significance brackets.
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005),
              frameon=False, ncol=3, fontsize=10.5)

    def bracket(x1, x2, y, p, h=0.08):
        if p >= 0.05:
            return
        label = "***" if p < 0.001 else "**" if p < 0.01 else "*"
        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=1.0, c="black")
        ax.text((x1 + x2) / 2, y + h, label, ha="center", va="bottom", fontsize=10)

    offs = {"Physician": -width, "SPICY-AI": 0.0, "GPT-4o": width}
    order = {("Physician", "SPICY-AI"): 0, ("SPICY-AI", "GPT-4o"): 1, ("Physician", "GPT-4o"): 2}
    for di, (dom, _) in enumerate(DOMAINS):
        sub = wil[wil.domain == dom].reset_index(drop=True)
        top = max(df.loc[df.group == g, dom].mean() + df.loc[df.group == g, dom].std(ddof=1) for g in GROUPS)
        y0 = max(top + 0.22, 5.3)
        for _, r in sub.iterrows():
            idx = order[(r.groupA, r.groupB)]
            bracket(di + offs[r.groupA], di + offs[r.groupB], y0 + idx * 0.42, r.p_holm)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf", "tiff"):
        fig.savefig(FIG_DIR / f"Figure2A.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved Figure 2A")


# ── Figure 2B ───────────────────────────────────────────────────────────────
def make_figure_2b(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    err_rates = (df.groupby("group")[["minor", "major"]].mean() * 100).reindex(GROUPS)
    y, h = np.arange(len(GROUPS)), 0.38
    bars_minor = ax.barh(y - h / 2, err_rates["minor"], h, label="Minor errors",
                         color="#E1A95F", edgecolor="black", linewidth=0.7)
    bars_major = ax.barh(y + h / 2, err_rates["major"], h, label="Major errors",
                         color="#B03030", edgecolor="black", linewidth=0.7)
    for bars in (bars_minor, bars_major):
        for b in bars:
            w = b.get_width()
            ax.text(w + 0.5, b.get_y() + b.get_height() / 2, f"{w:.1f}%", va="center", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(GROUPS, fontsize=11)
    ax.set_xlabel("Error rate (% of plans)", fontsize=12)
    # Leave headroom past the longest bar + its % label so the legend
    # (top-right, where the shortest bars sit) can never overlap anything.
    ax.set_xlim(0, max(err_rates.values.max() * 1.35, 25))
    ax.legend(loc="upper right", frameon=False, fontsize=10.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf", "tiff"):
        fig.savefig(FIG_DIR / f"Figure2B.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved Figure 2B")


# ── Figure 3 ────────────────────────────────────────────────────────────────
def make_figure_3(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(13.5, 4.8), sharey=True)
    rng = np.random.default_rng(seed=42)
    for ax, (dom, label) in zip(axes, DOMAINS):
        data = [df.loc[df.group == g, dom].values for g in GROUPS]
        bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                        medianprops=dict(color="black", linewidth=1.5),
                        flierprops=dict(marker="o", markersize=4, alpha=0.6))
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(GROUPS)
        for patch, g in zip(bp["boxes"], GROUPS):
            patch.set_facecolor(COLORS[g])
            patch.set_alpha(0.85)
            patch.set_edgecolor("black")
        # When a domain/group's Q1, median and Q3 all coincide (a single Likert
        # value accounts for the majority of responses), matplotlib correctly
        # draws a zero-height box -- but that can look like a missing/absent
        # box at a glance. Overlay an explicit marker so it reads as "IQR = 0"
        # rather than "no data".
        for i, (patch, g) in enumerate(zip(bp["boxes"], GROUPS)):
            d = df.loc[df.group == g, dom]
            q1, q3 = d.quantile(0.25), d.quantile(0.75)
            if q1 == q3:
                ax.plot([i + 1 - 0.275, i + 1 + 0.275], [q1, q1],
                        color="black", linewidth=3.5, solid_capstyle="butt", zorder=4)
                ax.annotate("IQR = 0", (i + 1, q1), xytext=(0, 11),
                            textcoords="offset points", ha="center", fontsize=8.5,
                            color="#333333", style="italic", zorder=5,
                            bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
        for i, d in enumerate(data):
            xs = rng.normal(i + 1, 0.07, len(d))
            ax.scatter(xs, d, s=10, alpha=0.35, color="black", zorder=3)
        ax.set_title(label, fontsize=11.5)
        ax.set_ylim(0.5, 5.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="x", labelsize=9.5)
    axes[0].set_ylabel("Likert score (1\u20135)", fontsize=12)
    fig.tight_layout()
    for ext in ("png", "pdf", "tiff"):
        fig.savefig(FIG_DIR / f"Figure3.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved Figure 3")


# ── Figure 1 (pipeline diagram) ─────────────────────────────────────────────
# Publication layout: single left-to-right generation flow; the curated
# knowledge base grounds the model from above; the plan output branches
# down into the study evaluation (solid) and up into the intended
# clinical-use pathway (dashed = not part of this study). No arrows cross.
def make_figure_1() -> None:
    fig, ax = plt.subplots(figsize=(13.2, 6.6))
    ax.set_xlim(0, 14); ax.set_ylim(0.2, 7.45); ax.axis("off")

    BLUE, BLUE_F   = "#2F5F8F", "#EAF1F8"
    AMBER, AMBER_F = "#A97A28", "#FDF3DC"
    GREEN, GREEN_F = "#3F7B3F", "#E6F2E6"
    RED, RED_F     = "#A93A3A", "#FBEAEA"
    GREY, GREY_F   = "#6B6B6B", "#F5F5F5"

    def box(x, y, w, h, lines, color, edge, dashed=False, lw=1.5):
        """lines: list of (text, fontsize, bold) tuples stacked vertically."""
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.14",
                           fc=color, ec=edge, linewidth=lw,
                           linestyle=(0, (5, 3)) if dashed else "solid")
        ax.add_patch(b)
        n = len(lines)
        for k, (txt, fs, bold) in enumerate(lines):
            cy = y + h * (n - k - 0.5) / n
            ax.text(x + w / 2, cy, txt, ha="center", va="center", fontsize=fs,
                    fontweight="bold" if bold else "normal", color="#1A1A1A",
                    linespacing=1.25)

    def arrow(x1, y1, x2, y2, color=BLUE, lw=1.8, dashed=False):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
            color=color, linewidth=lw, shrinkA=0, shrinkB=0,
            linestyle=(0, (5, 3)) if dashed else "solid"))

    ROW_Y, ROW_H = 3.4, 1.7    # main generation row
    TOP_Y, TOP_H = 5.9, 1.35   # knowledge base + intended-use row
    EV_Y,  EV_H  = 0.4, 1.5    # evaluation band

    # ── Main generation flow (left → right) ──────────────────────────────
    box(0.4, ROW_Y, 2.7, ROW_H,
        [("Clinical context", 10.5, True),
         ("RACPC referral:", 9, False),
         ("history, investigations,", 9, False),
         ("examination, risk factors", 9, False)],
        BLUE_F, BLUE)
    box(3.5, ROW_Y, 2.5, ROW_H,
        [("De-identification", 10.5, True),
         ("& prompt assembly", 10.5, True),
         ("structured case summary", 9, False)],
        AMBER_F, AMBER)
    box(6.4, ROW_Y, 3.5, ROW_H,
        [("DeepSeek-R1-Distill-Qwen-14B", 10, True),
         ("local SLM · Ollama · on-premises", 9, False),
         ("structured chain-of-thought", 9, False),
         ("(Dx \u2192 Ix \u2192 Mx \u2192 F/U)", 9, False)],
        GREEN_F, GREEN)
    box(10.3, ROW_Y, 3.3, ROW_H,
        [("Management plan output", 10.5, True),
         ("\u2264 200 words", 9, False),
         ("risk optimisation · investigations", 9, False),
         ("referrals · follow-up", 9, False)],
        BLUE_F, BLUE)

    mid = ROW_Y + ROW_H / 2
    arrow(3.1, mid, 3.5, mid)
    arrow(6.0, mid, 6.4, mid)
    arrow(9.9, mid, 10.3, mid)

    # ── Knowledge base grounds the model from above ───────────────────────
    box(5.9, TOP_Y, 4.5, TOP_H,
        [("Curated knowledge base (RAG)", 10, True),
         ("AHA/ACC Chest Pain 2021 · ACC/AHA/SCAI", 8.5, False),
         ("Revascularisation 2021 · CCS Dyslipidemia 2021", 8.5, False),
         ("RHH RACPC institutional protocol", 8.5, False)],
        RED_F, RED)
    arrow(8.15, TOP_Y, 8.15, ROW_Y + ROW_H, color=RED)
    ax.text(8.35, (TOP_Y + ROW_Y + ROW_H) / 2, "FAISS retrieval\ntop-k = 6 chunks",
            ha="left", va="center", fontsize=8.5, color=RED, style="italic")

    # ── Intended clinical use (dashed: future pathway, not this study) ────
    box(10.7, TOP_Y, 2.9, TOP_H,
        [("Intended clinical use", 10, True),
         ("clinician review & validation", 9, False),
         ("\u2192 final management plan", 9, False)],
        GREY_F, GREY, dashed=True)
    arrow(12.15, ROW_Y + ROW_H, 12.15, TOP_Y, color=GREY, dashed=True, lw=1.5)
    ax.text(12.35, (TOP_Y + ROW_Y + ROW_H) / 2, "future\nworkflow",
            ha="left", va="center", fontsize=8.5, color=GREY, style="italic")

    # ── Blinded evaluation (this study) ───────────────────────────────────
    box(0.4, EV_Y, 13.2, EV_H,
        [("Blinded Likert evaluation (this study)", 10.5, True),
         ("50 RACPC cases \u00d7 3 plan sources (physician · SPICY-AI · GPT-4o) = 150 plans",
          9.5, False),
         ("diagnostic accuracy · management appropriateness · completeness · "
          "clarity (1\u20135)  +  major / minor error flags", 9.5, False)],
        GREY_F, "#4A4A4A")
    arrow(11.95, ROW_Y, 11.95, EV_Y + EV_H)
    ax.text(11.75, (ROW_Y + EV_Y + EV_H) / 2, "scored without\nclinician editing",
            ha="right", va="center", fontsize=8.5, color=BLUE, style="italic")

    legend_elems = [
        Line2D([0], [0], color=BLUE, lw=2, label="Data / reasoning flow"),
        Line2D([0], [0], color=RED, lw=2, label="Guideline retrieval"),
        Line2D([0], [0], color=GREY, lw=2, linestyle=(0, (5, 3)),
               label="Intended future use (not evaluated here)"),
    ]
    ax.legend(handles=legend_elems, loc="upper left", bbox_to_anchor=(0.005, 0.99),
              frameon=False, fontsize=9, handlelength=2.4)

    fig.tight_layout()
    for ext in ("png", "pdf", "tiff"):
        fig.savefig(FIG_DIR / f"Figure1_pipeline.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved Figure 1 (pipeline)")


if __name__ == "__main__":
    main()
