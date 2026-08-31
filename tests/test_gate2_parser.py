from __future__ import annotations

import json
import unittest

from pasko_agent_society.gate2.parser import ProviderIdentityError, parse_provider_response
from pasko_agent_society.gate2.protocol import ALLOWED_ACTIONS, MODEL_ID


def response(*, text=None, refusal=None, status="completed", model=MODEL_ID):
    content = []
    if text is not None:
        content.append({"type": "output_text", "text": text})
    if refusal is not None:
        content.append({"type": "refusal", "refusal": refusal})
    return {
        "id": "resp-fixture",
        "model": model,
        "service_tier": "default",
        "status": status,
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "output": [{"type": "message", "status": "completed", "content": content}],
    }


class Gate2ParserTests(unittest.TestCase):
    def test_all_four_strict_actions_are_valid(self) -> None:
        for action in ALLOWED_ACTIONS:
            with self.subTest(action=action):
                parsed = parse_provider_response(response(text=json.dumps({"action_type": action})))
                self.assertTrue(parsed.behavioral_valid)
                self.assertEqual(parsed.disposition, "VALID_ACTION")
                self.assertEqual(parsed.action_type, action)

    def test_explicit_refusal_is_valid_behavior_even_with_extra_malformed_text(self) -> None:
        parsed = parse_provider_response(response(text="not json", refusal="I cannot do that"))
        self.assertTrue(parsed.behavioral_valid)
        self.assertEqual(parsed.disposition, "EXPLICIT_REFUSAL")
        self.assertIsNone(parsed.action_type)

    def test_malformed_and_schema_invalid_outputs_are_technical(self) -> None:
        values = ("not json", json.dumps({"action_type": "UNKNOWN"}), json.dumps({"action_type": "ABSTAIN", "extra": 1}))
        for value in values:
            with self.subTest(value=value):
                parsed = parse_provider_response(response(text=value))
                self.assertFalse(parsed.behavioral_valid)
                self.assertIn(parsed.technical_error_code, {"MALFORMED_OUTPUT", "SCHEMA_INVALID_OUTPUT"})

    def test_incomplete_response_is_technical(self) -> None:
        parsed = parse_provider_response(response(status="incomplete"))
        self.assertFalse(parsed.behavioral_valid)
        self.assertEqual(parsed.technical_error_code, "INCOMPLETE_OUTPUT")

    def test_provider_model_mismatch_is_integrity_error(self) -> None:
        with self.assertRaises(ProviderIdentityError):
            parse_provider_response(response(text='{"action_type":"ABSTAIN"}', model="another-model"))


if __name__ == "__main__":
    unittest.main()
