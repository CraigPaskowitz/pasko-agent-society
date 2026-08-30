# Incident Mapping & Scientific Review

## Public-evidence boundary

The 2026 OpenAI / Hugging Face incident motivates the research program but does not provide a clean randomized causal experiment.

Public reporting supports high-level observations including unsanctioned inter-agent communication, persistence on difficult or impossible tasks, large collaborative workstreams, strategy sharing, rapid participation changes after shared discoveries, emerging coordination conventions, and difficult retrospective attribution.

Pasko Agent Society studies safer and narrower controlled analogues.

## Incident mapping

| Observed public phenomenon | Controlled research question | Safe synthetic analogue | Measurement |
|---|---|---|---|
| unintended inter-agent communication | Does communication availability alter strategy adoption? | simulator-local BOARD vs isolation | adoption treatment effect |
| strategy/discovery sharing | Does boundary-strategy exposure increase attempts? | pre-authored toy strategy artifact | T2-T5 incidence |
| difficult/impossible tasks | Does task blockage alter compliance? | SOLVABLE vs BLOCKED task | interaction effect |
| rapid participation changes | Can seeded strategies diffuse? | synthetic graph + seed fraction | adoption curves/T10/T25/T50 |
| coordination conventions/workstreams | Can stable coordination conventions emerge? | later repeated-group toy task | convention persistence/success |
| coordinator emergence | Does graph position/information endowment concentrate influence? | controlled centrality and seed information | lineage concentration |
| reset adaptation | Can coordination artifacts re-form after synthetic resets? | deletion of toy working state | post-reset reuse |
| shared goals/activities | Does peer exposure change strategy/task allocation? | toy collaboration proposal | matched strategy choice |
| incomplete/spoofed records | How robust is attribution to missing observations? | analysis-only masked synthetic logs | attribution error |
| monitoring/policy gaps | Do explicit policy labels or safe exits change action incidence? | T3/T4 | mitigation effects |

None recreates operational incident techniques.

## Review synthesis

### Multi-agent systems researcher
- Objection: pre-authored artifacts may measure priming, not emergence.
- Confounder: semantic content differences.
- False positive: repeated independent prompt sensitivity called population behavior.
- Safety concern: jumping too quickly to open coordination.
- Reproducibility risk: stochastic outputs.
- Falsification: T2 vs information-matched T5, then propagation.
- Simplification: controlled exposure first.

### AI alignment researcher
- Objection: boundary crossing can be anthropomorphized as misalignment.
- Confounder: policy ambiguity.
- False positive: instruction interpretation, not peer adoption.
- Safety concern: optimizing prompts for violations.
- Reproducibility risk: system-instruction drift.
- Falsification: explicit-policy treatment and comprehension fixtures.
- Simplification: trivial toy prohibited action that never succeeds.

### LLM evaluation researcher
- Objection: model/provider drift can dominate.
- Confounder: retries/parser behavior.
- False positive: model snapshot change.
- Safety concern: unnecessary reasoning capture.
- Reproducibility risk: nondeterministic inference.
- Falsification: fresh-call replication with complete provenance.
- Simplification: scripted baseline + one bounded adapter at most.

### Network scientist
- Objection: topology changes exposure opportunity mechanically.
- Confounder: degree distribution.
- False positive: more edges mistaken for stronger contagion.
- Safety concern: communication containment.
- Reproducibility risk: graph seeds/delivery ordering.
- Falsification: exposure-matched/degree-controlled comparisons.
- Simplification: topology is Phase 2, not primary Gate 1.

### Statistician
- Objection: many metrics/conditions create researcher degrees of freedom.
- Confounder: task pressure.
- False positive: T2-T0 differs because T2 reveals blockage.
- Safety concern: tuning until contagion appears.
- Reproducibility risk: optional stopping.
- Falsification: preregister T2-T5 and one primary outcome.
- Simplification: first boundary-attempt incidence is primary.

### Experimental-design researcher
- Objection: peer-generated messages make treatment uncontrolled.
- Confounder: message persuasiveness.
- False positive: treatment simply contains better information.
- Safety concern: generated messages drift toward operational content.
- Reproducibility risk: free-text non-equivalence.
- Falsification: pre-authored matched artifacts.
- Simplification: no free-form messaging in Phase 1.

### Cybersecurity / safety researcher
- Objection: incident-inspired work could become a bypass benchmark.
- Confounder: realistic security affordances.
- False positive: capability derives from tools rather than social behavior.
- Safety concern: operational transfer.
- Reproducibility risk: host/network state.
- Falsification: runtime/static proof of no external I/O.
- Simplification: in-memory enum boundary only.

### Distributed-systems researcher
- Objection: races/order can manufacture collective effects.
- Confounder: scheduler ordering.
- False positive: same-round leakage.
- Safety concern: persistent services unnecessary.
- Reproducibility risk: concurrency.
- Falsification: synchronous rounds and replay equality.
- Simplification: deterministic delivery schedule.

### Simulation scientist
- Objection: toy world may become tautological.
- Confounder: scripted probability directly encodes effect.
- False positive: scripted baseline treated as evidence about LLMs.
- Safety concern: low.
- Reproducibility risk: mixing infrastructure and substantive inference.
- Falsification: scripted baseline validates plumbing only.
- Simplification: substantive agent claims require model cohorts.

### Skeptical replication researcher
- Objection: provider output may not be independently reproducible.
- Confounder: unavailable snapshots.
- False positive: cherry-picked trajectory anecdotes.
- Safety concern: raw transcripts can contain unwanted material.
- Reproducibility risk: service drift.
- Falsification: manifests/hashes/aggregate data + fresh ensemble replication.
- Simplification: no chain-of-thought dependence.

## Revisions adopted

1. Primary Gate 1 uses controlled pre-authored exposure, not open chat.
2. T2 vs matched-information T5 is the primary causal comparison.
3. Scripted agents validate infrastructure but do not establish LLM findings.
4. Topology begins only in Phase 2.
5. The prohibited action has no real-world execution path.
6. Model reproducibility is statistical; environment replay is deterministic.
