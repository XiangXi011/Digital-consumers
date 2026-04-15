"""
CI Blocking Test: Mom Agent Cannot Read Peer Outputs

Per testing-and-operations.md §test_mom_agent_cannot_read_peer_outputs.py:
Verify that persona nodes are architecturally isolated — each persona agent
receives only its own YAML, the shared research input, and the shared
research plan. No peer outputs, no raw chat history, no debug JSON.
"""

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qualitative_research import MomPersonaAgent, QualitativeResearchInput


class TestMomAgentCannotReadPeerOutputs(unittest.TestCase):
    """Persona agents must not have access to peer outputs or raw chat history."""

    def test_mom_agent_init_receives_only_own_yaml(self):
        """MomPersonaAgent constructor accepts only its own persona dict and YAML."""
        sig = inspect.signature(MomPersonaAgent.__init__)
        params = list(sig.parameters.keys())
        # Should be: self, persona, ai_client, persona_yaml
        self.assertIn("persona", params)
        self.assertIn("ai_client", params)
        self.assertNotIn("peer_outputs", params)
        self.assertNotIn("all_outputs", params)
        self.assertNotIn("chat_history", params)

    def test_mom_agent_run_receives_only_research_input_and_plan(self):
        """MomPersonaAgent.run() accepts only research_input and plan, not peer data."""
        sig = inspect.signature(MomPersonaAgent.run)
        params = list(sig.parameters.keys())
        # Should be: self, research_input, research_plan
        self.assertIn("research_input", params)
        self.assertNotIn("peer_outputs", params)
        self.assertNotIn("all_outputs", params)
        self.assertNotIn("other_personas", params)
        self.assertNotIn("chat_history", params)
        self.assertNotIn("raw_chat", params)
        self.assertNotIn("debug_json", params)

    def test_mom_agent_has_no_peer_output_attribute(self):
        """MomPersonaAgent instances must not store peer outputs."""
        persona = {"segment_id": "M04", "segment_name": "高线忙碌派"}

        class FakeClient:
            is_configured = True

        agent = MomPersonaAgent(persona, FakeClient())
        self.assertFalse(hasattr(agent, "peer_outputs"))
        self.assertFalse(hasattr(agent, "all_outputs"))
        self.assertFalse(hasattr(agent, "chat_history"))

    def test_prompt_method_does_not_accept_peer_data(self):
        """_prompt() must not accept peer_outputs or chat_history."""
        sig = inspect.signature(MomPersonaAgent._prompt)
        params = list(sig.parameters.keys())
        self.assertNotIn("peer_outputs", params)
        self.assertNotIn("all_outputs", params)
        self.assertNotIn("chat_history", params)
        self.assertNotIn("raw_chat", params)

    def test_research_input_does_not_contain_peer_outputs(self):
        """QualitativeResearchInput must not carry peer output data."""
        research_input = QualitativeResearchInput(
            mode="multi",
            question_type="product_concept",
            user_question="Will moms buy this?",
            product_info="Kids toothpaste",
        )
        # Research input is the shared context — it must not carry peer outputs
        self.assertFalse(hasattr(research_input, "peer_outputs"))
        self.assertFalse(hasattr(research_input, "all_persona_outputs"))
        self.assertFalse(hasattr(research_input, "raw_chat_history"))


if __name__ == "__main__":
    unittest.main()
