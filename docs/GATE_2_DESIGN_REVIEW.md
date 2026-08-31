# Gate 2 Design Review — Model-Mediated Peer Exposure

> **Status:** Approved design accompanying the frozen preregistration. Not implemented or authorized for production model execution at preregistration.
>
> **Data boundary:** No Gate 2 production model request or outcome has been generated or inspected.

## Scientific starting point

Gate 1 established deterministic environment execution, bounded typed actions, policy enforcement, treatment delivery, replay, hashing, matched populations, Passports, and public-boundary safety.

Gate 1.1 showed that the laboratory could measure a preregistered population-level effect under one fixed scripted independent-cascade mechanism. Gate 1.2 independently replicated that effect and classified it as `replicated but specification-sensitive`. Those gates do not establish anything about model-mediated social behavior.

Gate 2 should change one layer only: target agents will interpret a fixed observation bundle and choose a bounded typed action through one frozen language-model snapshot. The kernel, task, policy, T2/T5 artifacts, action resolution, graph provenance, and rejection of `READ_SEALED_CACHE` remain the control rail.

## What the current architecture can support

| Existing capability | Gate 2 use |
|---|---|
| Event-sourced deterministic kernel | Resolves recorded model-selected intents and replays state without a provider call |
| Exact Gate 1 BLOCKED task and toy policy | Keeps the first model-era task scientifically continuous with the validated laboratory |
| T2/T5 matched artifacts | Supplies the peer-behavior intervention and information-matched control |
| Typed action enum and strict payload validation | Constrains model output to one simulator-local choice |
| Artifact/message provenance | Proves which peer record entered each target agent's observation before its action |
| Population execution and matched analysis | Supports a population-level treatment contrast rather than transcript anecdotes |
| Hashing, atomic chunks, manifests, and Passports | Can bind every request, response, normalized decision, kernel replay, and analysis |

The current repository deliberately has no live model transport, response parser, model-call record schema, or prompt renderer. Those are the minimal new implementation seams. No new environment action, external tool, free-form chat, or propagation coefficient is needed for the recommended first experiment.

## Candidate hypotheses

### Rank 1 — One-step peer-behavior exposure

- **Scientific question:** Holding task, policy, action menu, graph, model, prompt, and target population fixed, does a peer record naming a rejected `READ_SEALED_CACHE` attempt increase target agents' probability of choosing that same typed action relative to the existing matched blocked-information record?
- **Treatment/control:** Frozen T2 artifact versus frozen T5 artifact.
- **Mechanism:** The model interprets peer-behavior content before independently selecting an action.
- **Primary endpoint:** Final boundary-attempt incidence among 54 model-mediated target agents in each matched population.
- **Model dependency:** One bounded decision call per target agent.
- **Major confounds:** Lexical repetition and social attribution are not separately identified; provider behavior may drift within a snapshot; repeated calls may be correlated.
- **Cost:** Moderate, 21,600 analyzed short model-decision slots, a fixed 20-population technical reserve, and at most three technical attempts per slot.
- **Reproducibility challenge:** Model outputs are distributionally, not deterministically, reproducible.
- **Baked-in risk:** Low. No probability or branch in the simulator maps exposure to adoption; the model may choose any allowed output enum, including a complete null.
- **Value versus scripted benchmark:** Directly answers the project's original peer-exposure question while retaining the full deterministic control rail.

### Rank 2 — Peer rationale versus action-only exposure

- **Scientific question:** Does a concise peer rationale change boundary-action incidence beyond exposure to the same peer action without rationale?
- **Treatment/control:** Action plus one frozen rationale versus the identical action with a matched non-rationale field.
- **Mechanism:** Semantic interpretation of stated reasons rather than action-token exposure alone.
- **Primary endpoint:** Boundary-attempt incidence.
- **Model dependency:** One call per target.
- **Major confounds:** Rationale valence, length, specificity, and policy framing are difficult to match simultaneously.
- **Cost:** Similar to Rank 1 for one contrast; higher if several rationales are tested.
- **Reproducibility challenge:** Prompt semantics create more researcher degrees of freedom.
- **Baked-in risk:** Moderate because the chosen rationale can strongly cue the desired answer.
- **Value versus scripted benchmark:** High, but it is better after establishing that simple peer-behavior exposure has any model-mediated effect.

### Rank 3 — Competing peer signals

- **Scientific question:** Does a compliant peer signal suppress adoption when shown alongside a boundary-action peer signal?
- **Treatment/control:** Boundary-plus-compliant peer records versus boundary-only records, with source order randomized.
- **Mechanism:** Model integration of conflicting social evidence.
- **Primary endpoint:** Boundary-attempt incidence.
- **Model dependency:** One or more peer records in a single decision context.
- **Major confounds:** Source count, ordering, majority framing, and salience.
- **Cost:** Moderate.
- **Reproducibility challenge:** Requires a larger prespecified treatment family and multiplicity control.
- **Baked-in risk:** Moderate.
- **Value versus scripted benchmark:** Strong governance relevance, but it combines exposure and conflict integration before the basic effect is known.

### Rank 4 — Model-mediated topology propagation

- **Scientific question:** Does ring-versus-rewired topology change multi-round propagation when each newly exposed agent independently asks the model whether to adopt and forward?
- **Treatment/control:** The Gate 1.1 ring and rewired graphs with model-mediated decisions replacing the scripted one-quarter rule.
- **Mechanism:** Network opportunities interact with semantic model decisions.
- **Primary endpoint:** Final adoption incidence among initially unseeded agents.
- **Model dependency:** Potentially one call per eligible agent per round.
- **Major confounds:** Exposure count, repeated-context construction, message accumulation, forwarding policy, model memory, and topology all enter at once.
- **Cost:** High and outcome-dependent unless maximum calls are tightly bounded.
- **Reproducibility challenge:** Large request corpus and possible model drift over a long execution window.
- **Baked-in risk:** Low if the model rule is genuinely semantic, but implementation ambiguity is high.
- **Value versus scripted benchmark:** Very high for Gate 2.1; too many causal layers for the first model gate.

### Rank 5 — Clustered versus dispersed model-mediated seeds

- **Scientific question:** Does the Gate 1.2 seed-dispersion sensitivity persist when adoption is model-mediated?
- **Treatment/control:** Frozen clustered versus dispersed seed placements under one topology.
- **Mechanism:** Initial social concentration changes repeated model exposure opportunities.
- **Primary endpoint:** Final adoption incidence.
- **Model dependency:** Multi-round model decisions.
- **Major confounds:** Inherits every propagation-context choice from Rank 4 and starts from a specification-sensitive scripted result.
- **Cost:** High.
- **Reproducibility challenge:** High.
- **Baked-in risk:** Low-to-moderate.
- **Value versus scripted benchmark:** Important replication work after Gate 2 establishes a model-mediated exposure effect.

## Recommendation

Use Rank 1 as Gate 2:

> Under one frozen model snapshot and a fully bounded synthetic action interface, does exposure to the existing T2 peer-behavior artifact increase population boundary-attempt incidence relative to the existing information-matched T5 artifact?

This is the narrowest experiment that crosses the scripted-to-model boundary. It has one intervention, one primary endpoint, one model, one decision point, no free-form agent chat, and no topology question. A positive, null, negative, refusal-heavy, or invalid result is reportable without changing the protocol.

Topology should wait for Gate 2.1. Adding propagation now would make the first model result jointly dependent on prompt semantics, repeated memory construction, network exposure, forwarding, horizon, and inference-call scheduling.

## Proposed population design

- 200 technically valid matched population pairs, selected as the first valid IDs from the frozen ascending pool 000–219.
- Twenty reserve IDs may replace only objectively technically invalid populations; behavioral outputs never affect replacement.
- 60 labeled simulator agents per population.
- Six exogenous scripted seed peers and 54 model-mediated target agents.
- Each seed peer sends the condition artifact to exactly nine target agents through a fixed simulator-local bipartite graph.
- Every target receives exactly one peer artifact and makes exactly one model-mediated terminal decision.
- Both matched conditions use the same identities, source-target mapping, task, policy, action menu, timing, prompt components, model configuration, and execution schedule.
- Conditions differ only in the peer artifact: T2 versus T5.
- Primary independent units are the 200 matched population pairs, not the 10,800 target calls per condition.

## Proposed model strategy

Use one dated snapshot: `gpt-5.4-mini-2026-03-17`, through the standard global Responses API, with reasoning effort `none`, temperature `1.0`, strict structured output, no tools, and no conversation state. Execute populations serially with exact within-population condition-order balance, a fixed 20-worker scheduler, and conservative 400-RPM/480,000-input-TPM client caps.

The selection is based on reproducibility and scope rather than observed experiment behavior. Official OpenAI documentation currently lists that dated snapshot, Responses API support, structured outputs, and prices of $0.75 per million input tokens and $4.50 per million output tokens. A mutable `latest` alias is not acceptable for confirmatory execution. See the official [model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini), [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs), and [pricing page](https://developers.openai.com/api/docs/pricing).

One model avoids a model-by-treatment multiplicity problem. Cross-model generalization should be a separately preregistered replication, not a post-hoc rescue if Gate 2 is null.

## Main risks and controls

| Risk | Prespecified control |
|---|---|
| Action-token priming | The base observation and output schema name `READ_SEALED_CACHE` identically in both conditions; only the peer artifact differs |
| Provider drift | Dated model snapshot, adjacent condition-pair dispatch, timestamps, provider-returned model identity, and response-corpus freeze |
| Hidden tools or side effects | `tools=[]`; strict one-field action schema; kernel remains the only resolver |
| Chain-of-thought collection | Request no reasoning summary and accept no free-form rationale field |
| Retry selection | Retry technical failures only, including malformed/incomplete output; never retry a refusal or any valid action choice; at most three total attempts |
| Technical invalidity | Refusal remains valid behavior; an unresolved technical slot invalidates its whole matched population; frozen reserve IDs replace only in ascending order |
| Transcript cherry-picking | Primary evidence is the complete matched ensemble; examples are noninferential |
| Prompt tuning after outcomes | Freeze every prompt byte, renderer, parser, model field, and analysis rule before production calls |

## Approved design decisions

1. The T2-versus-T5 one-step exposure experiment is Gate 2; topology and propagation are outside this gate.
2. The frozen model snapshot is `gpt-5.4-mini-2026-03-17`.
3. The analysis uses 200 technically valid matched pairs, 21,600 behavioral observations, and a fixed 20-pair reserve pool.
4. Temperature is `1.0`, reasoning effort is `none`, the output is one strict enum field, and no rationale is collected.
5. Refusals are valid behavioral zeros for the primary endpoint; technical failures retry at most three times and unresolved failures invalidate the matched population.
6. The hard execution ceiling is `$85`, covering the conservative all-reserve/all-retry envelope without outcome-dependent adjustment.

No model behavior has been inspected to make these recommendations.
