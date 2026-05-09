# 📌 HOMEWORK

<a id="homework-top"></a>

## Homework 3: AI Report Validation System — Submission Report

🕒 *Compiled for course submission*

---

## Checklist Mapping (per [`Reference Docs/HOMEWORK3.md`](Reference%20Docs/HOMEWORK3.md))

| Rubric bucket | Points | Where addressed in this file |
|---------------|--------|------------------------------|
| Writing component (~500 words, your own explanation) | 30 | [Writing component](#writing-component-student-authored) |
| Git repository links | 20 | [Git repository links](#-git-repository-links) |
| Screenshots / outputs (4–5+) | 25 | [Screenshots / outputs](#-screenshots--outputs) |
| Documentation | 25 | [Documentation](#-documentation) |

---

## 🔗 Git repository links

Base repository: **[Agentic-Flight-Report](https://github.com/JdogLloyd1/Agentic-Flight-Report)** (`JdogLloyd1` / `main` branch).

| Resource | Purpose |
|---------|---------|
| [`hw quality control/run_validation.py`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/run_validation.py) | Validation system script — calls the validator LLM, writes scores to CSV |
| [`hw quality control/validation_criteria.md`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/validation_criteria.md) | Validation criteria / rubric definition (dimensions, scale, benchmarks) |
| [`hw quality control/experiment_data/validation_scores.csv`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/experiment_data/validation_scores.csv) | Machine-readable validation results for every scored synthesis |
| [`hw quality control/run_statistics.py`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/run_statistics.py) | Statistical comparison (Bartlett, ANOVA / Welch, boxplot export) |
| [`hw quality control/run_agent3_experiment.py`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/run_agent3_experiment.py) | Prompt experiment runner (Prompt A / B / C, `n` runs per prompt) |
| [`hw quality control/experiment_data/synthesis_runs/A_001.md`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/experiment_data/synthesis_runs/A_001.md) | Example synthesized report validated in the experiment *(one of thirty; see sibling `B_*`, `C_*`)* |

Pipeline overview (Phases 0–4): [`HOMEWORK_PIPELINE.md`](HOMEWORK_PIPELINE.md).

---

## 📸 Screenshots / outputs

### 1. Validation system in action

![Terminal / session showing validation running (`run_validation`-style invocation)](Screenshots%20for%20Documentation/validation_in_action.png)

### 2. Validation output for one evaluated synthesis (scores + rationale)

![Sample validator output showing dimension scores and short strengths/weaknesses](Screenshots%20for%20Documentation/validation_results.png)

### 3. Validation criteria / rubric (text criteria)

Course rubric allows a rubric screenshot *when the criteria are visual*. Here the rubric lives in **`validation_criteria.md`** as structured tables rather than GUI tool output. **The canonical criteria table for grading is reproduced under [Documentation → Validation criteria table](#validation-criteria-table)** so every dimension remains traceable without a redundant figure.

*(Optional for your Canvas `.docx`: insert a screenshot of `validation_criteria.md` rendered in your editor or browser if your grader prefers a photographic rubric artifact.)*

### 4. Statistical analysis (terminal output — Bartlett + ANOVA)

![Run overview, Bartlett test, ANOVA table from `run_statistics.py`](Screenshots%20for%20Documentation/run_statistics_terminal.png)

### 5. Comparison of scores across prompts (box plot)

![Box plot of overall validation score by `prompt_id` (A / B / C)](experiment_data/overall_score_by_prompt.png)

---

<a id="writing-component-student-authored"></a>

## 📝 Writing component 

I built a quality control agent that evaluates the quality of a data reporter module from my Agentic Flight Report pipeline. In the agentic pipeline, Agent 3 aggregates API tool calls from Agent 1 and RAG information from Agent 2 to craft a coherent picture of airspace risk to the flight in question; Agent 4 then takes this output and condenses it for the customer. I tested 3 different prompts for Agent 3 with a fixed Agent 1/Agent 2 input to isolate the impacts of prompting. The results of each prompt were evaluated on a strict 1-5 scale system for different validation criteria, combined with a checklist coverage percentage and a Boolean grounding gate. Instead of reusing the class lab's generic essay quality Likert scales, I separate scoring by sector: live/reference separation, honest gap-calibration vs empty tools, grounding to JSON, capped concision penalties. The full breakdown can be viewed in [`validation_criteria.md`](validation_criteria.md).

For the experiment I pulled one frozen upstream snapshot off the manifest ([`experiment_data/run_manifest.json`](experiment_data/run_manifest.json)): AA 849 DFW→BOS, 2026-04-27. Prompt flavors were *A** (baseline airspace), **B** (exec‑brief vibe), **C** (lead with uncertainty). Each prompt was run `n = 10` times, resulting in 30 scored rows overall (`A_001` … `C_010`).

I used a modified lab statistics script titled **`run_statistics.py`**. That script looked at **`overall_score`**— the mean of the five core 1–5 scores in each CSV row—and asks whether **A/B/C** could plausibly differ. It prints the verbal analysis, runs Bartlett to sanity‑check variance across groups, and if  \(\alpha = 0.05\), it runs a standard one-way ANOVA test on \(H_0\colon \mu_A = \mu_B = \mu_C\). If the spreads did not meet the threshold, the script automatically switches to Welch ANOVA instead. A **`prompt_id`** box plot saved as **`overall_score_by_prompt.png`** was also generated to eyeball overlap and weird outliers. 

In my actual results, Bartlett came back around \(p \approx 0.246\), so the pooled ANOVA path was run instead of Welch. The omnibus test was pretty flat: \(F_{2,27} \approx 0.216\), \(p \approx 0.807\), partial \(\eta^2 \approx 0.016\)—so none of the prompts stood out on their own as clearly better solution based on **`overall_score`**. The sample means hug each other (C \(\approx 4.60\), B \(\approx 4.56\), A \(\approx 4.52\)). The closeness in scores may be due to only 10 samples per prompt and Agent 3 not tightly bound enough to phrase things differently even when the upstream JSON is fixed, meaning more drastically different prompt wording may be necessary to demonstrate a validation difference. 

I tweaked the rubric a few times early on — the validator was initially handing out closely spaced, very high scores to almost everything. I added more granular details for scoring levels and verbiage such as "if you're unsure, score lower." Changes resulted in some more spread observed in the scoring, but the validator still struggled to give scores lower than a 3, if any. Improvement efforts for a production effort would first work on tightening the scoring system to grade more critically.  

---

## 📚 Documentation

### System design summary

Agent 3 writes syntheses (`experiment_data/synthesis_runs/*.md`) from frozen Agent 1 + Agent 2 artifacts. **`run_validation.py`** submits each Markdown file to a validator model (role `VALIDATOR_ROLE` in that script — see repo link) structured to emit JSON dimension scores aligned with **`validation_criteria.md`**. Scores accumulate in **`validation_scores.csv`**. **`run_statistics.py`** reads the CSV and runs **Bartlett** then **ANOVA** (or Welch ANOVA if variances diverge).

### Validation criteria table

| Dimension | Description | Scale | Benchmark |
|-----------|-------------|-------|-----------|
| `live_reference_separation` | Clarity distinguishing LIVE operational snapshot vs FAA reference/context | Strict **1–5** | Operational **≥4** only if tagging is coherent end‑to‑end |
| `section_coverage` | Required operational themes rendered with specifics (NAS, delays, hubs, gaps) — not vague mentions | **1–5** | **≥4** demands concrete grounding in inputs |
| `grounding` | Numeric and factual alignment with LIVE JSON / Agent 2 reference | **1–5** | Penalize invented statistics or misplaced confidence |
| `gap_calibration` | Honesty about sparse / failed tool payloads | **1–5** | **≤3** if missing data is falsely glossed over |
| `concision` | No boilerplate stuffing; earns length operationally | **1–5** | Penalize repeating reference slabs |
| `checklist_coverage_pct` | Structural completion of substantive `##` sections | **0–100** (nearest 5) | Separate from LAB-style abstract Likerts |
| `grounding_gate` | Hard contradiction check vs LIVE facts | **`true/false`** | Instant fail flag if breached |

**Contrast with LAB.** The LAB’s generic textual Likerts map general attributes (tone, neutrality, completeness *in the abstract*) *without* enforcing domain-specific fidelity to cockpit-style JSON ingestion. This homework couples rubric anchors to explicit **`(live)/(reference)` fidelity**, checklist coverage tooling, and a **deterministic-derived `overall_score`** (mean of the five core Likerts) for omnibus inference.

Canonical source: **[`validation_criteria.md`](https://github.com/JdogLloyd1/Agentic-Flight-Report/blob/main/hw%20quality%20control/validation_criteria.md)**.

### Experimental design snapshot

| Item | Specification |
|------|----------------|
| Factors | **`prompt_id` ∈ { A, B, C }** (three distinct synthesizer prompting strategies) |
| Runs per prompt | **10 scored syntheses** each → **30** rows in `validation_scores.csv` |
| Dependent variable (primary analysis) | `overall_score = mean(dimensions 1–5)` on **[1.0 , 5.0]** |
| Blocking / controls | Frozen Agent 1 + Agent 2 bundle per pilot flight (see manifest) |
| Validator model (this batch) | `gpt-oss:120b-cloud` (column logged in CSV) |

### Statistical analysis narrative

**Hypotheses.**

- \(H_0\): \(\mu_{\text{A}} = \mu_{\text{B}} = \mu_{\text{C}}\) *(equal population means on `overall_score`)*  
- \(H_a\): at least two prompt populations differ  

**Procedure.** Bartlett \(p > 0.05\) → proceed with classical **one-way ANOVA** via `pingouin`/`scipy`.

**Empirical realization (frozen experiment log).**

| Quantity | Value |
|---------|-------|
| Bartlett \(p\) | \(\approx 0.246\) |
| ANOVA \(F(2,\,27)\) | \(\approx 0.216\) |
| ANOVA \(p\)-value | \(\approx 0.807\) |

**Interpretation.** Fail to reject \(H_0\). Prompt choice did **not** produce a statistically detectable shift in aggregated validation quality across this modest sample. Do not claim one prompt “wins decisively”; cite the negligible effect size \(\eta_p^2 \approx 0.016\). For coursework science practice, optionally discuss whether **larger \(n\)**, narrower prompts, multi-flight blocking, or per-dimension contrasts would sharpen power — but absent those extensions, inference stops at an **equivocal omnibus** result.

### Technical details

| Detail | Guidance |
|--------|----------|
| Python env | `hw quality control/standalone/.venv` (install from `standalone/requirements.txt`; includes `pandas`, `pingouin`, `scipy`, `matplotlib`) |
| Secrets | Populate `standalone/.env` (`OLLAMA_API_KEY`, optional `HW_FLIGHT_VALIDATION_MODEL`, timeouts, hosts) |
| Artifact layout | `experiment_data/agent1_live.txt`, `agent2_reference.txt`, `synthesis_runs/*.md`, `validation_scores.csv`, `overall_score_by_prompt.png` |
| Prompt sources | **`agent3_prompts.py`** (B, C definitions) plus baseline **A** in `hw_flight.agents.airspace_synthesizer` |

### Usage instructions (minimal)

Executed from **`hw quality control/`**:

1. **Freeze upstream inputs** *(if refreshing)* — `standalone/run_smoke_agents_12.py` (see README in `standalone/`).
2. **Run prompt experiment**: `standalone\.venv\Scripts\python.exe run_agent3_experiment.py --n 10`.
3. **Validate**: same interpreter → `run_validation.py`.
4. **Statistics**: `run_statistics.py` → prints omnibus tables and writes **`experiment_data/overall_score_by_prompt.png`**.

---

← 🏠 [Back to Top](#homework-top)
