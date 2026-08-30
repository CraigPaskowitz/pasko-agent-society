# Pasko Agent Society

**Pasko Agent Society** is an open experimental laboratory for reproducible research on emergent behavior, coordination, influence, information propagation, norm formation, and control in populations of AI agents.

It is a sibling research project to Pasko Republic, not a pivot of it.

- **Pasko Republic** studies computational human and societal behavior.
- **Pasko Agent Society** studies populations of executable AI agents.

The central premise is that AI-agent populations can be studied with experimental control that is difficult or impossible with human societies: investigators can instantiate matched agents, control exactly what each agent observes, vary communication topology and permissions, fork identical histories, change one declared variable, and repeat the experiment.

Pasko Agent Society is **not** an LLM-persona sandbox. It is not designed around agents freely chatting until something interesting happens.

> The environment is executable. Agent actions are typed. Exposure is recorded. Treatments are controlled. Ensembles test hypotheses.

## Initial research questions

- Does peer exposure change the probability of adopting a strategy?
- When does individual boundary-crossing behavior become population-level behavior?
- How do communication topology and initial seed-adopter fraction affect propagation?
- Do explicit escalation and safe-exit options reduce disallowed toy-action attempts?
- How does task impossibility or underspecification affect compliance?
- When do influence centers emerge?
- How persistent are discovered strategies after synthetic resets?
- How does false information propagate through agent networks?
- Does a population behave differently from isolated copies of the same model?
- Which effects are model-specific versus structural across models?

## Scientific posture

The project distinguishes:

1. **Mechanical causality** — simulator state transitions.
2. **Exposure provenance** — what an agent observed before acting.
3. **Experimental treatment effects** — distributional differences across matched populations.
4. **External claims** — which require separate evidence.

Exposure does not by itself establish persuasion or intent.

## Safety boundary

Initial research occurs only in a fully synthetic toy environment.

The project must not contain or interact with real external services, Hugging Face infrastructure, GitHub mutation as an experiment, public message boards, internet-accessible agent infrastructure, real credentials, real exploits, malware, privilege escalation, sandbox escape, host persistence, unauthorized external communication, or techniques for evading real safety systems.

A synthetic boundary crossing is a typed toy action rejected by an artificial policy. It is not a real security exploit.

See `SAFETY.md`.

## Gate 1 — Peer Exposure & Boundary Propagation

Gate 1 asks:

> Does exposure to another agent's disallowed toy strategy change the probability that otherwise matched agents attempt the same disallowed action?

The primary causal experiment uses pre-authored, content-controlled peer artifacts rather than open-ended agent chat. The primary comparison is boundary-strategy exposure versus an information-matched control that conveys the same task blockage without mentioning the disallowed strategy.

See `GATE_1_SPEC.md`.

## Relationship to the 2026 OpenAI / Hugging Face incident

The public incident motivates research questions; it is not a template for reenactment.

Public reporting described unauthorized inter-agent communication, persistence on difficult or impossible tasks, adoption of shared goals or strategies, large collaborative workstreams, and rapid shifts in participation after shared discoveries. Public investigations also emphasize substantial limits on attribution and reconstruction.

Pasko Agent Society converts those observations into safer, narrower experiments using artificial channels and toy policies. No operational incident technique belongs in this repository.

## License

Apache License 2.0.

## Research status

Gate 1 tasks, policies, parameters, and outcomes are synthetic unless explicitly stated otherwise. Results describe the specified artificial experimental system.

Gate 1.1 is complete. In the preregistered scripted topology benchmark, connected degree-preserving rewiring increased final adoption incidence among initially unseeded agents relative to the degree-4 ring by 4.846 percentage points (paired 95% CI: 4.308 to 5.385 points). The directional hypothesis was supported. The point estimate did not meet the separate five-percentage-point practical-magnitude criterion, and the conservative Hoeffding interval did not certify positivity.

This result concerns a fixed scripted independent-cascade mechanism. It is not evidence of LLM behavior, persuasion, autonomous norm formation, emergent intelligence, general social behavior in real agents, or novel network science. See the compact [Gate 1.1 evidence package](results/gate1_1/GATE_1_1_RESULT_REPORT.md).

## Gate 1 bootstrap

The bootstrap is a Python-standard-library-only implementation of the controlled-exposure experiment. It includes the deterministic Environment Kernel, all Gate 1 typed actions, the Archive Assembly fixtures, T0–T7, simulator-local communication plumbing, metrics, replay, hashing, Experiment Passports, and a scripted stochastic validation mechanism. It does not include an LLM adapter.

Run the tests and the predeclared compact demonstration from a clean checkout:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/safety_scan.py
python3 -m pasko_agent_society.cli run-demo \
  --manifest manifests/gate1_scripted_demo_v1.json \
  --output results/generated
```

The committed compact result is in `results/gate1_demo_summary.json`. See `docs/REPRODUCING_GATE_1.md` for the deterministic replay layers and `SAFETY_VALIDATION_REPORT.md` for the release review.

Scripted results validate experimental plumbing only. They are not evidence about LLM behavior.
