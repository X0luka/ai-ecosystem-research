import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import quality_gate as gate


class FaultTests(unittest.TestCase):
    def test_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(gate,'source_hash',return_value='snapshot'):
            folder = Path(tmp)
            plan = dict(problem='gap',limits='scope',evidence='output',counterexamples=['missing input'],
                        methods=dict.fromkeys(gate.AREAS,'execute'),criteria=dict.fromkeys(gate.AREAS,'observe'))
            gate.write(folder/'plan.json',plan)
            gate.start(folder)
            evidence = folder/'observation'
            evidence.write_text('actual')
            for area in gate.AREAS:
                gate.record(folder,area,[sys.executable,'-c','print(42)'],[evidence])
            gate.verify(folder)
            with self.assertRaises(ValueError):
                gate.record(folder,'effectiveness',[sys.executable,'-V'],[])
            with self.assertRaises(FileNotFoundError):
                gate.verify(folder)
            gate.record(folder,'effectiveness',[sys.executable,'-c','raise SystemExit(1)'],[evidence])
            with self.assertRaises(ValueError):
                gate.verify(folder)
            gate.record(folder,'effectiveness',[sys.executable,'-V'],[evidence])
            evidence.write_text('changed')
            with self.assertRaises(ValueError):
                gate.verify(folder)
            evidence.write_text('actual')
            with patch.object(gate,'source_hash',return_value='changed-source'), self.assertRaises(ValueError):
                gate.verify(folder)
            gate.write(folder/'plan.json',dict(plan,limits='relaxed'))
            with self.assertRaises(ValueError):
                gate.verify(folder)


if __name__ == '__main__':
    unittest.main()
