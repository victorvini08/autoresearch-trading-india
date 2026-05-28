# Real-World Autoresearch Loop — Design Spec

**Date:** 2026-05-28
**Branch:** `realworld-autoresearch`
**Status:** Draft for user review

---

## 1. Current state

- Strategy (`strategy.py`) is **locked**: cross-sectional 12-1 momentum-quality selection → bounded gross-targeting → vol-targeted gross. Last KEEP committed at `5c119fa` (ccae79c + direction-aware downside-vol estimator). Sealed test is **spent**.
- Development-era nightly autoresearch loop (`scripts/loop.py`, `scripts/run_overnight.py`) is **no longer scheduled**. Installed launchd jobs are only: `daily_update`, `premarket_scan`, `run_live`, `daily_report`, `dhan_token_refresh`. No `run_overnight.plist` exists.
- Paper trading via Dhan HQ is running at ₹1L capital, biweekly rebalance, CNC delivery. Produces ~5–6 realized trades per month.
- Trade-ledger truth lives in `portfolio.duckdb`: `desired_targets`, `submitted_orders`, `actual_fills`, `broker_positions`, `cash_ledger`, `position_lots`, `realized_trades`, `discrepancies`. Classifier outputs in `macro.duckdb` / `news.duckdb`. All joinable.

## 2. Goal

Build the **only** mechanism by which `strategy.py` evolves going forward: a slow, evidence-gated, self-improving loop that observes paper trading, defends against execution/data/safety failures, and — when sample size and evidence warrant — formulates strategy hypotheses, validates them through the existing `prepare.py` + anti-overfit + sealed-test machinery (invoked on-demand), and promotes a new strategy version only on a clean pass.

The system must be **smart** (event-aware, portfolio-aware, classifier-calibrated), **robust** (cannot be fooled by 5–20 trades of noise; cannot lower its own gates), and **conservative** (default action is no change; bias structurally toward holding).

## 3. Core principle

**Live data is too sparse to drive strategy "improvement" for many months.** Bailey & López de Prado's Minimum Track Record Length on a 5–6 trades/month book is 2–7 years before live evidence can statistically distinguish strategy decay from noise.

The real-world loop is therefore architected with two distinct outputs:

1. **Always-on diagnostics and safety** (deterministic, runs daily). Detects execution drift, classifier miscalibration, safety-state transitions. This is where 95% of value comes from in the first year.
2. **Rare, gated strategy evolution** (LLM + on-demand validator). Only fires when (a) sample size threshold met, (b) causal evidence present, (c) deterministic validator passes. Invokes the full `prepare.py` anti-overfit suite + a fresh sealed-test reveal. Promotes only on clean pass.

Asymmetry is the design: easy to de-risk, hard to add risk, near-impossible to act on small samples.

## 4. Architecture

```
EXISTING (unchanged)                            NEW
────────────────────                            ───

09:00 IST   premarket_scan ─┐
09:30 IST   daily_update    ─┤
10:15 IST   run_live        ─┤ → portfolio.duckdb {desired_targets,
15:35 IST   daily_report    ─┘     submitted_orders, actual_fills,
                                   broker_positions, cash_ledger,
                                   position_lots, realized_trades,
                                   discrepancies}

16:00 IST   ────────────────────►  ① realworld_monitor.py
                                       (deterministic, no LLM)
                                       writes realworld.duckdb:
                                       - reconciliation
                                       - attribution (signal/construction/
                                         execution/cost/event-study)
                                       - classifier_calibration
                                       - safety_state (state machine)
                                       - events (rule firings)

Last Sat 11:00 IST OR event-triggered ──►  ② realworld_review.py
                                              (LLM, Opus 4.7, READ-ONLY)
                                              + deterministic policy validator
                                              writes:
                                              - realworld_journal.md
                                              - realworld.duckdb.hypotheses
                                              - realworld.duckdb.audit
                                              - state/priors_from_realworld.json
                                              CANNOT change safety_state.

When a hypothesis is PENDING and CONFIDENCE=high ──►  ③ realworld_validator.py
                                              (on-demand, NOT scheduled)
                                              invokes prepare.py +
                                              anti-overfit suite +
                                              FRESH sealed-test reveal.
                                              On clean pass: writes new
                                              strategy.py version + row in
                                              strategy_versions table.
                                              On any failure: writes
                                              hypothesis state=REJECTED.
```

**Three components total.** No nightly cron. No parallel processes. ③ is the only mechanism that ever edits `strategy.py`, and it only runs when ② has produced a high-confidence hypothesis that the validator accepts.

## 5. Data layer — `realworld.duckdb`

Separate database from `portfolio.duckdb` (broker truth must stay sacred). Five tables.

### `reconciliation`
One row per (date, ticker) for any name that touched the book. Columns:
- `date`, `ticker`, `mode`
- `desired_target_pct`, `submitted_qty`, `filled_qty`, `held_qty_eod`
- `target_vs_submitted_delta`, `submitted_vs_filled_delta`, `filled_vs_held_delta`
- `cause` enum: `whole_share_rounding | cap_binding | partial_fill | data_delay | halt | mark_drift | manual_override | unexplained`
- `notes`

Every non-zero delta MUST have a `cause`. `unexplained` is a hard alert.

### `attributions`
One row per realized trade. The new attribution stack (not Brinson):
- Identity: `trade_id`, `ticker`, `sector`, `entry_date`, `exit_date`, `holding_days`, `mode`
- Economics: `entry_price`, `exit_price`, `qty`, `realized_pnl_inr`, `realized_pnl_pct`
- **Signal layer**: `rank_at_entry`, `momentum_score_at_entry`, `quality_score_at_entry`, `score_decile_at_entry`, `rank_ic_contribution`
- **Construction layer**: `ideal_fractional_target_pct`, `bounded_target_pct`, `whole_share_target_pct`, `construction_drag_bps`
- **Execution layer**: `target_pct`, `submitted_pct`, `filled_pct`, `held_pct`, `entry_slippage_bps`, `exit_slippage_bps`, `expected_entry_slippage_bps`, `expected_exit_slippage_bps`
- **Cost layer**: `dp_charge_actual_inr`, `dp_charge_expected_inr`, `stt_actual_inr`, `exchange_fee_actual_inr`, `total_cost_bps`, `cost_delta_vs_backtest_bps`
- **Event-study layer**: `macro_regime_at_entry`, `sentiment_at_entry`, `events_at_entry` (JSON), `mpc_overlap`, `india_vix_zone_at_entry`, `fii_concentration_at_entry`
- **Benchmark**: `nifty_return_over_holding_pct`, `nifty500_return_over_holding_pct`, `excess_return_pct`

Brinson decomposition is available as a SQL VIEW for dashboard parity, but the primary lens is the five-layer pipeline.

### `classifier_calibration`
One row per (classifier, score_date, ticker_or_market). Probabilistic-classifier-friendly:
- `classifier` enum: `macro_regime | sentiment | events | india_vix_regime`
- `predicted_value`, `predicted_proba_distribution` (if probabilistic), `labeled_outcome`, `label_definition_hash`, `label_version`
- `is_correct`, `brier_score`, `log_loss`, `class_conditional_recall_json`
- `baseline_random_guess_score`, `baseline_always_neutral_score`

Label definitions: `macro_regime` labeled by sign of Nifty 30d forward; `sentiment` per-ticker by sign of name's 5d forward excess return; `events` by realized ±1.5σ move within 5d; `india_vix_regime` by realized VIX 30d forward. Definitions stored as versioned hashes so we can detect when we changed the labeling logic itself.

### `events`
One row per pre-declared rule firing. Schema:
- `event_id` (uuid), `triggered_at`, `trigger_type`, `trigger_details` (JSON)
- `processed_by_review_id` (nullable), `action_taken`
- `severity` enum: `info | warning | critical`

Triggers detailed in §7.

### `hypotheses` (trial ledger)
Append-only. Schema:
- Identity: `hypothesis_id` (uuid), `created_at`, `created_by_review_id`, `created_by_event_id` (nullable)
- Content: `text`, `text_lexical_hash`, `text_embedding` (vector), `category` enum: `risk_off | universe_filter | signal_decay | cost | classifier | sizing | execution`, `safety_class` enum: `safe | moderate | dangerous`, `confidence` enum: `low | medium | high`
- Evidence: `supporting_trade_ids` (JSON array), `supporting_event_ids` (JSON array), `data_window_start`, `data_window_end`, `feature_versions` (JSON)
- Mechanism: `causal_story` (text), `predeclared_test` (text — falsification metric+threshold), `expected_mechanism` (text)
- Lifecycle: `state` enum: `PENDING | VALIDATOR_REJECTED | VALIDATOR_KEPT | OBSOLETE | WITHDRAWN | EXPIRED`, `expires_at` (default 90d)
- Validator writeback: `validator_run_id`, `validator_decision`, `validator_decided_at`, `validator_metrics_json`, `new_strategy_version_hash` (nullable)

### `audit`
One row per ② LLM run. Schema:
- `review_id` (uuid), `run_at`, `trigger` enum: `monthly | event_triggered | manual`
- `input_snapshot_hash`, `prompt_version`, `model_id`, `output_json` (full LLM output before validation), `validator_version`, `validator_result` (passed/failed), `validator_failures_json`
- `wrote_journal` (bool), `wrote_hypotheses_count`, `wrote_priors` (bool)

Plus a separate `strategy_versions.duckdb` (or directory of `.py` snapshots + index CSV — lowest tech that works) for SEBI material-change defensibility. Schema:
- `version_hash`, `created_at`, `iteration_id` (nullable; only ③-created versions get one), `parent_version_hash`, `unified_diff`, `gate_results_json`, `sealed_test_metrics_json`, `journal_excerpt`
- File at `state/strategy_versions/<hash>.py` (full snapshot)

## 6. Component ① — `scripts/realworld_monitor.py`

Daily 16:00 IST, ~10s, pure SQL/Python. Idempotent and append-only.

Steps:
1. For every new row in `portfolio.duckdb.realized_trades` since last run, build the corresponding `attributions` row by joining against `desired_targets`, `actual_fills`, `broker_positions`, `prices.duckdb`, `macro.duckdb`, `news.duckdb`, `universe.duckdb`.
2. For every (date, ticker) that touched the book today, build a `reconciliation` row. Every non-zero delta must be assigned a `cause`; `unexplained` deltas write a critical event.
3. For every (classifier, label-matured-day), compute calibration scores into `classifier_calibration`.
4. Evaluate event triggers (§7). New firings → rows in `events`.
5. Evaluate safety state machine (§8) using the day's closing `broker_positions` + `cash_ledger`. State transitions → row in `events` + side-effect file writes (`state/risk_multiplier.json`, `state/halt.json`).

T+1 cash-math invariant enforced here: `available_cash_for_rebalance = settled_cash - pending_buys_not_yet_filled`. Same-day sale proceeds do NOT count as available cash. Phase 0 verifies the existing executor honors this.

## 7. Event triggers (deterministic, version-controlled in `data/realworld_event_rules.py`)

| Trigger | Definition |
|---|---|
| `DRAWDOWN_STATE_CHANGE` | Safety state machine transitioned (§8). |
| `REGIME_PERSIST_WITH_EDGE` | `macro_regime` flipped and persisted ≥ 2 weeks AND historical backtest under that regime label shows materially different expected return/risk vs base rate (p < 0.05 on backtest historical sub-periods). Persistence alone is not evidence. |
| `CLASSIFIER_DRIFT` | Rolling 90d Brier score (probabilistic) or log-loss (class) for any classifier is worse than the "always neutral" baseline at p < 0.05. Per-class recall stored alongside. |
| `COST_SURGE` | Realized cost in bps of traded value, decomposed by component (DP, slippage, STT, exchange fee), is > 2× the backtest-model assumption for that component for ≥ 5 consecutive sells. |
| `POSITION_DRIFT_FROM_TARGET` | `held_pct - target_pct` exceeds ±200 bps for any held name for ≥ 3 sessions. |
| `RANK_IC_DECAY` | Live realized rank IC over rolling 60 sessions is outside the 5th–95th percentile of the backtest's rolling rank-IC distribution at p < 0.05. |
| `RECONCILIATION_BREAK` | Reconciliation row written with `cause=unexplained`. Critical severity. |
| `MPC_OVERLAP` | RBI Monetary Policy Committee meeting fell within the attribution window of any realized trade in the last 30 days. Info severity (don't claim clean evidence in those windows). |
| `INDIA_VIX_MA_CROSS` | Daily India VIX crosses its 200-day MA (in either direction). Practitioner literature documents 1–5 day lead on regime shifts. |
| `MANUAL_HALT` | `halt.json` toggled to halted by user. Override state. |

All firings write to `events`. Critical-severity firings additionally schedule an immediate ② run (out of cycle).

## 8. Safety state machine (deterministic, owned by ①)

**Calibrated to our strategy's actual backtest profile** (aggregate max DD 12.2%, worst-fold max DD 7.2%, mean Sortino 3.49 over 13 folds). Wright Research's 10% threshold was too tight — it would trigger on routine drawdowns our strategy is designed to tolerate.

```
   NORMAL ──peak-equity DD ≥ 8%──►   WATCH
                ◄──recover to within 3% of peak for 20 sessions──
                 (DD beyond worst-fold backtest of 7.2%; observation only)

   WATCH ──peak-equity DD ≥ 12%──►   RISK_REDUCED
                ◄──recover to within 5% of peak for 20 sessions──
                 (at aggregate backtest max DD; writes
                  state/risk_multiplier.json = 0.5; executor
                  applies multiplier at next rebalance)

   RISK_REDUCED ──peak-equity DD ≥ 16%──►   HALTED_REVIEW
                ◄──manual user reset only
                 (≈1.3× aggregate backtest max DD; clearly out of regime)

   HALTED_REVIEW ── (terminal; halt.json flipped to halted;
                    only user can reset to RISK_REDUCED)
```

**Wiring requirements (must be verified at implementation time, not assumed):**
- `scripts/executors/dhan.py` MUST read `state/risk_multiplier.json` and multiply gross targets by the multiplier before submitting orders. Without this read, the state machine is decorative.
- `scripts/run_live.py` MUST honor `state/halt.json` (already does today — verify the existing check still triggers).
- A regression test must verify: writing `risk_multiplier.json = {"multiplier": 0.5}` AND running the executor against the same intended targets produces orders at half the target weight.
- A regression test must verify: writing `halt.json` halted=true causes `run_live` to exit before order submission.

State is broker-truth (read from `broker_positions` + `cash_ledger`); not dependent on the sealed test being correctly priced. Transitions trigger:
- An event row in `events`.
- Write `state/risk_multiplier.json` and/or `state/halt.json`.
- Schedule an immediate ② run.

The LLM (② / ③) cannot change safety state. Only the deterministic controller can.

## 9. Component ② — `scripts/realworld_review.py`

**Last Saturday of month at 11:00 IST** OR event-triggered (critical events). Opus 4.7. **Read-only with respect to strategy.py and gates.**

(Saturday over Friday: Fridays are rebalance days; review should not compete with execution. Saturday gives clean overnight gap + market closed all weekend, so reasoning isn't anchored to intraday noise.)

### Prompt structure

Hard preamble (documentation; not the control):

```
You are an analyst reviewing live paper-trading results.

YOUR DEFAULT OUTPUT IS "NO CHANGE."

Hard constraints:
1. Sample size is ~5-8 realized trades/month. You CANNOT distinguish strategy
   decay from noise on this sample. Bias structurally toward "no action."
2. Every hypothesis must cite (a) specific trades in attributions that
   motivate it, (b) a CAUSAL story, (c) a falsification test (predeclared_test).
3. If safety_state != NORMAL: only `risk_off` category hypotheses allowed.
4. Re-proposing a hypothesis in state VALIDATOR_REJECTED is forbidden.
5. If realized_trades count < 30 (cold start): hypothesis generation
   suppressed entirely. Only execution/reconciliation/data-bug observations.
6. You cannot suggest changes to anti-overfit gates, sealed-test protocol,
   or safety_state machine. Those are immutable.
7. Hypotheses that propose new signals or hyperparameter retunes are
   classified `dangerous` and require confidence=high to enter validator.
```

Then assembled context: last 30d `attributions`, rolling 90d `classifier_calibration` summary, current `broker_positions`, last 6 months `hypotheses` with states, new `events`, tail of `realworld_journal.md`, sealed-test snapshot, `mpc_overlap` flags, India VIX zone, FII concentration HHI.

Strict JSON output schema (see §11 validator).

### Outputs (only if validator passes)

- Append to `realworld_journal.md` — human-readable monthly entry.
- Insert rows in `hypotheses` (PENDING state) for each accepted hypothesis.
- Insert row in `audit` (always — even on validator failure).
- Write `state/priors_from_realworld.json` — top hypotheses + classifier summary + cost deltas + active events. (Currently no nightly consumer; reserved for future ③ invocation and dashboard.)

### Deterministic policy validator (`data/realworld_review_validator.py`)

This is the **actual control surface**. The prompt is documentation; this is enforcement:

1. **Schema check** — every required field present, every enum-valued field in allowed values.
2. **Cold-start gate** — if `count(realized_trades) < 30`, no `hypotheses_for_validator` allowed. Only execution/reconciliation observations.
3. **Drawdown gate** — if `safety_state != NORMAL`, only `category=risk_off` hypotheses allowed.
4. **Causal-citation check** — every hypothesis has non-empty `supporting_trade_ids` ⊆ actual ids in `attributions`. Empty = reject.
5. **Falsifiability check** — every hypothesis has non-empty `predeclared_test`. Missing = reject.
6. **Duplicate detection** — `text_lexical_hash` checked against all `hypotheses` rows in state ∈ {VALIDATOR_REJECTED, OBSOLETE, WITHDRAWN, EXPIRED}. Optionally also embedding-similarity (Phase 6+). Hit = reject.
7. **Audit fields** — input snapshot hash, prompt version, model id, validator version, generation timestamp. All required.

On failure: re-call LLM once with failures appended; on second failure write `audit` row and exit. No silent acceptance.

## 10. Component ③ — `scripts/realworld_validator.py` (on-demand strategy evolution)

**This is the only path that ever edits `strategy.py`.** Not scheduled. Triggered explicitly by user or by ② when a hypothesis lands with `confidence=high`.

Workflow:
1. Read the hypothesis row from `realworld.duckdb.hypotheses`.
2. Read current `strategy.py`.
3. Invoke Claude Opus 4.7 with: hypothesis text + causal story + supporting evidence + current strategy → return a strategy.py edit that implements the hypothesis.
4. Run the full `prepare.py` walk-forward evaluator on the edited strategy.
5. Run the full anti-overfit suite (`backtest/anti_overfit.py`): Bonferroni, RW Monte Carlo, parsimony, sub-period stationarity, universe-respect.
6. Run a **fresh sealed-test reveal** on a held-out window not used since the last KEEP. (Sealed test is the immovable gate. If we are out of sealed data, the system halts here and asks the user to extend.)
7. Run capital-scale robustness at ₹5L (per locked decision #11).
8. If ALL gates pass AND sealed metrics improve AND ₹5L variant is robust:
   - Compute `version_hash`, write snapshot to `state/strategy_versions/<hash>.py`.
   - Write row in `strategy_versions` table with diff, gates, sealed metrics.
   - Atomically replace `strategy.py` with the new version.
   - Update hypothesis row state → `VALIDATOR_KEPT`.
   - Append a structured entry to `realworld_journal.md`.
9. If ANY gate fails:
   - Update hypothesis row state → `VALIDATOR_REJECTED`.
   - Store full failure detail in `validator_metrics_json`.
   - Do NOT touch `strategy.py`.

Validator does NOT auto-fire. User runs `uv run python -m scripts.realworld_validator <hypothesis_id>` when ready, or the system can schedule it for the next safe execution window. This preserves a human-in-the-loop on every strategy version change while still being a one-command operation.

Audit trail: every ③ run is journal-recorded and the new version is rollback-able by hash.

## 11. Cold-start behavior

For the first 30 realized trades (~4–6 months of paper trading), ②'s validator's cold-start gate suppresses all hypothesis generation. The LLM can still:
- Critique classifier calibration (data exists; just not trades).
- Flag reconciliation/execution/cost anomalies.
- Recommend safety-state observations (but cannot decide transitions).
- Record "insufficient evidence" notes in the journal.

Journal entries during cold-start are marked at the top: **"Cold-start mode (N=<count> realized trades): hypothesis generation suppressed until N≥30. Live PnL commentary is diagnostic, not inferential."**

## 12. What the loop is structurally prevented from doing

Code-enforced, not norm-enforced:

1. Cannot edit `strategy.py` or `prepare.py` from ② — no write path; only ③ touches strategy.py and only after gates pass.
2. Cannot lower anti-overfit gate thresholds — gates live in `backtest/anti_overfit.py`, untouched.
3. Cannot bypass sealed test — only `prepare.py` runs sealed, and only when ③ invokes it.
4. Cannot propose non-`risk_off` hypotheses during non-NORMAL safety state — validator rejects.
5. Cannot generate strategy hypotheses during cold-start — validator rejects.
6. Cannot re-propose burned hypotheses — validator's lexical+embedding duplicate check rejects.
7. Cannot mark itself as a KEEP — only ③ writes `state=VALIDATOR_KEPT`.
8. Cannot change safety state — only deterministic controller in ① writes safety_state.
9. Cannot trigger orders or toggle `halt.json` directly — only safety controller can.
10. Cannot produce artifacts on validator failure — `audit` row is the only writeback, then exit.

## 13. Sequencing (phases — each ships standalone value)

**Phase 0 — Reconciliation card in dashboard (~1.5 weeks).** Deterministic daily computation of five questions per date: (1) did we hold what we intended? (2) did execution match assumptions? (3) did live constraints distort the research book? (4) did the T+1 cash math hold? (5) did peak-equity drawdown cross 8%/12%/16%? Output surfaces as a new **"Reconciliation" card in `state/reports/dashboard.html`**, scoped to the selected date via the existing per-tab slider. No new md files. No LLM.

**Minimal additions per Codex review (folded in lean):**

- **Corporate-action awareness.** Small new file `storage/corporate_actions.json` (or single duckdb table) fetched daily from NSE corporate-actions page during the existing `daily_update`. Schema: `ex_date`, `ticker`, `type` (split | bonus | dividend | demerger | isin_change | suspension), `ratio_or_amount`, `new_symbol` (for ISIN changes). Reconciliation cause logic recognizes CA events — a 1:2 split shows as `cause=corporate_action` instead of `cause=unexplained`. Dividends credited to `cash_ledger.kind=dividend` so PnL is total-return.

- **Order-state truth (verify + extend, don't redesign).** Audit the existing Dhan integration: does it capture (a) partial fills as distinct from full fills, (b) rejections as distinct from "no fill yet", (c) all status transitions? Where it doesn't, extend the existing `submitted_orders.status` column to record the missing states. Reconciliation question 1 becomes precise: "5 of 6 names traded successfully, 1 partial fill (RELIANCE 80/100), 0 rejections" instead of just "5 fills."

- **Tax-aware capital tracking.** One SQL view on `realized_trades`: per-FY (Apr 1 → Mar 31) STCG (held < 12mo, 15%) + LTCG (held ≥ 12mo, 10% above ₹1L exemption). One new row in the reconciliation card: "FY26 tax reserve: ₹X (Y% of equity)" → deployable = equity − reserve. No separate card.

Independently useful and read in the user's existing daily workflow.

**Phase 1 — Full deterministic monitor (~2–3 weeks).** Create `realworld.duckdb` with all 5 tables. Populate `reconciliation`, `attributions` (covering BOTH realized trades AND currently-held positions — closed trades show realized PnL + excess return; held positions show unrealized PnL + entry-context-vs-current-context drift flags), `classifier_calibration`, `events`. Implement safety state machine + controller. No LLM yet. Run for 2–4 weeks against live paper book to verify reconciliation balances to within 1bp and event triggers fire correctly.

**Phase 2 — Historical replay of triggers (3–5 days).** Wire event triggers against historical paper-trading data. Confirm thresholds fire at sensible rates (not too noisy, not too silent). Tune.

**Phase 3 — LLM review in read-only mode (~1 week).** Build `scripts/realworld_review.py` + deterministic validator. Run monthly. Writes `realworld_journal.md` + `hypotheses` + `audit`. **③ NOT yet implemented.** Cold-start gate active (so first few months are observation-only anyway). Manually inspect 2–3 monthly runs and adversarially break the validator.

**Phase 4 — On-demand validator + strategy versioning (~1 week).** Build `scripts/realworld_validator.py`. Build `strategy_versions` storage. Wire hypothesis writeback. First few invocations are MANUAL only — user must run the command. Schedule consideration deferred to Phase 6+.

**Phase 5 — Dashboard integration (3–5 days).** Surface attribution stack, classifier calibration, safety state, hypothesis ledger in the existing dashboard. Make the journal entries linkable from the dashboard.

**Phase 6 — Optional refinements.** Shadow / challenger books (track ideal-research book and challenger variants daily, never trade them; gives concrete diff between "strategy as designed" and "strategy as executed"). Embedding-based duplicate detection. Auto-scheduling of ③ on high-confidence hypotheses.

## 14. Open questions for user review

1. **Phase 0 first, or jump to Phase 1?** Phase 0 ships in a week and shakes out reconciliation logic before we depend on it. Recommended: yes, Phase 0 first.
2. **Cold-start threshold — 30 trades or different?** 30 ≈ 5 months of paper. Could argue 15 or 50. 30 is conservative middle.
3. **Strategy versioning storage — separate `versions.duckdb` or directory of `.py` snapshots + CSV index?** Lowest-tech wins; I lean directory + CSV. Easier to grep, easier to back up.
4. **`realworld_journal.md` location — repo root for parity with `journal.md`?** Yes.
5. **Should ③ ever auto-fire on high-confidence hypotheses, or always manual?** I lean always-manual for v1; revisit after we see ② output quality.
6. **Shadow / challenger books in Phase 1 or Phase 6?** They're the highest-value diagnostic Codex called out. But they're also the most complex piece. I lean Phase 6 to avoid blocking Phase 1 on schema decisions.

---

## Appendix A — What the development-era nightly autoresearch loop did (for context)

`scripts/loop.py`: read journal → LLM proposed strategy.py edit → ran prepare.py walk-forward → atomic anti-overfit gates → KEEP/REVERT → wrote journal entry. Driven by `scripts/run_overnight.py` which iterated N times per night. **Has not run since strategy was locked.** Its machinery (`prepare.py`, `backtest/anti_overfit.py`, sealed-test reveal) is intact and is what ③ invokes on-demand.

## Appendix C — Codex final review (2026-05-28)

**Critical gaps surfaced:**

1. **Corporate-action ledger is mandatory.** Splits, bonuses, demergers, symbol/ISIN changes, delistings, suspensions, special dividends. Without a CA ledger, the loop will misclassify a data adjustment as alpha decay, fill error, or drawdown. Every position attribution must reference adjusted AND unadjusted price paths.

2. **Execution attribution needs order-state granularity.** Separate states: signal → intended order → placed order → accepted order → partial fill → rejected order → cancelled order → exchange-confirmed fill → broker-reconciled holding. Treating a partial fill or rejection as a clean fill poisons live IC, cost estimates, drift flags, and drawdown state.

3. **Tax accounting belongs in portfolio/dashboard, NOT strategy.** Dashboard must show pre-tax + post-tax equity, realized tax liability, available capital after tax reserve. Otherwise paper performance overstates live compounding.

4. **DuckDB/state corruption needs a recovery contract.** Daily snapshots + checksums + restore tests + single source-of-truth hierarchy: broker holdings/cash beats local DB; local DB explains history; dashboard flags mismatch.

5. **Fresh sealed-test idea is fragile.** Finite sealed data. Once validator repeatedly queries future-ish untouched data, it becomes development data. Define a data budget: e.g. one promotion window per calendar quarter; after depletion require shadow/live paper evidence rather than another sealed reveal.

**Silent-failure additions:**

- Live Rank IC must be computed against actual PIT tradeable universe on each signal date (post-liquidity, post-CA, post-halt filters). NOT against held names or current Nifty 500.
- Classifier-derived flags (Step 3 regime drift, Step 4 regime-persist-with-edge) must be marked TAINTED downstream if Brier degrades.
- Cost surge detection must decompose: brokerage, DP, STT, stamp duty, exchange fees, GST, slippage, impact — separately. Single "cost surge" flag hides whether problem is turnover, spread, failed limit behavior, or tax drag.
- Embedding dedup is convenience only. Real guard: structured hypothesis fingerprints — feature family, holding-period thesis, universe slice, risk-control change, expected failure mode.

**Sequencing corrections:**

- Step 2 (safety) BEFORE Step 4 (events) — correct as planned. Safety must be deterministic, minimal, early; it can emit events but must not depend on the event framework.
- Step 1 BEFORE Step 3 — correct. Step 3 must consume reconciled fills/holdings only, not raw broker snapshots.
- **Step 6 too dangerous as written.** Clean pass cannot immediately replace live strategy. Mandatory promotion chain: `VALIDATOR_KEPT` → `SHADOW_ACTIVE` (≥8-12 weeks OR ≥4 rebalance cycles) → compare vs incumbent on live eligible universe + realized costs + rejections + drift + drawdown → manual promote. This also solves part of sealed-data depletion.

**Self-improving claim:**

> "As written, this is mostly self-monitoring plus manual research escalation. That is not a criticism; it is safer."

Genuine self-improvement should come from **non-strategy adaptive operations**, NOT strategy mutation:
- Dynamically tighten/loosen execution limits based on realized slippage and rejection rate.
- Risk multiplier adjusts only through the deterministic state machine.
- Update classifier calibration/reliability weights when live Brier evidence is statistically strong.
- Update hypothesis priors for future validator ranking, without touching `strategy.py`.

Keep `strategy.py` promotion manual and shadow-gated. Let the system improve measurement, execution quality, and review prioritization automatically.

**Trader-side risks to flag explicitly:**

- Paper fills may materially understate slippage, partial fills, and rejection risk.
- ₹1L capital makes whole-share sizing, DP charges, single-name concentration noisy.
- 12.2% backtest max DD does NOT bound live DD. 16% halt is a governance threshold, not a worst case.
- Corporate actions and symbol changes create false PnL unless reconciled.
- Tax drag materially reduces compounding, especially at short holding periods.
- Model/classifier explanations are not truth; they are audit metadata.
- Strategy lock does not eliminate model risk, data risk, broker risk, or regime-break risk.
- Manual validator promotions can still overfit through repeated human selection.

**Headline design change:** Step 7 (shadow books) becomes **non-optional in reduced form**. Every validator-kept strategy MUST run as a shadow challenger before live replacement. That is the missing bridge between backtest robustness and real-world robustness.

---

## Appendix B — India-specific findings folded into this design

- **SEBI April 2026 "material change" defensibility** → `strategy_versions` table with version hashes, diffs, gate results, rollback artifact.
- **Wright Research published 10% portfolio DD → cash shift rule** → safety state machine peak-equity DD thresholds 7%/10%/15%.
- **Capitalmind documented ~25% live-vs-backtest CAGR gap** → fold into priors-file context so LLM knows India retail-scale degradation is real and bounded.
- **India VIX 200-day MA crossover** (documented 1–5d lead on regime shifts) → new classifier input + event trigger.
- **FII flow concentration as Herfindahl** across sector indices → new classifier input (distinct from raw flow).
- **RBI MPC ~10% of meetings >1.5σ** → `MPC_OVERLAP` event flag in monitor.
- **NSE intraday U-shape** (open/close expensive) → executor pre-trade window narrow to 11:30–14:00 IST (single-line change in `scripts/executors/dhan.py`).
- **T+1 cash math invariant** → reconciliation rule in Phase 0.
