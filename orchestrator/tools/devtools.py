import os, grpc
from . import devtools_pb2 as pb          # ← note the leading dot
from . import devtools_pb2_grpc as rpc    # ← relative import

_channel = grpc.insecure_channel(os.getenv("DEVTOOLS_ENDPOINT").replace("tcp://",""))
_stub = rpc.DevToolsStub(_channel)

def write_file(path:str, content:str)->str:
    _stub.WriteFile(pb.WriteFileRequest(path=path, content=content))
    return f"wrote {path}"

def run_shell(cmd:str)->str:
    r = _stub.RunShell(pb.ShellRequest(cmd=cmd))
    return r.stdout + r.stderr
