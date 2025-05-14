import os
import grpc
from . import devtools_pb2 as pb          # relative import
from . import devtools_pb2_grpc as rpc    # relative import

# establish a channel to your DevTools daemon
# DEVTOOLS_ENDPOINT should be something like "tcp://host:port"
_endpoint = os.getenv("DEVTOOLS_ENDPOINT", "tcp://localhost:17764")
_channel = grpc.insecure_channel(_endpoint.replace("tcp://", ""))
_stub = rpc.DevToolsStub(_channel)

def write_file(path: str, content: str) -> str:
    """
    RPC call to write a file on disk.
    Returns a human-readable confirmation.
    """
    _stub.WriteFile(pb.WriteFileRequest(path=path, content=content))
    return f"wrote {path}"

def run_shell(cmd: str) -> str:
    """
    RPC call to run a shell command.
    Returns combined stdout+stderr.
    """
    resp = _stub.RunShell(pb.ShellRequest(cmd=cmd))
    return resp.stdout + resp.stderr
