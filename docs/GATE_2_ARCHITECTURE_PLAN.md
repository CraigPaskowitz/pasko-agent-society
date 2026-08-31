# Gate 2 Architecture Plan

> **Status:** Frozen preregistration architecture. No adapter, provider dependency, API key handling, live transport, production manifest, or model result exists at preregistration.

## Boundary to add

The kernel remains deterministic and network-free. A narrow operator-controlled provider transport sits outside the kernel and supplies an untrusted structured response to a strict parser.

```text
Simulator observation
  -> canonical prompt renderer
  -> immutable model request record
  -> one allowlisted provider transport
  -> immutable raw response record
  -> strict refusal/JSON-schema parser
  -> bounded ActionIntent or recorded nondecision
  -> existing EnvironmentKernel
  -> ledger, state hash, replay, metrics
```

The model never receives a transport, tool, URL, credential, filesystem handle, shell, browser, connector, or callback. It cannot call the environment. It emits one enum value; the kernel alone resolves it.

## Minimal interfaces

### `ModelDecisionRequest`

Bind at minimum:

- protocol, campaign, population, condition, source, and target identities;
- observation-bundle canonical hash;
- system, developer, observation-base, condition-artifact, and response-schema hashes;
- exact rendered request-body hash;
- provider enum, endpoint/API family, dated model snapshot, and generation fields;
- deterministic dispatch position and attempt number;
- absence of tools, conversation state, and external resources.

### `ModelCallRecord`

Retain:

- request hash and attempt lineage;
- provider response ID, returned model identity, status, service tier, and timestamps;
- raw response hash and a privacy-reviewed raw response body;
- input, cached-input, output, and reasoning-token usage where returned;
- normalized structured action or explicit refusal as behavioral output;
- malformed response, incomplete response, transport/API error, and retry/exhaustion metadata as technical evidence;
- parser version and normalized-decision hash;
- no authorization header, API key, environment dump, or chain-of-thought.

### `BoundedDecisionParser`

The parser accepts only the exact `gate2-action-choice-v1` object. Unknown keys, unknown enum values, arrays, prose, tool calls, and nested payloads cannot create an action. A valid action receives `model_output_reference=<normalized-record-hash>` before entering the existing kernel.

Provider refusal is a technically valid recorded model outcome and produces no intent. It is not retried or rewritten as a model-selected `ABSTAIN` action. Malformed/incomplete output is simulator-inert but technically retryable and never silently scored as non-adoption.

## Capability separation

Gate 2 requires one external inference transport, but that transport is not an agent tool.

- The core simulator and replay path import no network client.
- The provider adapter is separately invoked by the operator runner.
- Only the fixed OpenAI Responses endpoint may be addressed by the adapter implementation.
- The campaign manifest selects a provider enum, never an arbitrary URL.
- Credentials remain process-local to the provider client, are never model-visible, never serialized, and never committed.
- Tests and CI inject fixture transports and require no API key or network.
- The base package remains runnable without installing the optional provider extra.

Any implementation that lets model output alter a URL, request header, filesystem path, function name, tool list, or Python callable violates this plan.

## Prompt construction

The renderer must:

1. read the six frozen prompt/schema assets;
2. validate that the treatment and control artifacts equal the existing Gate 1 T2/T5 visible artifacts byte-for-data;
3. combine the frozen observation object and selected peer artifact without exposing simulator, treatment, or campaign IDs;
4. canonicalize JSON using UTF-8, sorted keys, no insignificant whitespace, and no locale-dependent rendering;
5. create separate system, developer, and user messages without concatenating role boundaries;
6. hash each component and the complete request before dispatch;
7. refuse any unregistered field or prompt hash.

Population and condition IDs are provenance metadata, not prompt prose. Agent and peer IDs may appear only in their frozen observation fields and are identical across the matched conditions.

## Model/environment randomness separation

- Root `20260903` and namespace `gate2-v1` determine target ordering, source-target mapping validation, and condition dispatch order; population eligibility is the frozen ascending ID order 000–219.
- They do not claim to seed the provider model.
- Each model call is a fresh stateless request with no `previous_response_id` or conversation.
- Provider stochasticity is measured as part of the declared model configuration and is not presented as deterministic.
- Environment replay consumes normalized recorded actions and must reproduce identical ledger and state hashes without contacting the provider.

## Storage and resumability

One target-condition decision slot has an immutable request record and one to three atomic attempt records. A slot becomes behaviorally complete only with one valid structured action or explicit refusal. One matched population pair is one durable scientific chunk containing all 108 valid behavioral observations plus both deterministic environment replays. Populations execute one at a time in ascending frozen ID order. If any slot exhausts three technical attempts, the whole population is recorded as technically invalid before the next eligible reserve ID is considered. The first 200 valid IDs form the inferential sample. Within each population, 54 target blocks use exact 27/27 condition-order balance and a fixed 20-worker scheduler. All attempts share frozen 400-RPM and 480,000-input-TPM client-side dispatch ceilings.

The implementation should provide:

- request records written before dispatch;
- attempt journals separate from accepted call records;
- atomic same-directory writes and per-slot locks;
- deterministic behavioral-response selection and technical retry accounting;
- duplicate, ambiguous-attempt, and corrupt-record rejection;
- per-population completion and campaign completion manifests;
- explicit completed, pending, refusal, technical-invalid, reserve, resumed, and retried counts;
- analysis lock until the first 200 technically valid populations and every excluded technical population reconstruct and the campaign validity rules pass;
- operational status that never exposes condition-separated action counts before completion.

## Outcome-blind implementation certification

Before any production call:

- freeze the implementation source and campaign manifest;
- prove prompt hashes and T2/T5 equality;
- prove no provider call occurs in unit tests or CI;
- use fixture transports for valid action, refusal, malformed-then-valid, incomplete-then-valid, exhausted technical failure, timeout, rate limit, server error, duplicate, and late-response cases;
- prove unknown output cannot reach the kernel;
- prove every `READ_SEALED_CACHE` intent remains rejected;
- prove model-call replay does not contact the provider;
- prove serial/parallel kernel replay equivalence;
- prove analysis refuses partial or identity-mismatched corpora;
- verify Gate 1 through Gate 1.2 hashes and tests remain unchanged.

A minimal scientifically unrelated provider capability handshake is allowed after the preregistration freeze under a `NONPRODUCTION_PROVIDER_SMOKE_TEST` identity. It must not contain the Archive Assembly task, T2/T5 artifacts, production prompt, or production model-call identity, and it cannot be used to tune the prompt.

## Proposed repository structure

```text
preregistrations/
  GATE_2_PREREGISTRATION.md
docs/
  GATE_2_DESIGN_REVIEW.md
  GATE_2_ARCHITECTURE_PLAN.md
  GATE_2_COST_AND_SCALE.md
  GATE_2_IMPLEMENTATION_CERTIFICATION.md       # future
prompts/gate2_peer_exposure_v1/
  system.txt
  developer.txt
  observation-base.json
  treatment-artifact.json
  control-artifact.json
schemas/
  gate2_action_choice_v1.json
  gate2_model_call_v1.json                     # future
  gate2_population_chunk_v1.json               # future
manifests/
  gate2_peer_exposure_v1.json                  # only after preregistration freeze
pasko_agent_society/gate2/
  protocol.py                                  # future
  renderer.py                                  # future
  parser.py                                    # future
  records.py                                   # future
  storage.py                                   # future
  analysis.py                                  # future
  provider_openai.py                           # optional live boundary, future
scripts/
  gate2_status.py                              # future
  gate2_run.py                                 # future
  gate2_verify.py                              # future
  gate2_analyze.py                             # future
tests/
  test_gate2_*.py                              # future, fixture-only
artifacts/gate2_peer_exposure_v1/              # ignored production corpus
results/gate2/                                 # compact frozen evidence
```

No future path listed above is authorized for implementation or execution by this design document.
