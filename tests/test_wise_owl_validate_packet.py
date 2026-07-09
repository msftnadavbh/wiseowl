import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_validate_packet.py"
FIXTURES = ROOT / "tests" / "fixtures"


VALID_CRITIC = {
    "role": "logic_owl",
    "verdict": "blocked",
    "findings": [
        {
            "id": "E1",
            "severity": "blocking",
            "category": "correctness",
            "issue": "The validator accepts empty evidence.",
            "evidence": "tests/test_wise_owl_validate_packet.py exercises an empty evidence string.",
            "impact": "Prime Owl cannot distinguish grounded findings from guesses.",
            "suggested_fix": "Reject blank evidence strings.",
            "confidence": "high",
        }
    ],
    "notes": [],
}

VALID_PRIME = {
    "verdict": "fix_required",
    "accepted_findings": [
        {
            "source_ids": ["logic_owl:E1"],
            "severity": "blocking",
            "category": "correctness",
            "issue": "The validator accepts empty evidence.",
            "evidence": "logic_owl:E1 includes a blank evidence field in the supplied critic output.",
            "impact": "The builder may receive ungrounded blocking work.",
            "required_builder_action": "Reject accepted findings with blank evidence.",
        }
    ],
    "rejected_findings": [
        {
            "source_ids": ["guardian_owl:S2"],
            "reason": "no_evidence",
            "explanation": "The critic did not cite a file, command, or constraint.",
        }
    ],
    "builder_instructions": ["Apply all blocking accepted findings."],
}


def prime_packet(verdict, accepted_findings):
    return {
        "verdict": verdict,
        "accepted_findings": accepted_findings,
        "rejected_findings": [],
        "builder_instructions": ["Apply the Prime Owl decision."],
    }


class ValidatePacketTest(unittest.TestCase):
    def run_validator(self, packet, packet_type):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(packet, handle)
            packet_path = Path(handle.name)
        try:
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--type", packet_type, "--file", str(packet_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            packet_path.unlink(missing_ok=True)

    def run_prime_with_critics(self, prime_packet, critic_packets, mode=None):
        paths = []
        try:
            for packet in [prime_packet, *critic_packets]:
                handle = tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False)
                with handle:
                    json.dump(packet, handle)
                    paths.append(Path(handle.name))
            command = [sys.executable, str(SCRIPT), "--type", "prime", "--file", str(paths[0])]
            if paths[1:]:
                command.extend(["--critics", *map(str, paths[1:])])
            if mode:
                command.extend(["--mode", mode])
            return subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            for path in paths:
                path.unlink(missing_ok=True)

    def test_valid_critic_passes(self):
        result = self.run_validator(VALID_CRITIC, "critic")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_critic_pass_with_notes_passes(self):
        for packet_name in (
            "critic_valid_logic_pass.json",
            "critic_valid_proof_pass.json",
            "critic_valid_guardian_pass.json",
        ):
            with self.subTest(packet_name=packet_name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--type", "critic", "--file", str(FIXTURES / packet_name)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_critic_pass_missing_notes_fails(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--type", "critic", "--file", str(FIXTURES / "critic_invalid_pass_missing_notes.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("$.notes: missing required field", result.stderr)

    def test_critic_pass_malformed_notes_fail(self):
        for packet_name in (
            "critic_invalid_pass_empty_notes.json",
            "critic_invalid_pass_null_note.json",
            "critic_invalid_pass_blank_note.json",
            "critic_invalid_pass_non_string_note.json",
        ):
            with self.subTest(packet_name=packet_name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--type", "critic", "--file", str(FIXTURES / packet_name)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("notes", result.stderr)

    def test_critic_verdict_must_match_finding_severities(self):
        cases = (
            ("critic_invalid_pass_with_findings.json", "expected 'concerns'"),
            ("critic_invalid_concerns_empty.json", "expected 'pass'"),
            ("critic_invalid_blocked_without_blocking.json", "expected 'concerns'"),
        )
        for packet_name, expected_error in cases:
            with self.subTest(packet_name=packet_name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--type", "critic", "--file", str(FIXTURES / packet_name)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_critic_blocked_with_blocking_finding_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--type", "critic", "--file", str(FIXTURES / "critic_valid_blocked.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_critic_missing_evidence_fails(self):
        packet = copy.deepcopy(VALID_CRITIC)
        packet["findings"][0]["evidence"] = " "
        result = self.run_validator(packet, "critic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence", result.stderr)

    def test_critic_blank_actionable_fields_fail(self):
        packet = copy.deepcopy(VALID_CRITIC)
        packet["findings"][0]["issue"] = ""
        packet["findings"][0]["impact"] = " "
        packet["findings"][0]["suggested_fix"] = "\t"
        result = self.run_validator(packet, "critic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue", result.stderr)
        self.assertIn("impact", result.stderr)
        self.assertIn("suggested_fix", result.stderr)

    def test_unknown_critic_role_fails(self):
        packet = copy.deepcopy(VALID_CRITIC)
        packet["role"] = "owl_style"
        result = self.run_validator(packet, "critic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("role", result.stderr)

    def test_duplicate_critic_finding_id_fails(self):
        packet = copy.deepcopy(VALID_CRITIC)
        packet["findings"].append(copy.deepcopy(packet["findings"][0]))
        result = self.run_validator(packet, "critic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate critic finding id", result.stderr)

    def test_valid_prime_owl_packet_passes(self):
        result = self.run_validator(VALID_PRIME, "prime")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_valid_prime_pass_with_no_accepted_findings(self):
        result = self.run_validator(prime_packet("pass", []), "prime")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_prime_pass_empty_schema_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--type", "prime", "--file", str(FIXTURES / "prime_valid_pass_empty.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Source accounting was not checked", result.stdout)

    def test_explicit_empty_critics_fails(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--type", "prime", "--file", str(FIXTURES / "prime_valid_pass_empty.json"), "--critics"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected at least one argument", result.stderr)

    def test_prime_pass_missing_builder_instructions_fails(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--type",
                "prime",
                "--file",
                str(FIXTURES / "prime_invalid_pass_missing_required_fields.json"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("$.builder_instructions: missing required field", result.stderr)

    def test_prime_pass_critic_style_fails(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--type", "prime", "--file", str(FIXTURES / "prime_invalid_pass_critic_style.json")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("$.role: unexpected field", result.stderr)
        self.assertIn("$.findings: unexpected field", result.stderr)
        self.assertIn("$.notes: unexpected field", result.stderr)

    def test_valid_prime_caution_with_non_blocking_finding(self):
        finding = copy.deepcopy(VALID_PRIME["accepted_findings"][0])
        finding["severity"] = "non_blocking"
        result = self.run_validator(prime_packet("caution", [finding]), "prime")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fix_required_without_blocking_fails(self):
        finding = copy.deepcopy(VALID_PRIME["accepted_findings"][0])
        finding["severity"] = "suggestion"
        result = self.run_validator(prime_packet("fix_required", [finding]), "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 'caution'", result.stderr)

    def test_pass_with_accepted_finding_fails(self):
        finding = copy.deepcopy(VALID_PRIME["accepted_findings"][0])
        finding["severity"] = "non_blocking"
        result = self.run_validator(prime_packet("pass", [finding]), "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 'caution'", result.stderr)

    def test_pass_with_blocking_finding_fails(self):
        result = self.run_validator(prime_packet("pass", [copy.deepcopy(VALID_PRIME["accepted_findings"][0])]), "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 'fix_required'", result.stderr)

    def test_caution_without_accepted_findings_fails(self):
        result = self.run_validator(prime_packet("caution", []), "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 'pass'", result.stderr)

    def test_caution_with_blocking_finding_fails(self):
        result = self.run_validator(prime_packet("caution", [copy.deepcopy(VALID_PRIME["accepted_findings"][0])]), "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 'fix_required'", result.stderr)

    def test_invalid_confidence_fails(self):
        packet = copy.deepcopy(VALID_CRITIC)
        packet["findings"][0]["confidence"] = "certain"
        result = self.run_validator(packet, "critic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confidence", result.stderr)

    def test_prime_accepted_finding_missing_evidence_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["evidence"] = ""
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence", result.stderr)

    def test_prime_missing_required_builder_action_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        del packet["accepted_findings"][0]["required_builder_action"]
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_builder_action", result.stderr)

    def test_prime_blank_actionable_fields_fail(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["issue"] = ""
        packet["accepted_findings"][0]["impact"] = " "
        packet["accepted_findings"][0]["required_builder_action"] = "\n"
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue", result.stderr)
        self.assertIn("impact", result.stderr)
        self.assertIn("required_builder_action", result.stderr)

    def test_prime_blank_builder_instruction_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["builder_instructions"] = [" "]
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("builder_instructions", result.stderr)

    def test_prime_bad_rejection_reason_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"][0]["reason"] = "vibes"
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reason", result.stderr)

    def test_prime_blank_rejection_explanation_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"][0]["explanation"] = " "
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explanation", result.stderr)

    def test_prime_empty_accepted_source_ids_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["source_ids"] = []
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_ids", result.stderr)

    def test_prime_empty_rejected_source_ids_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"][0]["source_ids"] = []
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_ids", result.stderr)

    def test_prime_duplicate_source_id_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"][0]["source_ids"] = ["logic_owl:E1"]
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate source_id", result.stderr)

    def test_prime_old_role_source_id_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["source_ids"] = ["owl_guard:OG1"]
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid source_id", result.stderr)

    def test_prime_critic_schema_fields_fail(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["id"] = "E1"
        packet["accepted_findings"][0]["suggested_fix"] = "Use the critic schema."
        packet["accepted_findings"][0]["confidence"] = "high"
        packet["role"] = "prime_owl"
        packet["notes"] = []
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("$.role: unexpected field", result.stderr)
        self.assertIn("accepted_findings[0].id: unexpected field", result.stderr)

    def test_prime_singular_source_id_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"][0]["source_id"] = packet["rejected_findings"][0].pop("source_ids")
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_id: unexpected field", result.stderr)

    def test_require_critics_fails_without_critics(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(VALID_PRIME, handle)
            packet_path = Path(handle.name)
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--type", "prime", "--file", str(packet_path), "--require-critics"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            packet_path.unlink(missing_ok=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--require-critics requires", result.stderr)

    def test_prime_display_name_source_id_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["accepted_findings"][0]["source_ids"] = ["Guardian Owl:GO-001"]
        result = self.run_validator(packet, "prime")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid source_id", result.stderr)

    def test_prime_with_critics_requires_full_accounting(self):
        critic = copy.deepcopy(VALID_CRITIC)
        critic["findings"].append(
            {
                "id": "E2",
                "severity": "non_blocking",
                "category": "testability",
                "issue": "A second finding needs accounting.",
                "evidence": "The critic packet contains logic_owl:E2.",
                "impact": "Prime Owl must accept, merge, or reject every source finding.",
                "suggested_fix": "Account for logic_owl:E2.",
                "confidence": "high",
            }
        )
        result = self.run_prime_with_critics(VALID_PRIME, [critic])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing critic findings logic_owl:E2", result.stderr)

    def test_prime_with_critics_rejects_unknown_source_id(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"] = []
        packet["accepted_findings"][0]["source_ids"] = ["Euclid:E1"]
        result = self.run_prime_with_critics(packet, [VALID_CRITIC])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown critic findings Euclid:E1", result.stderr)

    def test_prime_with_critics_accepts_stable_role_ids(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"] = []
        result = self.run_prime_with_critics(packet, [VALID_CRITIC])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Source accounting was not checked", result.stdout)

    def test_prime_with_duplicate_critic_roles_fails(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"] = []
        result = self.run_prime_with_critics(packet, [VALID_CRITIC, copy.deepcopy(VALID_CRITIC)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate critic role 'logic_owl'", result.stderr)

    def test_standard_mode_requires_logic_and_proof(self):
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"] = []
        result = self.run_prime_with_critics(packet, [VALID_CRITIC], mode="standard")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode standard: missing critic roles proof_owl", result.stderr)

    def test_standard_mode_accepts_exact_reviewer_set(self):
        logic = copy.deepcopy(VALID_CRITIC)
        proof = copy.deepcopy(VALID_CRITIC)
        proof["role"] = "proof_owl"
        proof["findings"][0]["id"] = "P1"
        packet = copy.deepcopy(VALID_PRIME)
        packet["rejected_findings"] = [
            {
                "source_ids": ["proof_owl:P1"],
                "reason": "low_value",
                "explanation": "The finding is valid but not useful for this change.",
            }
        ]
        result = self.run_prime_with_critics(packet, [logic, proof], mode="standard")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lite_mode_rejects_critic_packets(self):
        packet = prime_packet("pass", [])
        result = self.run_prime_with_critics(packet, [VALID_CRITIC], mode="lite")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode lite: unexpected critic roles logic_owl", result.stderr)

    def test_security_mode_accepts_guardian_only(self):
        guardian = copy.deepcopy(VALID_CRITIC)
        guardian["role"] = "guardian_owl"
        result = self.run_prime_with_critics(prime_packet("pass", []), [{**guardian, "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}], mode="security")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_security_mode_rejects_extra_logic_role(self):
        logic = {"role": "logic_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        guardian = {"role": "guardian_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        result = self.run_prime_with_critics(prime_packet("pass", []), [guardian, logic], mode="security")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode security: unexpected critic roles logic_owl", result.stderr)

    def test_full_mode_rejects_missing_guardian(self):
        logic = {"role": "logic_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        proof = {"role": "proof_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        result = self.run_prime_with_critics(prime_packet("pass", []), [logic, proof], mode="full")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode full: missing critic roles guardian_owl", result.stderr)

    def test_full_mode_rejects_duplicate_role(self):
        logic = {"role": "logic_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        guardian = {"role": "guardian_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        proof = {"role": "proof_owl", "verdict": "pass", "findings": [], "notes": ["No meaningful issues found."]}
        result = self.run_prime_with_critics(prime_packet("pass", []), [logic, copy.deepcopy(logic), guardian, proof], mode="full")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate critic role 'logic_owl'", result.stderr)

    def test_mode_can_only_be_used_with_prime_packets(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--type",
                "critic",
                "--file",
                str(FIXTURES / "critic_valid_logic_pass.json"),
                "--mode",
                "standard",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--mode can only be used with --type prime", result.stderr)

    def test_fixture_packets_validate_as_documented(self):
        cases = [
            ("critic", "critic_guardian_owl_privacy.json", [], 0),
            ("critic", "critic_proof_owl_ci.json", [], 0),
            ("critic", "critic_valid_logic_pass.json", [], 0),
            ("critic", "critic_valid_proof_pass.json", [], 0),
            ("critic", "critic_valid_guardian_pass.json", [], 0),
            ("critic", "critic_invalid_pass_missing_notes.json", [], 1),
            ("critic", "critic_invalid_pass_empty_notes.json", [], 1),
            ("critic", "critic_invalid_pass_null_note.json", [], 1),
            ("critic", "critic_invalid_pass_blank_note.json", [], 1),
            ("critic", "critic_invalid_pass_non_string_note.json", [], 1),
            ("critic", "critic_invalid_pass_with_findings.json", [], 1),
            ("critic", "critic_invalid_concerns_empty.json", [], 1),
            ("critic", "critic_invalid_blocked_without_blocking.json", [], 1),
            ("critic", "critic_valid_blocked.json", [], 0),
            ("prime", "prime_pass.json", [], 0),
            ("prime", "prime_valid_pass_empty.json", [], 0),
            ("prime", "prime_invalid_pass_missing_required_fields.json", [], 1),
            ("prime", "prime_invalid_pass_critic_style.json", [], 1),
            ("prime", "prime_caution.json", [], 0),
            ("prime", "prime_fix_required_privacy.json", [], 0),
            ("prime", "invalid_prime_fix_required_without_blocking.json", [], 1),
            ("prime", "invalid_prime_duplicate_source.json", [], 1),
            (
                "prime",
                "invalid_prime_missing_source_accounting.json",
                ["critic_guardian_owl_privacy.json", "critic_proof_owl_ci.json"],
                1,
            ),
            ("critic", "critic_current_guardian_owl_api_auth_and_storage.json", [], 0),
            ("critic", "critic_current_proof_owl_persistence_and_routes.json", [], 0),
            (
                "prime",
                "prime_valid_current_fix_required_api_auth_and_storage.json",
                ["critic_current_guardian_owl_api_auth_and_storage.json", "critic_current_proof_owl_persistence_and_routes.json"],
                0,
            ),
            (
                "prime",
                "prime_invalid_stale_source_ids_and_verdict_mismatch.json",
                ["critic_current_guardian_owl_api_auth_and_storage.json", "critic_current_proof_owl_persistence_and_routes.json"],
                1,
            ),
            ("prime", "prime_invalid_critic_schema_instead_of_prime_schema.json", [], 1),
            ("critic", "critic_release_logic_owl.json", [], 0),
            ("critic", "critic_release_guardian_owl.json", [], 0),
            ("critic", "critic_release_proof_owl.json", [], 0),
            (
                "prime",
                "prime_valid_split_docs_security_and_release_hygiene.json",
                ["critic_release_logic_owl.json", "critic_release_guardian_owl.json", "critic_release_proof_owl.json"],
                0,
            ),
        ]
        for packet_type, packet_name, critic_names, expected in cases:
            command = [sys.executable, str(SCRIPT), "--type", packet_type, "--file", str(FIXTURES / packet_name)]
            if critic_names:
                command.extend(["--critics", *[str(FIXTURES / name) for name in critic_names]])
            with self.subTest(packet_name=packet_name):
                result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
                if expected == 0:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_overmerge_fixture_documents_bad_pattern(self):
        bad = json.loads((FIXTURES / "prime_invalid_overmerged_docs_security_finding.json").read_text())
        good = json.loads((FIXTURES / "prime_valid_split_docs_security_and_release_hygiene.json").read_text())
        self.assertEqual(bad["accepted_findings"][0]["source_ids"], ["guardian_owl:G-001", "proof_owl:P-003"])
        self.assertEqual(bad["accepted_findings"][0]["severity"], "blocking")
        self.assertEqual(bad["accepted_findings"][0]["category"], "security")
        good_source_sets = [set(finding["source_ids"]) for finding in good["accepted_findings"]]
        self.assertIn({"guardian_owl:G-001"}, good_source_sets)
        self.assertIn({"proof_owl:P-003", "logic_owl:L-003"}, good_source_sets)

    def test_demo_transcript_packets_validate(self):
        transcript = (ROOT / "docs" / "demo-transcript.md").read_text(encoding="utf-8")
        packets = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", transcript, re.DOTALL)]
        self.assertEqual(len(packets), 3)

        spec = importlib.util.spec_from_file_location("demo_packet_validator", SCRIPT)
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        critics = packets[:2]
        for packet in critics:
            self.assertEqual(validator.validate_critic(packet), [])
        self.assertEqual(
            validator.validate_prime(packets[2], critics, validator.MODE_ROLES["standard"], "standard"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
