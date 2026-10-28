import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _rpc(proc: subprocess.Popen[str], payload: dict) -> dict | None:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    if payload.get("id") is None:
        return None
    line = proc.stdout.readline()
    if not line:
        raise AssertionError(f"server closed stdout; stderr={proc.stderr.read() if proc.stderr else ''}")
    return json.loads(line)


class McpTests(unittest.TestCase):
    def test_initialize_list_and_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["FFEMPEG_CACHE_DIR"] = str(Path(tmp) / "in")
            env["FFEMPEG_OUTPUT_DIR"] = str(Path(tmp) / "out")
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "ffempeg" / "mcp_server.py")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=ROOT,
                env=env,
            )
            try:
                init = _rpc(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "0"},
                        },
                    },
                )
                self.assertEqual(init["result"]["serverInfo"]["name"], "ffempeg")
                _rpc(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
                listed = _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                names = {tool["name"] for tool in listed["result"]["tools"]}
                self.assertIn("probe_media", names)
                self.assertIn("make_gif", names)
                checked = _rpc(
                    proc,
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "check_ffmpeg", "arguments": {}}},
                )
                body = json.loads(checked["result"]["content"][0]["text"])
                self.assertIn("ffmpeg", body["version"].lower())
                self.assertFalse(checked["result"]["isError"])
                missing = _rpc(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {"name": "probe_media", "arguments": {"source": "no-such-file.m4v"}},
                    },
                )
                self.assertTrue(missing["result"]["isError"])
            finally:
                if proc.stdin:
                    proc.stdin.close()
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
