# Models — Grid Load Forecasting Index (v1 list, fixed 2026-11-19)

Selection rule: open weights; a licence that allows research
evaluation; runnable on a Kaggle T4 or on CPU. Zero-shot,
univariate, no fine-tuning. Every fact below is from the model's
official model card, repository or paper, accessed 2026-11-19.
Library versions are the versions documented for the checkpoint at
access time; each adapter pins and records the exact version it
runs with.

The retrospective window starts 2025-11-03. Release dates were
re-checked on 2026-11-20 against the first public weights —
each checkpoint's Hugging Face repository creation date and
commit history, not the paper date — and corrected where the
two differed (DEVIATIONS.md). No model on this list was
released after the window start, so no model is flagged under
the contamination rule in PLAN.md.

## Summary

| Model | Checkpoint | Licence | Released | Released during window? |
|---|---|---|---|---|
| Chronos-Bolt (base) | amazon/chronos-bolt-base | Apache-2.0 | 2024-11-25 | No |
| Chronos-2 | amazon/chronos-2 | Apache-2.0 | 2025-10-30 | No |
| TimesFM 2.5 | google/timesfm-2.5-200m-pytorch | Apache-2.0 | 2025-09-02 | No |
| Moirai 2.0 | Salesforce/moirai-2.0-R-small | CC BY-NC 4.0 | 2025-08-06 | No |
| TiRex | NX-AI/TiRex | NXAI Community License | 2025-05-26 | No |
| Toto | Datadog/Toto-Open-Base-1.0 | Apache-2.0 | 2025-04-30 | No |
| Sundial | thuml/sundial-base-128m | Apache-2.0 | 2025-05-13 | No |
| Granite TTM r2 | ibm-granite/granite-timeseries-ttm-r2 | Apache-2.0 | 2024-10-08 | No |
| Moirai-MoE | Salesforce/moirai-moe-1.0-R-small | CC BY-NC 4.0 | 2024-11-01 | No |
| Time-MoE | Maple728/TimeMoE-50M | Apache-2.0 | 2024-09-21 | No |

Dropped candidate: TabPFN-TS (see the end of this file and
DECISIONS.md #10).

## Per-model records

### Chronos-Bolt (base) — Amazon

- **Checkpoint:** `amazon/chronos-bolt-base` (205M parameters).
- **Licence:** Apache-2.0.
- **Library:** `chronos-forecasting` (pip).
- **Released:** 2024-11-25 (Hugging Face repository created
  that day; the AWS Machine Learning Blog announced the
  Chronos-Bolt family on 2024-12-02).
- **Training data, as published:** the model card states the model
  "has been trained on nearly 100 billion time series
  observations" and does not name the corpus. No cutoff date is
  published.
- **US load data:** not documented — the corpus is not named, so
  whether EIA-930, PJM or ERCOT data is in it is not published.
- **Context:** maximum 2,048 (model card comparison table), so the
  index's 2,048-hour context applies in full.

### Chronos-2 — Amazon

- **Checkpoint:** `amazon/chronos-2` (120M parameters).
- **Licence:** Apache-2.0.
- **Library:** `chronos-forecasting` >= 2.0 (pip, per the model
  card).
- **Released:** 2025-10-30 (Hugging Face repository created
  that day; technical report arXiv:2510.15821, 2025-10-17) —
  before the window start.
- **Training data, as published:** the model card lists a subset
  of the Chronos Datasets collection (excluding the test portion
  of datasets that overlap with GIFT-Eval), a subset of GIFT-Eval
  Pretrain, and synthetic univariate and multivariate data. No
  single cutoff date is published.
- **US load data:** EIA-930, PJM and ERCOT are not named. The
  parent Chronos corpus includes an electricity-consumption
  dataset (the UCI Electricity Consuming Load series, Portuguese
  households), which is not US grid data.
- **Context:** maximum 8,192; the index passes 2,048.

### TimesFM 2.5 — Google

- **Checkpoint:** `google/timesfm-2.5-200m-pytorch` (200M
  parameters).
- **Licence:** Apache-2.0.
- **Library:** `timesfm` 2.x (pip).
- **Released:** 2025-09-02 (Hugging Face repository created
  that day; google-research/timesfm release notes followed on
  2025-09-15).
- **Training data, as published:** the model card lists
  GiftEvalPretrain; Wikimedia Pageviews with a cutoff of November
  2023; Google Trends top queries to the end of 2022; and
  synthetic and augmented data. The list names source families,
  not individual series.
- **US load data:** EIA-930, PJM and ERCOT are not named in the
  published list. Every dated source predates the window.
- **Context:** maximum 16,000+; the index passes 2,048.

### Moirai 2.0 — Salesforce

- **Checkpoint:** `Salesforce/moirai-2.0-R-small`.
- **Licence:** CC BY-NC 4.0; the card states "This release is for
  research purposes only." The licence allows this non-commercial
  research evaluation.
- **Library:** `uni2ts` (SalesforceAIResearch/uni2ts, installed
  from the repository).
- **Released:** 2025-08-06 — the weights were public on
  Hugging Face that day ("initial commit" and "Push model
  using huggingface_hub" in the repository's commit history;
  Salesforce announced the model on 2025-08-08). The November
  2025 date recorded in the first version of this file is the
  arXiv paper (2511.11698), not the release. The date was
  corrected after scoring; see DEVIATIONS.md. The model was
  not released during the window and is not flagged.
- **Training data, as published:** the model card lists a subset
  of GIFT-Eval Pretrain, the GIFT-Eval train split ("non-leaking
  historical context"), and internal Salesforce operational data.
  No cutoff date is published.
- **US load data:** EIA-930, PJM and ERCOT are not named.
- **Context:** patch-based, flexible; the index passes 2,048.

### TiRex — NX-AI

- **Checkpoint:** `NX-AI/TiRex` (35M parameters, xLSTM).
- **Licence:** NXAI Community License (a Llama-3-style community
  licence: royalty-free use, with a commercial licence required
  only for organisations above €100M annual revenue). It allows
  this research evaluation.
- **Library:** `tirex-ts` 1.1.1 (pip).
- **Released:** 2025-05-26 (Hugging Face repository created
  that day; paper arXiv:2505.23719, May 2025).
- **Training data, as published:** the model card's dataset
  metadata lists `autogluon/chronos_datasets` and
  `Salesforce/GiftEvalPretrain`. No cutoff date is published.
- **US load data:** EIA-930, PJM and ERCOT are not named.
- **Context:** designed for long contexts; the index passes 2,048.
- **Run note:** TiRex's optional custom CUDA kernels need compute
  capability 8.0 or later; a Kaggle T4 is 7.5, so on T4 the model
  runs through its standard PyTorch path (or on CPU). This is
  verified when the adapter is built.

### Toto — Datadog

- **Checkpoint:** `Datadog/Toto-Open-Base-1.0` (151M parameters).
- **Licence:** Apache-2.0.
- **Library:** `toto-ts` (pip; project code at DataDog/toto).
- **Released:** 2025-04-30 (Hugging Face repository created
  that day; paper arXiv:2505.14766, 2025-05-20).
- **Training data, as published:** the paper describes a corpus
  of about 2.36 trillion time points: Datadog's own observability
  telemetry, open datasets, and synthetic data; the model card's
  dataset metadata lists `Salesforce/GiftEvalPretrain` and
  `autogluon/chronos_datasets` among the open datasets. No cutoff
  date is published.
- **US load data:** EIA-930, PJM and ERCOT are not named; the
  proprietary part of the corpus is observability telemetry, not
  grid data.
- **Context:** the checkpoint's configured maximum applies if
  below 2,048; the effective length passed is recorded at run
  time.

### Sundial — THUML

- **Checkpoint:** `thuml/sundial-base-128m` (128M parameters).
- **Licence:** Apache-2.0.
- **Library:** `transformers` (AutoModelForCausalLM with the
  model code from thuml/Sundial).
- **Released:** 2025-05-13 (Hugging Face repository created
  that day; paper arXiv:2502.00816, February 2025; ICML 2025
  spotlight).
- **Training data, as published:** TimeBench, a corpus of about
  1.03 trillion time points curated from public datasets; the
  model card's dataset metadata lists `thuml/UTSD`,
  `Salesforce/lotsa_data` (LOTSA) and
  `autogluon/chronos_datasets`. No cutoff date is published.
- **US load data:** EIA-930, PJM and ERCOT are not named in the
  published corpus lists. LOTSA and the Chronos corpus include
  other electricity datasets (the UCI Electricity Consuming Load
  series, ETT), none of them US grid data.
- **Context:** 2,880 in the paper's configuration; the index
  passes 2,048.

### Granite TTM r2 — IBM

- **Checkpoint:** `ibm-granite/granite-timeseries-ttm-r2`
  (TinyTimeMixers, ~1M parameters per variant).
- **Licence:** Apache-2.0.
- **Library:** `granite-tsfm` (pip).
- **Released:** 2024-10-08 (Hugging Face repository created
  that day; TTM r2 followed in January 2025; paper
  arXiv:2403.14960, NeurIPS 2024).
- **Training data, as published:** the model card lists the
  training collection explicitly: Australian Electricity Demand,
  Australian Weather, London Smart Meters, solar and wind power
  datasets, traffic datasets (PEMS family), KDD Cup 2018 and
  Bitcoin — about 700M samples, all with clear commercial-use
  licences. No cutoff date is published.
- **US load data:** electricity demand data is present, but it is
  Australian demand and London meter data. No EIA-930, PJM, ERCOT
  or other US grid data appears in the published list.
- **Context:** the checkpoint publishes one revision per
  context length (512, 1,024 and 1,536 hours, each with a
  96-hour head), all below the index's 2,048. The scored run
  uses the 1,536-hour revision (`1536-96-r2`), the model's
  maximum under the brief's context rule; the first v1 run
  used the 512-hour default revision. Both versions are
  reported in DEVIATIONS.md. The model runs comfortably on
  CPU.

### Moirai-MoE — Salesforce

- **Checkpoint:** `Salesforce/moirai-moe-1.0-R-small` (117M
  parameters total, 11M activated).
- **Licence:** CC BY-NC 4.0 (the Moirai family licence; the card
  marks the release as for research purposes). The licence allows
  this non-commercial research evaluation.
- **Library:** `uni2ts` (SalesforceAIResearch/uni2ts).
- **Released:** 2024-11-01 (Hugging Face repository created
  that day; paper arXiv:2410.10469, October 2024).
- **Training data, as published:** LOTSA, the corpus assembled
  for Moirai (27B+ observations across nine domains). No cutoff
  date is published.
- **US load data:** EIA-930, PJM and ERCOT are not in LOTSA's
  published dataset list; LOTSA includes other electricity
  datasets (UCI Electricity Consuming Load, ETT), not US grid
  data.
- **Context:** patch-based, flexible; the index passes 2,048.

### Time-MoE — Time-MoE project

- **Checkpoint:** `Maple728/TimeMoE-50M` (113M parameters total,
  50M activated). The 200M variant exists; the 50M is the base
  benchmarked variant and keeps the run inside the free-tier
  budget.
- **Licence:** Apache-2.0.
- **Library:** `transformers` with the model code from the
  Time-MoE repository (AutoModelForCausalLM).
- **Released:** 2024-09-21 (Hugging Face repository created
  that day; paper arXiv:2409.16040; ICLR 2025 spotlight).
- **Training data, as published:** Time-300B, an open corpus of
  about 309 billion time points across more than nine domains,
  published on Hugging Face with the model. No cutoff date is
  published.
- **US load data:** EIA-930, PJM and ERCOT are not named in the
  published description of Time-300B; its energy-domain series
  come from public collections (ETT and similar), not US grid
  reporting.
- **Context:** up to 4,096; the index passes 2,048.

## Dropped candidates

### TabPFN-TS — dropped (DECISIONS.md #10)

The current TabPFN-TS releases (tabpfn-time-series >= 1.0) run on
TabPFN-3 / TabPFN-3.5 checkpoints. Those weights are gated:
downloading them requires accepting Prior Labs' licence on their
site first. The licence (TABPFN-3 License v1.0 and the TABPFN-3.5
License v1.0) explicitly allows testing, evaluation and *internal*
benchmarking, and bars commercial and production use; it does not
grant publication of benchmark results, which is what this index
exists to do. The candidate therefore fails the selection rule as
it stands in November 2026: the weights are not openly downloadable
and the licence does not clearly allow this evaluation's results
to be published. Revisit if a TabPFN checkpoint is released under
a licence that allows published research evaluation.
