from __future__ import annotations

import copy
import unittest

from pasko_agent_society.fixtures import BOUNDARY_RULE_ID, TREATMENTS, task_for_treatment
from pasko_agent_society.graph import empty_graph, ring_graph
from pasko_agent_society.kernel import EnvironmentKernel
from pasko_agent_society.schemas import ActionIntent, ActionType


def kernel_for(treatment: str = "T2", agents: tuple[str, ...] = ("agent-000",)) -> EnvironmentKernel:
    return EnvironmentKernel(
        experiment_id="test-experiment",
        replicate_id="replicate-000",
        task=task_for_treatment(treatment),
        treatment=TREATMENTS[treatment],
        agent_ids=agents,
        graph=empty_graph(),
    )


def intent(
    kernel: EnvironmentKernel,
    action_type: ActionType | str,
    *,
    suffix: str = "one",
    agent_id: str = "agent-000",
    **kwargs: object,
) -> ActionIntent:
    return ActionIntent(
        action_id=f"action-{suffix}",
        agent_id=agent_id,
        tick=kernel.state["tick"],
        action_type=action_type,
        **kwargs,
    )


class KernelSafetyTests(unittest.TestCase):
    def test_disallowed_action_is_always_rejected_without_state_mutation(self) -> None:
        kernel = kernel_for()
        before = kernel.final_state_hash
        resolution = kernel.resolve(intent(kernel, ActionType.READ_SEALED_CACHE))
        self.assertFalse(resolution.permitted)
        self.assertFalse(resolution.executed)
        self.assertEqual(resolution.policy_rule_id, BOUNDARY_RULE_ID)
        self.assertEqual(before, kernel.final_state_hash)

    def test_disallowed_action_is_rejected_in_every_treatment(self) -> None:
        for treatment_id in sorted(TREATMENTS):
            with self.subTest(treatment=treatment_id):
                kernel = kernel_for(treatment_id)
                kernel.advance_tick()
                before = kernel.final_state_hash
                resolution = kernel.resolve(
                    intent(
                        kernel,
                        ActionType.READ_SEALED_CACHE,
                        suffix=f"sealed-{treatment_id.casefold()}",
                    )
                )
                self.assertFalse(resolution.permitted)
                self.assertFalse(resolution.executed)
                self.assertEqual(resolution.policy_rule_id, BOUNDARY_RULE_ID)
                self.assertEqual(before, kernel.final_state_hash)

    def test_unknown_action_cannot_execute(self) -> None:
        kernel = kernel_for()
        before = copy.deepcopy(kernel.state)
        resolution = kernel.resolve(intent(kernel, "OPEN_REAL_SYSTEM"))
        self.assertFalse(resolution.executed)
        self.assertEqual(resolution.failure_reason, "UNKNOWN_ACTION")
        self.assertEqual(before, kernel.state)

    def test_url_host_path_and_command_payloads_are_rejected(self) -> None:
        unsafe_values = (
            "https:" + "//example.invalid",
            "/" + "private/example",
            ".." + "/relative",
            "bash",
            "C:" + "\\private",
        )
        for index, value in enumerate(unsafe_values):
            with self.subTest(value=value):
                kernel = kernel_for()
                resolution = kernel.resolve(
                    intent(
                        kernel,
                        ActionType.ESCALATE,
                        suffix=f"unsafe-{index}",
                        structured_payload={"reason_code": value},
                    )
                )
                self.assertFalse(resolution.executed)
                self.assertIn(
                    resolution.failure_reason,
                    {"UNSAFE_PAYLOAD_VALUE", "UNSAFE_OR_INVALID_IDENTIFIER"},
                )

    def test_arbitrary_payload_field_is_rejected(self) -> None:
        kernel = kernel_for()
        resolution = kernel.resolve(
            intent(
                kernel,
                ActionType.ESCALATE,
                structured_payload={"reason_code": "TASK_BLOCKED", "extra": "VALUE"},
            )
        )
        self.assertEqual(resolution.failure_reason, "UNKNOWN_PAYLOAD_FIELD")

    def test_required_action_target_cannot_be_omitted(self) -> None:
        kernel = kernel_for()
        resolution = kernel.resolve(intent(kernel, ActionType.CREATE_ARTIFACT))
        self.assertFalse(resolution.executed)
        self.assertEqual(resolution.failure_reason, "MISSING_ACTION_TARGET")
        self.assertNotIn(None, kernel.state["artifacts"])

    def test_successful_mutation_has_ledger_provenance(self) -> None:
        kernel = kernel_for()
        kernel.advance_tick()
        revision_before = kernel.state["revision"]
        resolution = kernel.resolve(
            intent(
                kernel,
                ActionType.REQUEST_RESOURCE,
                resource_id="resource-red",
            )
        )
        self.assertTrue(resolution.executed)
        self.assertGreater(kernel.state["revision"], revision_before)
        self.assertTrue(
            any(
                event["event_type"] == "RESOURCE_GRANTED"
                and event["mutation_paths"] == ["agents.agent-000.held_tokens"]
                for event in kernel.ledger
            )
        )
        kernel.assert_invariants()

    def test_unavailable_green_never_mutates_blocked_resources(self) -> None:
        kernel = kernel_for("T5")
        kernel.advance_tick()
        resolution = kernel.resolve(
            intent(
                kernel,
                ActionType.REQUEST_RESOURCE,
                resource_id="resource-green",
            )
        )
        self.assertTrue(resolution.permitted)
        self.assertFalse(resolution.executed)
        self.assertEqual(resolution.failure_reason, "RESOURCE_UNAVAILABLE")
        self.assertEqual(kernel.state["agents"]["agent-000"]["held_tokens"], [])

    def test_observation_is_agent_scoped(self) -> None:
        kernel = kernel_for(agents=("agent-000", "agent-001"))
        observation = kernel.observation_bundle("agent-000")
        self.assertNotIn("agents", observation)
        self.assertNotIn("ledger", observation)
        self.assertNotIn("originating_treatment", str(observation))
        self.assertEqual(observation["agent_id"], "agent-000")

    def test_external_message_target_cannot_enter_state(self) -> None:
        graph = ring_graph(("agent-000", "agent-001"))
        kernel = EnvironmentKernel(
            experiment_id="test-graph",
            replicate_id="replicate-000",
            task=task_for_treatment("T2"),
            treatment=TREATMENTS["T2"],
            agent_ids=("agent-000", "agent-001"),
            graph=graph,
        )
        kernel.advance_tick()
        resolution = kernel.resolve(
            intent(
                kernel,
                ActionType.SEND_MESSAGE,
                target_id="https:" + "//example.invalid",
                channel_id="channel-ring",
                structured_payload={
                    "message_type": "STRATEGY_LINEAGE",
                    "strategy_plan": ["READ_SEALED_CACHE"],
                    "originating_strategy": "READ_SEALED_CACHE",
                },
            )
        )
        self.assertFalse(resolution.executed)
        self.assertEqual(kernel.state["messages"], {})

    def test_artifact_delivery_is_exact_and_provenanced(self) -> None:
        kernel = kernel_for("T2", ("agent-000", "agent-001"))
        artifact = kernel.state["artifacts"]["artifact-controlled-peer-note"]
        self.assertEqual(artifact["content"]["peer_action"], "READ_SEALED_CACHE")
        deliveries = [
            event for event in kernel.ledger if event["event_type"] == "ARTIFACT_DELIVERED"
        ]
        self.assertEqual(len(deliveries), 2)
        self.assertEqual(
            {event["payload"]["originating_treatment"] for event in deliveries}, {"T2"}
        )


class GraphDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ring_graph(("agent-000", "agent-001", "agent-002"))
        self.kernel = EnvironmentKernel(
            experiment_id="test-graph",
            replicate_id="replicate-000",
            task=task_for_treatment("T0"),
            treatment=TREATMENTS["T0"],
            agent_ids=("agent-000", "agent-001", "agent-002"),
            graph=self.graph,
        )
        self.kernel.advance_tick()
        for index, agent_id in enumerate(("agent-000", "agent-001")):
            resolution = self.kernel.resolve(
                intent(
                    self.kernel,
                    ActionType.JOIN_CHANNEL,
                    suffix=f"join-{index}",
                    agent_id=agent_id,
                    channel_id="channel-ring",
                )
            )
            self.assertTrue(resolution.executed)

    def test_structured_message_is_simulator_local_and_delayed(self) -> None:
        resolution = self.kernel.resolve(
            intent(
                self.kernel,
                ActionType.SEND_MESSAGE,
                suffix="send",
                target_id="agent-001",
                channel_id="channel-ring",
                structured_payload={
                    "message_type": "STRATEGY_LINEAGE",
                    "strategy_plan": ["READ_SEALED_CACHE"],
                    "originating_strategy": "READ_SEALED_CACHE",
                },
            )
        )
        self.assertTrue(resolution.executed)
        self.assertEqual(self.kernel.state["agents"]["agent-001"]["inbox_message_ids"], [])
        self.kernel.advance_tick()
        self.assertEqual(
            self.kernel.state["agents"]["agent-001"]["inbox_message_ids"],
            ["message-00000000"],
        )
        delivery = next(
            event for event in self.kernel.ledger if event["event_type"] == "MESSAGE_DELIVERED"
        )
        self.assertEqual(delivery["payload"]["target_agent_id"], "agent-001")
        self.assertEqual(delivery["payload"]["parent_message_id"], None)

    def test_free_form_message_payload_is_rejected(self) -> None:
        resolution = self.kernel.resolve(
            intent(
                self.kernel,
                ActionType.SEND_MESSAGE,
                suffix="free-form",
                target_id="agent-001",
                channel_id="channel-ring",
                structured_payload={
                    "message_type": "arbitrary prose is not accepted",
                    "strategy_plan": ["ESCALATE"],
                    "originating_strategy": "ESCALATE",
                },
            )
        )
        self.assertFalse(resolution.executed)
        self.assertEqual(resolution.failure_reason, "UNSAFE_PAYLOAD_VALUE")


if __name__ == "__main__":
    unittest.main()
