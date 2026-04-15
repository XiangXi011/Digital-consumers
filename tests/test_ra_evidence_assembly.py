"""
CI Blocking Test: RA Evidence Assembly

Per testing-and-operations.md §test_ra_evidence_assembly.py:
Verify that minority or veto-based rejection evidence survives into
`minority_reject_evidence` and appears in the final RA output.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qualitative_research import (
    _extract_evidence_atoms,
    _group_evidence_atoms,
)


class TestRAEvidenceAssembly(unittest.TestCase):
    """Minority and veto-based rejection evidence must survive into final output."""

    def _make_mom_output(
        self,
        persona_id: str,
        persona_name: str,
        stance: str,
        concerns: list,
        motivations: list,
        core_needs: list,
        rubric_scores: dict | None = None,
    ) -> dict:
        return {
            "persona_id": persona_id,
            "persona_name": persona_name,
            "stance": stance,
            "concerns": concerns,
            "motivations": motivations,
            "core_needs": core_needs,
            "rubric_scores": rubric_scores or {
                "efficacy_clarity": 3,
                "trust_signal": 3,
                "convenience": 3,
                "price_fit": 3,
            },
            "verbatim_answer": "测试回答",
        }

    def test_minority_rejecting_persona_evidence_is_preserved(self):
        """A rejecting persona's concerns must appear in minority_reject_evidence."""
        mom_outputs = [
            self._make_mom_output(
                "M01", "宠爱富养家", "rejecting",
                concerns=["价格太低显得廉价", "缺乏进口品牌背书"],
                motivations=[],
                core_needs=["高端品质"],
            ),
            self._make_mom_output(
                "M02", "自在成长家", "interested",
                concerns=["希望颜值更高"],
                motivations=["小红书上有推荐", "性价比不错"],
                core_needs=["社媒种草"],
            ),
            self._make_mom_output(
                "M04", "高线忙碌派", "interested",
                concerns=[],
                motivations=["专业背书让人放心"],
                core_needs=["省心"],
            ),
        ]

        atoms = _extract_evidence_atoms(mom_outputs)
        groups = _group_evidence_atoms(atoms)

        # Minority reject evidence must be non-empty
        minority_rejects = groups["minority_reject_evidence"]
        self.assertTrue(len(minority_rejects) > 0, "Minority reject evidence must be preserved")

        # Rejecting persona's concerns must be in minority evidence
        minority_agent_ids = {a["agent_id"] for a in minority_rejects}
        self.assertIn("M01", minority_agent_ids)

        # Specific concern text must be preserved
        minority_values = [a["value"] for a in minority_rejects]
        self.assertTrue(
            any("廉价" in v or "进口" in v for v in minority_values),
            f"M01's rejection reasons must be preserved, got: {minority_values}",
        )

    def test_veto_low_scores_generate_evidence_atoms(self):
        """Low rubric scores (<=2) should generate evidence atoms."""
        mom_outputs = [
            self._make_mom_output(
                "M05", "品质精算师", "rejecting",
                concerns=["成分存疑"],
                motivations=[],
                core_needs=["可验证证据"],
                rubric_scores={
                    "efficacy_clarity": 2,
                    "trust_signal": 1,
                    "convenience": 3,
                    "price_fit": 2,
                },
            ),
        ]

        atoms = _extract_evidence_atoms(mom_outputs)

        # Low scores should produce evidence atoms
        score_atoms = [a for a in atoms if "分" in a["value"] and "满分" in a["value"]]
        self.assertTrue(len(score_atoms) > 0, "Low rubric scores must produce evidence atoms")

    def test_multiple_rejecting_personas_all_preserved(self):
        """When multiple personas reject, all rejection evidence must be preserved."""
        mom_outputs = [
            self._make_mom_output(
                "M01", "宠爱富养家", "rejecting",
                concerns=["不够高端"],
                motivations=[],
                core_needs=["进口品质"],
            ),
            self._make_mom_output(
                "M07", "全能优等家", "rejecting",
                concerns=["缺乏专业背书"],
                motivations=[],
                core_needs=["数据支撑"],
            ),
            self._make_mom_output(
                "M04", "高线忙碌派", "interested",
                concerns=["操作步骤偏多"],
                motivations=["品牌可信"],
                core_needs=["省心"],
            ),
        ]

        atoms = _extract_evidence_atoms(mom_outputs)
        groups = _group_evidence_atoms(atoms)

        minority_rejects = groups["minority_reject_evidence"]
        minority_agent_ids = {a["agent_id"] for a in minority_rejects}

        # Both rejecting personas must have evidence preserved
        self.assertIn("M01", minority_agent_ids)
        self.assertIn("M07", minority_agent_ids)

    def test_consensus_evidence_comes_from_majority(self):
        """Consensus evidence should come from non-rejecting personas."""
        mom_outputs = [
            self._make_mom_output(
                "M02", "自在成长家", "interested",
                concerns=[],
                motivations=["种草方便", "颜值高"],
                core_needs=["社媒口碑"],
            ),
            self._make_mom_output(
                "M04", "高线忙碌派", "interested",
                concerns=[],
                motivations=["品牌信任", "使用方便"],
                core_needs=["专业背书"],
            ),
            self._make_mom_output(
                "M06", "小镇贵妇妈", "interested",
                concerns=[],
                motivations=["功能多", "价格合理"],
                core_needs=["面子消费"],
            ),
        ]

        atoms = _extract_evidence_atoms(mom_outputs)
        groups = _group_evidence_atoms(atoms)

        consensus = groups["top_consensus_evidence"]
        self.assertTrue(len(consensus) > 0, "Consensus evidence must be present for agreeing personas")

        # Consensus should not contain minority-flagged atoms
        for atom in consensus:
            self.assertFalse(atom["is_minority"])

    def test_evidence_atoms_have_required_fields(self):
        """Every evidence atom must have all required fields per data-contracts.md."""
        mom_outputs = [
            self._make_mom_output(
                "M03", "传统关爱妈", "hesitant",
                concerns=["价格偏高"],
                motivations=["老牌子比较放心"],
                core_needs=["实惠"],
            ),
        ]

        atoms = _extract_evidence_atoms(mom_outputs)
        required_fields = {"agent_id", "persona_name", "field", "value", "weight_hint", "is_minority"}

        for atom in atoms:
            self.assertTrue(
                required_fields.issubset(atom.keys()),
                f"Atom missing fields: {required_fields - atom.keys()}",
            )
            self.assertIn(
                atom["field"],
                {"efficacy", "trust", "price", "convenience", "other"},
                f"Invalid evidence field: {atom['field']}",
            )


if __name__ == "__main__":
    unittest.main()
