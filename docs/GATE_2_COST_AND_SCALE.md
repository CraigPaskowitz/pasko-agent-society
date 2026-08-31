# Gate 2 Cost and Scale Proposal

> **Pricing observation date:** 2026-08-30
>
> **Status:** Frozen preregistration cost plan. No production model request has been made.

## Proposed scale

| Quantity | Value |
|---|---:|
| Analyzed technically valid matched pairs | 200 |
| Frozen reserve pairs | 20 |
| Target agents per condition | 54 |
| Calls per matched population pair | 108 |
| Analyzed logical decision slots | 21,600 |
| Maximum logical slots across IDs 000–219 | 23,760 |
| Maximum provider attempts at three per slot | 71,280 |
| Conservative input ceiling per call | 1,200 tokens |
| Maximum output tokens per call | 64 tokens |
| Analyzed one-attempt input ceiling | 25,920,000 tokens |
| Analyzed one-attempt output ceiling | 1,382,400 tokens |
| Full-pool one-attempt input ceiling | 28,512,000 tokens |
| Full-pool one-attempt output ceiling | 1,520,640 tokens |
| Full-pool three-attempt input ceiling | 85,536,000 tokens |
| Full-pool three-attempt output ceiling | 4,561,920 tokens |

The 1,200-token input ceiling materially exceeds the expected compact prompt and provides budget headroom without changing model context. The implementation must measure the frozen request corpus before execution and stop if any production request exceeds the ceiling.

## Model and current unit prices

The protocol uses `gpt-5.4-mini-2026-03-17`. Official OpenAI documentation lists the dated snapshot, Responses API support, Structured Outputs support, and current standard prices of $0.75 per million input tokens and $4.50 per million output tokens. See the official [GPT-5.4 Mini model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and [API pricing](https://developers.openai.com/api/docs/pricing).

Pricing and account-specific availability can change. They must be reverified before the preregistration is publicly frozen and again before execution. A price change does not authorize changing the model, prompt, sample size, or scientific design after outcome generation.

## Conservative cost calculation

At the documented standard token rates:

```text
analyzed input  = 25.92000 million * $0.75 = $19.44000
analyzed output =  1.38240 million * $4.50 =  $6.22080
analyzed one-attempt maximum                    $25.66080

full-pool input  = 28.51200 million * $0.75 = $21.38400
full-pool output =  1.52064 million * $4.50 =  $6.84288
full-pool one-attempt maximum                    $28.22688

three-attempt full-pool worst case = 3 * $28.22688 = $84.68064
```

The frozen hard provider-billed ceiling is `$85.00`, the smallest sensible whole-dollar amount above the conservative reserve-plus-three-attempt maximum. Retryable technical failures may increase attempts, but only one valid behavioral observation may be credited to a logical slot. The runner must stop before submitting a request that could exceed the remaining ceiling under the frozen per-request token maximum. A ceiling stop pauses the campaign and keeps it incomplete; if the frozen pool cannot produce 200 technically valid pairs within the ceiling, the campaign is `INVALID_INCONCLUSIVE`. It does not authorize a smaller sample, cheaper model, shorter prompt, added reserves, or partial analysis.

## Precision and power rationale

The primary analysis uses 200 population-pair differences, each based on 54 target decisions per condition.

Under an outcome-independent worst-case Bernoulli variance of `0.25` per target and conditional independence within a population, the maximum paired-population variance is:

```text
0.25 / 54 + 0.25 / 54 = 0.009259259259259259
```

At 200 pairs, this gives a standard error no larger than approximately `0.006804` and a two-sided 95 percent paired-t half-width of approximately `0.01342` using `t(0.975,199) = 1.971956544249...`.

Because provider calls may be correlated within a population/time block, the design also evaluates conservative intraclass-correlation planning scenarios without using observed Gate 2 outcomes:

| Assumed within-condition ICC | Approximate 95% half-width | Approximate power for the frozen primary rule at a 0.05 effect |
|---:|---:|---:|
| 0.00 | 0.0134 | >0.999 |
| 0.05 | 0.0256 | 0.970 |
| 0.10 | 0.0337 | 0.830 |

Power uses the preregistered lower bound of a two-sided 95 percent interval clearing zero, equivalent to a one-sided 0.025 threshold. These are planning assumptions, not claims about provider independence. The experiment remains valid if the effect is smaller, zero, negative, or more variable than these scenarios.

## Throughput and wall-clock estimate

The official model page currently lists Tier 1 limits of 500 requests per minute and 500,000 tokens per minute. The protocol deliberately freezes lower client-side limits of 400 requests and 480,000 estimated input tokens per rolling minute, regardless of a higher account tier.

- 54.0 minutes for the 21,600 analyzed one-attempt slots at 400 RPM;
- 59.4 minutes for all 23,760 frozen IDs at one attempt per slot;
- 178.2 minutes for the full 71,280-attempt conservative maximum.

Actual execution will be slower because of latency, provider scheduling, output tokens, safety checks, checkpointing, and retries. A reasonable expected planning range is 1–4 hours; the extreme all-slots-three-attempt envelope may take 3–8 hours. The implementation must record dispatch and completion times and preserve adjacent matched-condition scheduling.

Batch processing is not authorized. Switching to Batch, Flex, Fast mode, another service tier, or another model after freeze could change timing or provider behavior and therefore requires a preregistration amendment before production calls.

## Cost-governance rules

- No API key is required for repository tests, CI, replay, or analysis.
- No live call may occur before a separate implementation certification and execution authorization.
- The campaign status must expose spent and maximum possible remaining cost without exposing interim treatment outcomes.
- Technical retries are allowed only when no valid behavioral response exists; refusals and valid action choices are never retried.
- A pricing or rate-limit change that makes the frozen campaign infeasible is a blocker, not permission to tune the scientific design.
