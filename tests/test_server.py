import json
import threading
from http.client import HTTPConnection

from signalforge.server import SignalForgeHandler
from signalforge.store import TraceStore
from http.server import ThreadingHTTPServer


def test_health_and_evaluate_api(tmp_path):
    SignalForgeHandler.store = TraceStore(tmp_path / "test.db")
    server = ThreadingHTTPServer(("127.0.0.1", 0), SignalForgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        connection.request("GET", "/health")
        assert connection.getresponse().status == 200
        payload = {"trace_id": "api-1", "input": "Hi", "output": "Hello", "model": "test"}
        connection.request("POST", "/api/evaluate", body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 200
        assert json.loads(response.read())["results"][0]["trace_id"] == "api-1"
    finally:
        server.shutdown()
        server.server_close()
        SignalForgeHandler.store.close()
