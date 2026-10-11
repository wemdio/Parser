import subprocess
import unittest
from unittest.mock import Mock, patch

from backend.process_supervisor import Supervisor, api_responds, stop_child


class ProbeTests(unittest.TestCase):
    def test_probe_requires_successful_health_response(self):
        for status, body, expected in [(200, b'{"status":"ok"}', True),
                                       (503, b'{"status":"ok"}', False),
                                       (200, b'{"status":"degraded"}', False),
                                       (200, b'[]', False),
                                       (200, b'not json', False)]:
            with self.subTest(status=status, body=body):
                connection = Mock()
                connection.getresponse.return_value.status = status
                connection.getresponse.return_value.read.return_value = body
                with patch('backend.process_supervisor.http.client.HTTPConnection', return_value=connection):
                    self.assertEqual(api_responds(), expected)
                connection.close.assert_called_once()

    def test_timeout_closes_connection(self):
        connection = Mock()
        connection.request.side_effect = TimeoutError()
        with patch('backend.process_supervisor.http.client.HTTPConnection', return_value=connection):
            self.assertFalse(api_responds())
        connection.close.assert_called_once()


class StopTests(unittest.TestCase):
    def test_shutdown_escalates_only_after_grace_period(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('api', 20), 0]
        stop_child(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()

    def test_exited_child_is_not_signalled(self):
        child = Mock()
        child.poll.return_value = 1
        stop_child(child, diagnose=True)
        child.send_signal.assert_not_called()
        child.terminate.assert_not_called()


class SupervisorTests(unittest.TestCase):
    def run_sequence(self, probes, polls=None, grace=0):
        supervisor = Supervisor(['fake'], startup_grace=grace)
        child = Mock(pid=42, returncode=1)
        child.poll.side_effect = polls or [None] * (len(probes) + 1)
        event = Mock()
        event.is_set.side_effect = [False, False, True]
        event.wait.side_effect = [False] * len(probes) + [True, False]
        supervisor.stopping = event
        with patch('backend.process_supervisor.subprocess.Popen', return_value=child) as spawn, \
             patch('backend.process_supervisor.api_responds', side_effect=probes) as probe, \
             patch('backend.process_supervisor.stop_child') as stop:
            supervisor.run()
            return spawn, probe, stop

    def test_three_failures_restart_previously_healthy_process(self):
        _, _, stop = self.run_sequence([True, False, False, False])
        self.assertTrue(any(call.kwargs.get('diagnose') is True for call in stop.call_args_list))

    def test_success_resets_failure_counter(self):
        _, _, stop = self.run_sequence([True, False, False, True, False, False])
        self.assertEqual(len(stop.call_args_list), 1)

    def test_startup_grace_avoids_restart(self):
        _, _, stop = self.run_sequence([False] * 4, grace=3600)
        self.assertEqual(len(stop.call_args_list), 1)

    def test_startup_failure_eventually_restarts(self):
        _, _, stop = self.run_sequence([False] * 3)
        self.assertEqual(len(stop.call_args_list), 2)
        self.assertFalse(stop.call_args_list[0].kwargs['diagnose'])

    def test_stop_signal_sets_shutdown_event(self):
        supervisor = Supervisor(['fake'])
        supervisor.request_stop()
        self.assertTrue(supervisor.stopping.is_set())

    def test_crashed_process_is_replaced_and_shutdown_stops_replacement(self):
        supervisor = Supervisor(['fake'])
        crashed = Mock(pid=1, returncode=1)
        crashed.poll.return_value = 1
        replacement = Mock(pid=2)
        event = Mock()
        event.is_set.side_effect = [False, False, False, True, True]
        event.wait.side_effect = [False, False, True]
        supervisor.stopping = event
        with patch('backend.process_supervisor.subprocess.Popen', side_effect=[crashed, replacement]) as spawn, \
             patch('backend.process_supervisor.stop_child') as stop:
            supervisor.run()
        self.assertEqual(spawn.call_count, 2)
        stop.assert_called_once_with(replacement)


if __name__ == '__main__':
    unittest.main()
