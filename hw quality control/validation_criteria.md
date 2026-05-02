# Homework 3 — Custom validation criteria (Agent 3 synthesis)

This differs from the LAB’s generic Likert set (`accuracy`, `formality`, `faithfulness`, …) by scoring **merged aviation operational briefings** against **Agent 1 JSON + Agent 2 reference text**.

## Strict scale (validator prompt in `run_validation.py`)

| Score | Meaning |
|-------|--------|
| **5** | Exceptional on that dimension; teaching-example quality (**rare**). |
| **4** | Strong; at most **one minor** issue. |
| **3** | Acceptable but with **clear** limitations (typical “ships with caveats”). |
| **2** | Weak; major gaps or confusion. |
| **1** | Fails; contradictions, unsafe mix-ups, or unusable. |

The validator is instructed to **prefer the lower score when unsure**, avoid giving **5** on many dimensions at once without evidence, and **not** copy the same integer across all five Likerts unless each dimension truly earns it.

## Validation criteria table

| Dimension | Description | Scale | Strict benchmark |
|-----------|-------------|-------|------------------|
| **live_reference_separation** | Clarity of live vs reference; easy to misread operational vs book content | **1–5** | **4+** only if tagging is consistent end-to-end |
| **section_coverage** | NAS, weather, delays, other ops, hubs—**operationalized**, not generic mentions | **1–5** | **3** if themes appear but thin; **4+** only with specifics from inputs |
| **grounding** | Claims match LIVE JSON / Agent 2; no invented or over-precise numbers | **1–5** | Penalize any mismatch or “too confident” detail |
| **gap_calibration** | Empty/error/partial tools in Agent 1 reflected honestly—no false completeness | **1–5** | **≤3** if gaps are glossed over |
| **concision** | No boilerplate padding; sections earn their length | **1–5** | Penalize repeatable reference dumps |
| **checklist_coverage_pct** | Substantive `##` sections vs empty shells | **0–100** (nearest 5) | Stricter than “heading exists” |
| **grounding_gate** | No **clear** contradiction of LIVE JSON | **true/false** | **false** if any live fact wrong |

## Overall score (for ANOVA)

\[
\texttt{overall\_score} = \mathrm{mean}(\texttt{live\_reference\_separation}, \texttt{section\_coverage}, \texttt{grounding}, \texttt{gap\_calibration}, \texttt{concision})
\]

Range **1.0–5.0**, comparable to averaging LAB Likert dimensions.

## Implementation

- Validator system prompt: `run_validation.py` (`VALIDATOR_ROLE`).
- Model: `OLLAMA_MODEL` for agents; optional **`HW_FLIGHT_VALIDATION_MODEL`** (e.g. cloud GPT-OSS) for validation only — see `hw_flight.core.config` / `.env`.

## Prompt experiment (A / B / C)

| ID | Intent |
|----|--------|
| **A** | Baseline **Airspace Synthesizer** (production-style sections) |
| **B** | **Executive-brief** shape: short executive summary + capped subsections |
| **C** | **Uncertainty-first**: conservative language, explicit gaps, minimal inference beyond live JSON |

Prompt bodies: `agent3_prompts.py` (B, C) and `hw_flight.agents.airspace_synthesizer.ROLE` (A).
