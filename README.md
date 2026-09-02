# Petrologix

Hi There, This is a petroleum geology agent that reads well logs. It combines an XGBoost
lithology model trained on the FORCE 2020 Norwegian Continental Shelf dataset,
a deterministic porosity calculator, a geology RAG over a curated book corpus,
and Claude Sonnet 5 as the reasoning layer, behind a FastAPI backend and a brown
React HUD frontend.

The project began as a QLoRA fine-tune of Qwen2.5-7B-Instruct on geology Q/A.
That model is published and still runs on a Hugging Face T4 Space, and the
training log below is kept in full — but it is no longer the model in the live
path. See [The Qwen2.5-7B fine-tune](#part-ii--the-qwen25-7b-fine-tune) for what
it is, Acutally Oil  Geology is a dificult realm for a small 7B LLM it was built, and why I swtich backend to Claude-Sonnet.

- **Lithology model:** `petrologix` v2, XGBoost, 118 wells, shipped as a wheel
- **Agent:** Claude Sonnet 5 (`claude-sonnet-5`), tool-calling
- **Dataset (LLM):** [beaunix/geo-mind-qa](https://huggingface.co/datasets/beaunix/geo-mind-qa)
- **Model (LLM):** [beaunix/aegis-geo-mind-qwen2.5-7b-bnb-4bit](https://huggingface.co/beaunix/aegis-geo-mind-qwen2.5-7b-bnb-4bit)
- **Space (LLM demo):** [beaunix/aegis-geo-mind-demo](https://huggingface.co/spaces/beaunix/aegis-geo-mind-demo)

> Academic and educational project. Not validated for operational drilling or
> exploration decisions.

---

## Motivation

Publicly available geoscience-tuned LLMs are scarce, and none focus
specifically on petroleum geology. Petrologix targets that gap — but the
evaluation of the fine-tune (§4.2) changed the shape of the answer. A model can
reproduce expert register and reasoning structure perfectly and still state a
kerogen H/C ratio backwards with total confidence. Language models are good at
geological *reasoning* and bad at geological *numbers*.

So the system stopped trying to make one model do everything. Numbers come from
places that can actually produce them: a gradient-boosted classifier over log
curves, a closed-form porosity equation over RHOB, a retrieval corpus of real
books. The LLM interprets, and a guard layer checks what it says against what
it was given.

---

# Part I — The agent system

## A. Architecture

```
                    React HUD (Vite + TS + Tailwind + KaTeX)
                                    |
                              services/api.ts
                                    |
                         FastAPI  (app/main.py)
                                    |
                    +---------------+---------------+
                    |               |               |
              /predict          /chat          /wells/samples
                    |               |
                    +-------> agent/graph.py <------+
                                    |
        route -> [lithology] -> retrieve -> generate -> guard
                    |               |          |         |
              XGBoost model    Qdrant RAG   Claude    corrections
                                            + tools
```

Three things are deliberate here:

- **The heavy numeric work happens before the LLM is called.** The prediction is
  the expensive, trustworthy part of the answer; an LLM outage degrades the
  response to the raw tool summary rather than losing it.
- **The LLM never sees raw curves.** ~10k rows of log data go to the chart, not
  the prompt. The model sees a ~250-token text summary.
- **Whatever the model writes is checked before it ships.** See §E.

## B. The lithology model (XGBoost)

Trained on the full 118-well FORCE 2020 LAS set and shipped as a versioned
wheel (`wheels/petrologix-0.2.1-py3-none-any.whl`, model v2), so serving cannot
drift from training — the feature engineering lives inside the wheel and is
never reimplemented in this repo.

| | |
|---|---|
| Features | 29, engineered from 8 required curves |
| Required curves | GR, RDEP, RMED, RHOB, NPHI, DTC, CALI, DRHO |
| Optional curves | PEF, RSHA, RXO, SP, ROP |
| Classes | 11 lithologies (FORCE 2020 codes) |
| Test accuracy | 0.694 (majority baseline 0.626) |
| Weighted F1 | 0.679 |
| Macro F1 | 0.402 |
| Held-out set | 17 wells, ~220k rows |

The gap between weighted F1 (0.679) and macro F1 (0.402) is the honest headline:
the model is good at the common rocks and blind to the rare ones.

**Reliable:** Shale, Sandstone, Limestone, Halite.
**Not reliable — test recall on held-out wells:** Chalk 0.000, Dolomite 0.003,
Tuff 0.032, Marl 0.064.

That blindness is a product constraint, not a footnote. The absence of Chalk
from a result is a fact about the model, never about the well, and §E enforces
that the agent says so.

`check_distribution` compares an upload against the training curve statistics
and **refuses** wells that do not resemble the Norwegian Continental Shelf,
rather than returning a confident guess for a basin the model has never seen.

Pipeline for one upload:

```
upload -> LAS/CSV parse -> curve validation -> out-of-distribution check
       -> per-depth prediction -> merged lithology intervals -> summary
```

## C. The agent graph

`app/agent/graph.py` is a hand-rolled state machine in LangGraph's shape — typed
state, named `*_node` functions, an explicit router — with no framework
dependency. One `GeoMindState` per request carries inputs, tool results, the
trace, and the bookkeeping the guards need.

```
route_node -> [lithology_node] -> retrieve_node -> generate_node -> guard_node
```

- **`route_node`** — deterministic. Whether a file was uploaded is a fact the
  backend already has; asking a model to infer it would be strictly worse. With
  no new file it restores the session's cached summary, intervals and curves.
- **`lithology_node`** — runs the XGBoost path. A rejected upload (missing
  curves, unsupported format) is a normal outcome that produces an explanation,
  not a 500.
- **`retrieve_node`** — geology RAG, skipped for equation questions (§D). Never
  raises: a retrieval failure degrades to the pre-RAG answer.
- **`generate_node`** — assembles the system prompt from composable rule blocks
  and calls Claude. Rules are injected only when they apply; applying lithology
  rules to a general geology question made the model hedge on everything, and
  applying citation rules to a turn with no sources made it invent citations.
- **`guard_node`** — appends corrections (§E).

### Tool invocation: two different decisions

| Tool | Who decides | Why |
|---|---|---|
| Lithology (XGBoost) | The **backend**, deterministically | The presence of an upload is known. No inference needed. |
| `compute_porosity` | The **model** | "Compute porosity for my well" and "explain porosity" are one word apart, and only the model can tell them apart. |

`compute_porosity` is offered only when there are intervals to compute over
*and* a log to read — otherwise the tool would have nothing to work with.

### The porosity tool

Density porosity from RHOB, with matrix density selected per predicted
lithology zone:

$$\phi_D = \frac{\rho_{ma} - \rho_b}{\rho_{ma} - \rho_f}$$

It is deliberately loud about why a number might be wrong. Each zone carries
caveats for clay-bound water in shale, an unreliable lithology call, low
lithology confidence, and a physically implausible result reported rather than
clamped — a clamped 0.0% reads as a confident answer and hides the diagnostic.

**Washout detection** is the one that earns its keep. An enlarged hole puts mud
between the density pad and the formation; RHOB reads low and porosity reads
high, which is exactly how a washed sand fakes a spectacular reservoir. On the
25/5-1 sample well this catches the 694–926 m sand reporting 47.5% porosity:
78% of the zone washed, ~5 in over gauge, RHOB at 1.97 g/cc. Bit size is
normally absent from these LAS files, so in-gauge diameter is estimated per
zone as the 5th percentile of CALI, and the caveat states the measured excess
rather than certifying a good hole. No caliper produces no claim at all, rather
than an implied clean hole.

### Session state

`POST /predict` writes the upload to a temp file and deletes it in a `finally`,
so a follow-up "now compute porosity" turn has no file. Depth, RHOB and CALI
are therefore read **while the file still exists** and cached on the session as
`WellCurves` (float32, ~170 KB per well) alongside the intervals. The porosity
tool prefers cached curves over a path.

## D. The RAG, and the Equation Bypass Hack

The corpus is petroleum geology books, papers and well-log articles: 11,809
chunks in Qdrant Cloud, embedded with BAAI/bge-large-en-v1.5 at 1024
dimensions. Query embeddings are an HTTP call to a feature-extraction endpoint,
so the serving image needs no torch. Retrieval over-fetches and de-duplicates on
a normalised text prefix, because ~14% of the corpus is near-duplicate chunks
from two OCR passes of the same page.

RAG was switched off for a while, because retrieved passages were making
answers *worse*. The diagnosis turned out to be specific rather than general:

**The books are scanned print from before LaTeX.** Their prose survived OCR
intact. Their equations did not — they arrive as symbol soup, and chunking split
what survived. And because `RETRIEVAL_RULES` correctly tell the model to prefer
the passages over its own recall, asking for Archie's equation got back mangled
characters copied faithfully from a damaged source. The corpus was actively
worse than the model's own knowledge for exactly one class of question.

So the fix is routing, not a rewrite:

```python
if is_formula_request(question):
    state.note("retrieve=skipped (equation request)")
    return state          # the corpus is never queried
```

`is_formula_request` fires on equation wording (*equation, formula, derivation,
solve for, cementation exponent*) and on equations named after people — Archie,
Wyllie, Timur, Larionov, Simandoux, Waxman-Smits, Darcy, Kozeny-Carman. Those
arrive as bare names carrying none of the trigger words, and they are precisely
what the corpus answers worst.

A question naming the user's own well is **never** a formula request, even when
it says "calculate" — "calculate the porosity of my well" must stay on the
porosity tool.

On a bypassed turn `MATH_RULES` replaces the retrieval rules: answer from your
own training, write LaTeX (`$inline$` / `$$display$$`), define every symbol with
units, name the assumptions (Archie assumes a clean water-wet formation), and
**cite nothing** — a `[n]` refers to a retrieved passage and there are none this
turn. The frontend renders it through `remark-math` + `rehype-katex`, so the
user gets typeset mathematics instead of OCR debris.

Everything else — depositional environments, traps, source rock maturity, rock
properties — still goes to the corpus and comes back with cited passages, which
is the part the books are genuinely good at.

The remaining corpus defects are real and unfixed: `section_title` concatenates
every heading on a page, and the near-duplicate rate is high. The proper fix is
re-ingestion with better PDF extraction, a text-quality floor and dedup at write
time — not more retrieval code.

## E. Output guards

Prompt wording alone did not hold. Measured against the fine-tune with an
identical prediction, the model claimed a blind-spot lithology was absent in
**3 of 3 runs**, and once fabricated "60.0% total gas saturation, 32.0% water
saturation, 23.8 API and 17.0 porosity" from a log containing none of those
quantities.

Three guards run on every answer. None of them rewrite the model's words — each
appends a correction, so the user sees both what was said and why it is wrong.

| Guard | Catches |
|---|---|
| `find_blind_spot_claims` | "No dolomite is present" — absence of a class with ~0 recall is a model limitation, not a finding |
| `find_unsupported_quantities` | Numeric claims about porosity, permeability, saturation, API gravity, net pay — the model is sent lithology, depth and confidence only, so these are fabricated by construction |
| `find_unsupported_confidence` | Confidence figures that appear in no source the model was actually shown |

Each has a deliberate exemption, and each exemption exists because the guard was
wrong without it:

- Sentences describing the *model's* limits ("the model cannot detect Chalk")
  are skipped — that sentence is what the system prompt asks for, and correcting
  it had the assistant arguing with itself.
- `[n]`-cited sentences are exempt when RAG context is present: with passages in
  the prompt, a porosity range can be legitimately sourced.
- Quantities a tool actually measured this turn are exempt. Without this the
  agent printed its own porosity table and then appended "the lithology model
  has no porosity data".
- Confidence values are checked against every tool output, not just the
  lithology summary — the porosity tool quoting its own 0.7 threshold was
  flagged as invented before that.
- Formula requests skip the quantity check entirely: a worked example uses
  illustrative numbers, not claims about the well.

## F. Backend and frontend

**Backend** — FastAPI.

| Endpoint | Purpose |
|---|---|
| `POST /predict` | Upload a log, get intervals + curves + distribution check |
| `POST /chat` | One agent turn, with session well context |
| `GET /chat/session/{id}` | Session state |
| `GET /model/info` | Model card: version, classes, curve contract, metrics |
| `GET /wells/samples` | Held-out sample wells |
| `GET /wells/samples/{id}/analyze` | Analyse a sample well |
| `GET /oil-prices` | Market data |
| `GET /health`, `GET /ready` | Liveness and model readiness |

**Frontend** — Vite + React 18 + TypeScript + Tailwind, a fixed three-column
"cyberpunk HUD" console: well log input | geologist assistant | log plot. State
is a single Zustand store. There are no browser-side mocks — every number comes
from the backend. `WellLogChart` renders up to five tracks (GR, RDEP, RHOB,
NPHI, DTC), laid out from the well's actual curves and breaking the polyline on
data gaps. The two sample buttons load **held-out test wells** (25/5-1
sandstone, 17/11-1 shale/evaporite), so the demo shows generalization rather
than memorised training data.

## G. Running it

```bash
# Backend  (port 8006)
python -m venv geologs
./geologs/bin/pip install -r requirements.txt
./geologs/bin/python -m uvicorn app.main:app --reload --port 8006 --host 0.0.0.0

# Frontend
cd frontend && npm install && npm run dev
```

`requirements.txt` installs the lithology model from the local wheel, which pins
xgboost 3.1.2, scikit-learn 1.8.0 and pandas <3.0 to match the artifact. No
torch, no transformers — the LLM and the embedder are both HTTP calls.

## H. Tests and CI

```bash
./geologs/bin/python -m pytest -q     # 41 tests
cd frontend && npm run lint && npm run build
```

41 pytest tests cover the guards, the porosity maths and its caveats, the
equation-bypass routing, and curve validation. Every one is pure logic with the
network monkeypatched, so the suite needs no API keys and runs in under a
second. GitHub Actions (`.github/workflows/main.yml`) runs backend tests and
frontend lint + build on every push to `master` and every PR targeting it.

---

# Part II — The Qwen2.5-7B fine-tune

**Status: published, and no longer in the live path.** The sections below are
the original engineering log of the QLoRA fine-tune — data pipeline, filtering
rounds, throughput benchmarking, hyperparameters, evaluation and deployment.
They are kept in full because the decisions in `ETL/` and `training/` were made
empirically and are justified here.

What it is: a QLoRA fine-tune of Qwen2.5-7B-Instruct on ~10k geology Q/A pairs,
published in 4-bit (bitsandbytes nf4) and running as a public Gradio chat demo
on a Hugging Face **T4 Space** (16GB VRAM). `llm/hf_client.py` and
`llm/prompt_builder.py` still exist in this repo and still work; they are
dormant.

Why the backend moved to Claude Sonnet 5: the evaluation found the
fine-tune reproduces expert register and reasoning structure reliably while
stating specific numeric facts wrong with high confidence — inverted kerogen
H/C–O/C ratios, temperature confused with burial depth, a fabricated transition
temperature. Agent work also needs tool-calling, and fine-tuning on Q/A at
`max_seq_length=1024` frequently degrades exactly that. The guards in §E were
built against this model's measured failures, and they still run on the Claude
path — `find_unsupported_quantities` in particular stays correct by
construction, since no model can source those numbers from what it is sent.
Hence I  need a strong LLM  to answer  inner sciences Petroleum Geology questions, 
My 7B Qwen2.5 was not good enough to carry on this critical task therefore I switch to
Claude-Sonnet-5 by Anthropic API  Key,  this LLM  has strong background in Geology wired
to my own Vector Knowledge it generates reliable  answers on petroleum geology field sciences.

## 1. Data pipeline (ETL)

### 1.1 Source datasets

| Source | Raw rows | License | Notes |
|---|---|---|---|
| `daven3/geosignal` (K2 paper corpus) | 39,749 | Apache-2.0 | Mixed geoscience + generic instruction filler |
| Original curated general geology Q/A | 818 | — | Authored for this project |
| Original curated petroleum geology Q/A | 125 | — | Sedimentology, stratigraphy, well logging, seismic |
| Held-out test set | 60 | — | Disjoint from training data |

`geosignal` was evaluated first against two alternative HF datasets
(`GeoGPT-Research-Project/GeoGPT-QA`, `GeoGPT-CoT-QA`). Both were rejected:
inspection showed the majority of their rows sourced from *IOP Conference
Series: Earth and Environmental Science*, a broad environmental-science
venue, with most content unrelated to geology (agriculture, air quality,
wastewater treatment, urban ecology). `geosignal` was selected instead
because its `type` and `category` columns allow direct, verifiable
filtering down to genuine geoscience content.

### 1.2 Filtering rounds applied to `geosignal`

Five rounds of quality filtering were applied, each verified empirically
against sampled output rather than assumed:

1. **Type filtering** — kept only `type ∈ {geo, geoqa, self}`, discarding
   `dolly`, `alpaca-gpt4`, `NI`, and `arc` (generic instruction-tuning
   filler; `arc` rows were confirmed to be answer-only multiple-choice
   letters with no usable question context).
2. **Category filtering** — removed `gso.wikipedia.*` and `gso.wordnet.*`
   entries (generic NER training data with no geological content).
3. **Pattern-based noise removal** — removed rows matching a "related
   paper" instruction pattern (bibliography list outputs from
   `metaearth.rruff.qa`, some exceeding 19,000 characters of citation
   text) and a broken template artifact (`"is/means that <number>"`,
   a generation bug in the source data).
4. **Placeholder removal** — removed rows where the entire answer was a
   database placeholder (`"No Corresponding Information"`), which taught
   nothing but non-answers.
5. **Length-based outlier removal** — dropped rows exceeding the
   empirical 99th percentile of token length. Manual inspection of the
   dropped rows confirmed they were predominantly named-entity-recognition
   tasks over full paper abstracts (`gakg.abstract.ner`), plus a small
   amount of off-domain noise (a corporate finance NPV problem, forum
   posts unrelated to geology).

Result: 39,749 → 18,054 rows of verified geoscience content.

### 1.3 Merging and class balancing

The cleaned `geosignal` subset was merged with the two original curated
datasets. Because the curated sets (818 + 125 rows) represented only
4.3% of the combined pool, they were oversampled ×5 within the training
split only (never in validation, to avoid inflating held-out metrics).
Cross-source deduplication was applied before oversampling so that
oversampling amplified genuinely unique content rather than duplicates.

Final corpus: **21,639 training rows / 940 validation rows**, after a
final token-length filter (see §2.1).

All merge and filtering steps included explicit checks for train/validation
leakage at every stage.

### 1.4 Data integrity incident

During dataset assembly, an append operation performed directly against a
Google Drive-mounted path produced 4 malformed JSON lines when read back
immediately after the write. Root-cause analysis confirmed this was a
FUSE eventual-consistency artifact, not data corruption — a subsequent
read of the same file returned 100% valid JSON. This reinforced a
project-wide rule: **all data and training I/O happens on local disk;
Google Drive is used only for one-time transfers at the start and end of
a session.**

---

## 2. Tokenization and sequence length

Rather than estimating `max_seq_length` from raw character counts, the
full corpus was rendered through Qwen2.5-7B-Instruct's actual chat
template and tokenized, then measured empirically:

| Percentile | Tokens |
|---|---|
| p50 | 162 |
| p90 | 361 |
| p99 | 640 |
| p99.9 | 1,074 |

**`max_seq_length = 1024`** was selected (99.85% coverage). The 33 rows
(0.15%) exceeding this threshold were dropped rather than truncated, to
avoid teaching the model to end responses mid-sentence. Manual inspection
confirmed the dropped rows were low-value (NER-over-abstract tasks,
off-domain finance/forum content).

---

## 3. Training configuration

### 3.1 Throughput benchmarking

Before committing GPU credits to a full run, a dedicated benchmark swept
multiple `(batch_size, gradient_accumulation)` configurations, measuring
**examples/second** (not steps/second — step-based throughput is not
comparable across differing gradient accumulation settings) with save and
eval disabled.

| batch | grad_accum | eff. batch | examples/s | VRAM |
|---|---|---|---|---|
| 8 | 2 | 16 | 15.1 | 14% |
| 16 | 1 | 16 | 13.1 | 14% |
| 16 | 2 | 32 | 13.2 | 15% |
| 24 | 1 | 24 | 11.3 | 14% |
| 32 | 1 | 32 | 11.0 | 17% |
| **8** | **4** | **32** | **15.1** | **14%** |

`batch=8, grad_accum=4` (effective batch 32) was selected: highest
throughput, and VRAM usage far below the ceiling where gradient
offloading would degrade speed. Hardware: RTX PRO 6000 Blackwell (95GB),
Colab.

### 3.2 Hyperparameters

| Parameter | Value |
|---|---|
| Base model | Qwen2.5-7B-Instruct |
| Method | QLoRA, 4-bit |
| LoRA rank / alpha | 16 / 16 |
| Target modules | q/k/v/o_proj, gate/up/down_proj |
| Effective batch size | 32 (8 × 4) |
| Epochs | 3 |
| Learning rate | 2e-4, cosine schedule |
| max_seq_length | 1024 |
| eval_steps / save_steps | 250 |
| Early stopping | patience 3 on eval_loss |

### 3.3 Infrastructure practices

All training I/O followed lessons from a prior fine-tuning post-mortem:

- Datasets staged to local disk before training; never read from or
  written to Google Drive during the run.
- Checkpoints saved locally; the best model copied to Drive once, at the
  end.
- Validation subsampled per-eval (dynamic random resampling each
  evaluation, not a single fixed subset) to reduce overfitting risk to a
  static validation slice while keeping eval cost low.

Training wall clock: **40 minutes** (~6 credits on the training
infrastructure used).

---

## 4. Evaluation

### 4.1 Loss curves

| Step | Train loss | Val loss |
|---|---|---|
| 250 | 1.559 | 1.605 |
| 500 | 1.420 | 1.574 |
| 750 | 1.231 | 1.566 |
| 1000 | 1.141 | 1.563 |
| 1250 | 1.140 | **1.560** (best) |
| 1500 | 1.012 | 1.576 |
| 1750 | 1.053 | 1.574 |
| 2000 | 1.066 | 1.574 |

`load_best_model_at_end` restored the step-1250 checkpoint, before
validation loss began to plateau and drift upward (mild overfitting onset
past that point).

**A note on interpreting these numbers:** a validation loss around 1.5-1.6
is not, by itself, evidence of a weak model. Much of this dataset consists
of open-ended explanatory answers where multiple correct phrasings exist
(e.g., "faults glide over the asthenosphere" vs. "plates move and interact")
— token-level loss penalizes the model for not predicting the exact
reference wording even when its own answer is equally correct. This creates
an irreducible loss floor that is a property of the dataset, not a
reliable measure of the model's geological competence. Test-set
perplexity (6.12) and direct inspection of generated answers were used
instead of loss magnitude to judge output quality.

### 4.2 Qualitative evaluation (60-question held-out test set)

Generated answers were manually reviewed against reference answers across
general geology, petroleum systems, sequence stratigraphy, and well
logging. Findings:

**Strengths:**
- Correct, well-structured answers on sequence stratigraphy, basin
  classification, structural vs. stratigraphic traps, primary/secondary
  migration, accommodation space, and well-log interpretation
  (gamma ray, resistivity, sonic, caliper/mud log).
- Correct domain terminology used naturally (e.g., "listric, syn-rift
  normal faults," "capillary entry pressure," "disequilibrium
  compaction").
- No fabricated formation names or fictitious citations observed.

**Weaknesses (factual errors under expert review):**
- Kerogen type classification: H/C and O/C ratio relationships were
  inverted for Type I and Type III kerogen in one generation.
- One instance of confusing source-rock maturation temperature (°C) with
  burial depth, stating "60–120 km" instead of temperature.
- One fabricated specific numeric claim regarding a halite ductile-brittle
  transition temperature.

**Conclusion:** the model reliably reproduces the *register and reasoning
structure* of an expert geologist, but can state specific numeric facts
incorrectly with high confidence. This is the expected failure mode of an
SFT-only domain model and is the motivating reason for a planned
retrieval-augmented (RAG) follow-up, rather than a hyperparameter
adjustment — the errors are factual gaps, not undertraining.

---

## 5. Deployment

### 5.1 Model publication

The merged fp16 model was published to the Hub, followed by a 4-bit
(`bitsandbytes`, nf4, double quantization) version to support inference on
lower-VRAM hardware.

### 5.2 Gradio Space

A public chat demo runs the 4-bit model on a T4 GPU (16GB VRAM). The
fp16 merged model (~14-15GB weights) left insufficient headroom for KV
cache and activations on a T4, causing multi-minute latency and hangs on
subsequent turns. Switching to the 4-bit checkpoint (~4-5GB weights)
resolved this.

Additional runtime constraints applied for T4 stability:
- Conversation history capped to the last 3 turns (unbounded history
  growth was increasing both memory pressure and generation latency turn
  over turn).
- `max_new_tokens` reduced from 512 to 192.
- Chat history parsing updated for Gradio 6.x's dict-based message format
  (`{"role": ..., "content": ...}`), replacing the legacy tuple format.

The Space includes an explicit research-preview disclaimer describing the
SFT-without-RAG status and known limitations, and a system prompt
instructing the model to express uncertainty on unverified numeric claims
rather than guess.

---

# Part III — Next steps

- **MCP integration** (`app/mcp/`) — external petroleum and geoscience data
  sources as model-callable tools. The stubs are wired points, not progress.
- **Corpus re-ingestion** — better PDF extraction, a text-quality floor and
  dedup at write time, so the RAG can eventually serve equations instead of
  being routed around for them.
- **Port the graph to LangGraph** — worth it once MCP creates branches the model
  must choose between. Today there is one real branch, so the framework would
  add dependency weight and no capability.

- **Add Numerica Gaskell Equation Solver 2D**: new agent tool to  model oil flow in a wet rock in 2D.  "Still working on this feature."

---

## Repository links

| Artifact | Link |
|---|---|
| Dataset (LLM) | https://huggingface.co/datasets/beaunix/geo-mind-qa |
| Model, 4-bit (LLM) | https://huggingface.co/beaunix/aegis-geo-mind-qwen2.5-7b-bnb-4bit |
| Space, demo (LLM) | https://huggingface.co/spaces/beaunix/aegis-geo-mind-demo |

## License

MIT (model, dataset, and code in this repository).

## Disclaimer

Petrologix is an academic and educational research preview. It is not validated
for operational geological, exploration, or drilling decisions.

The lithology model was trained only on the Norwegian Continental Shelf and does
not reliably detect Chalk, Dolomite, Tuff or Marl. Porosity is a density-derived
estimate carrying the caveats it reports, not a core measurement. Numeric and
factual claims from the language model should be independently verified against and tell thruth.
