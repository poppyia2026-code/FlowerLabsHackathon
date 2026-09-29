"""Regression coverage for real transport boundaries and explicit chat review."""
from __future__ import annotations

import copy
import json
import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from poppy_orchestrator.agent_app import main
from poppy_orchestrator.clients.grid_clients import GridHospitalCredClient
from poppy_orchestrator.contracts.claims import ClaimRequest, ProviderRef
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid, FakeGridNode
from poppy_orchestrator.live_runtime import STATE_KEY
from poppy_orchestrator.supernodes.runtime import serve_runtime_instruction

ROOT = Path(__file__).resolve().parents[1]


def request():
    return ClaimRequest('request-1', ProviderRef('SYNTH-NPI-1888888888', 'SYNTH-NETWORK-X'),
                        ('work_history_complete', 'board_status'), 'HospitalCred')


class TamperedGrid(FakeAgentGrid):
    def __init__(self, mutate):
        super().__init__()
        self.mutate = mutate

    def _pull_messages(self, message_ids, timeout=0):
        result = super()._pull_messages(message_ids, timeout)
        self.mutate(result['messages'][0])
        return result


class TransportTests(unittest.TestCase):
    def test_pending_reply_never_uses_local_fixture(self):
        response = GridHospitalCredClient(FakeAgentGrid(_auto_reply=False)).request_claims(request())
        self.assertFalse(response.ok)
        self.assertEqual(response.claims, ())

    def test_other_provider_is_rejected(self):
        def mutate(message):
            payload = json.loads(message['payload'])
            payload['provider_id'] = 'SYNTH-NPI-1999999999'
            message['payload'] = json.dumps(payload)
        self.assertFalse(GridHospitalCredClient(TamperedGrid(mutate)).request_claims(request()).ok)

    def test_wrong_reply_metadata_is_rejected(self):
        for field, value in [('src_node_id', 'wrong-node'), ('reply_to_message_id', 'wrong-message'),
                             ('error', 'worker failed')]:
            with self.subTest(field=field):
                grid = TamperedGrid(lambda message: message.update({field: value}))
                self.assertFalse(GridHospitalCredClient(grid).request_claims(request()).ok)

    def test_wrong_payload_identity_is_rejected(self):
        for field, value in [('request_id', 'other-request'), ('source_node', 'PayerEnrollment'),
                             ('synthetic', 'false'), ('ok', 'true')]:
            with self.subTest(field=field):
                def mutate(message):
                    payload = json.loads(message['payload'])
                    payload[field] = value
                    message['payload'] = json.dumps(payload)
                self.assertFalse(GridHospitalCredClient(TamperedGrid(mutate)).request_claims(request()).ok)

    def test_ambiguous_or_similar_node_names_are_rejected(self):
        for nodes in ([FakeGridNode('1', 'UntrustedHospitalCred')],
                      [FakeGridNode('1', 'HospitalCred'), FakeGridNode('2', 'HospitalCred')]):
            self.assertFalse(GridHospitalCredClient(FakeAgentGrid(nodes=nodes)).request_claims(request()).ok)

    def test_requested_provider_is_preserved(self):
        response = GridHospitalCredClient(FakeAgentGrid()).request_claims(request())
        self.assertTrue(response.ok)
        self.assertEqual(response.request_id, 'request-1')
        self.assertEqual(response.provider_id, request().provider.provider_id)
        self.assertFalse(response.get('work_history_complete').value)


class Events:
    def __init__(self):
        self.items = []

    def emit(self, item):
        if not isinstance(item.get('type'), str) or not item['type']:
            raise ValueError("Flower requires a non-empty event type")
        self.items.append(item)


class ReplyGrid:
    def __init__(self, error=False):
        self.reply = None
        self.error = error

    def tools(self):
        return [{'name': 'push_reply_message'}]

    def call(self, item):
        if item['name'] != 'push_reply_message':
            raise AssertionError('SuperNode attempted to initiate orchestration')
        self.reply = json.loads(item['arguments']['payload'])
        return {'output': json.dumps({'message_id': None if self.error else 'reply-1',
                                      'error': 'offline' if self.error else None})}


class WorkerTests(unittest.TestCase):
    def make_context_and_agent(self):
        data = {'provider_id': 'SYNTH-NPI-1888888888', 'network_id': 'SYNTH-NETWORK-X',
                'request_id': 'request-1', 'to': 'HospitalCred', 'synthetic': True,
                'intent': 'request_verification_claims',
                'claim_types': ['work_history_complete', 'board_status']}
        agent = SimpleNamespace(grid=ReplyGrid(), events=Events(),
                                prompt=json.dumps({'message_id': 'instruction-1', 'src_node_id': '1',
                                                   'payload': json.dumps(data)}))
        context = SimpleNamespace(node_config={'poppy-role': 'HospitalCred',
                                  'poppy-data': str(ROOT / 'fixtures/supernodes/HospitalCred/providers.json')},
                                  state={}, run_config={})
        return context, agent

    def test_same_fab_dispatches_to_worker_with_real_prompt_envelope(self):
        context, agent = self.make_context_and_agent()
        main(agent, context)
        self.assertEqual(agent.grid.reply['provider_id'], 'SYNTH-NPI-1888888888')
        self.assertEqual(agent.grid.reply['request_id'], 'request-1')
        self.assertFalse(next(c for c in agent.grid.reply['claims']
                              if c['claim_type'] == 'work_history_complete')['value'])

    def test_no_inbound_message_does_not_return_default_provider(self):
        context, agent = self.make_context_and_agent()
        agent.prompt = ''
        with self.assertRaises(ValueError):
            serve_runtime_instruction(agent, context)
        self.assertIsNone(agent.grid.reply)

    def test_local_role_cannot_be_overridden_by_message(self):
        context, agent = self.make_context_and_agent()
        context.node_config['poppy-role'] = 'PayerEnrollment'
        with self.assertRaises(ValueError):
            serve_runtime_instruction(agent, context)
        self.assertIsNone(agent.grid.reply)

    def test_local_shard_is_required(self):
        context, agent = self.make_context_and_agent()
        context.node_config.pop('poppy-data')
        with self.assertRaises(ValueError):
            serve_runtime_instruction(agent, context)

    def test_reply_failure_is_not_swallowed(self):
        context, agent = self.make_context_and_agent()
        agent.grid.error = True
        with self.assertRaises(RuntimeError):
            serve_runtime_instruction(agent, context)


class ChatReviewTests(unittest.TestCase):
    def setUp(self):
        from flwr.app import Context, RecordDict
        self.context = Context(run_id=100, node_id=1, node_config={}, state=RecordDict(),
                               run_config={'grid-pull-timeout': 1})
        self.agent = SimpleNamespace(grid=FakeAgentGrid(), events=Events(),
                                      prompt='Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X')
        self.env = patch.dict(os.environ, {'ENDEAVOR_ENABLED': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def record(self):
        return json.loads(self.context.state[STATE_KEY]['json'])

    def test_first_turn_waits_and_second_turn_uses_exact_reviewed_bundle(self):
        with patch('poppy_orchestrator.agent_app.build_stub_clients', side_effect=AssertionError):
            main(self.agent, self.context)
        self.assertEqual(self.record()['status'], 'pending')
        self.assertFalse(any(e.get('event') == 'privcred.claim_receipt' for e in self.agent.events.items))
        grid_calls = len(self.agent.grid.events)
        self.context.run_id = 101
        self.agent.prompt = '/approve run-100'
        main(self.agent, self.context)
        self.assertEqual(self.record()['result']['outcome'], 'credentialed')
        self.assertEqual(self.record()['result']['run_id'], 'run-100')
        self.assertEqual(len(self.agent.grid.events), grid_calls)
        self.assertEqual(self.agent.events.items[-1], {'type': 'response.completed'})

    def test_human_decisions_are_not_automatic(self):
        for action, outcome in [('escalate', 'escalated'), ('reject', 'rejected')]:
            with self.subTest(action=action):
                self.context.state.clear()
                self.agent.prompt = 'Verify SYNTH-NPI-1888888888'
                main(self.agent, self.context)
                self.agent.prompt = f'/{action} run-100 operator explanation'
                main(self.agent, self.context)
                self.assertEqual(self.record()['result']['outcome'], outcome)
                self.assertIsNone(self.record()['result']['receipt'])

    def test_auto_approval_config_rejected(self):
        self.context.run_config['hitl-auto-approve-dry-run'] = 'true'
        with self.assertRaises(ValueError):
            main(self.agent, self.context)
        self.assertEqual(self.agent.grid.events, [])

    def test_wrong_review_id_and_replayed_decision_do_not_issue_receipts(self):
        main(self.agent, self.context)
        pending = copy.deepcopy(self.record())
        self.agent.prompt = '/approve wrong-id'
        main(self.agent, self.context)
        self.assertEqual(self.record(), pending)
        self.agent.prompt = '/approve run-100'
        main(self.agent, self.context)
        completed = copy.deepcopy(self.record())
        main(self.agent, self.context)
        self.assertEqual(self.record(), completed)

    def test_missing_node_cannot_credential_even_when_approved(self):
        self.agent.grid = FakeAgentGrid(_auto_reply=False)
        main(self.agent, self.context)
        self.agent.prompt = '/approve run-100'
        main(self.agent, self.context)
        self.assertEqual(self.record()['result']['outcome'], 'failed')

    def test_expired_review_requires_new_verification(self):
        main(self.agent, self.context)
        record = self.record()
        record['bundle']['collected_at'] = time.time() - 700
        self.context.state[STATE_KEY]['json'] = json.dumps(record)
        self.agent.prompt = '/approve run-100'
        main(self.agent, self.context)
        self.assertEqual(self.record()['status'], 'expired')

    def test_missing_grid_never_falls_back(self):
        self.agent.grid = None
        with self.assertRaises(RuntimeError):
            main(self.agent, self.context)
