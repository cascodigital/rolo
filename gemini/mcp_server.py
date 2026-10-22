import os
import subprocess
import json
import sys

# Base paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable
UPDATE_SH = os.path.join(PROJECT_ROOT, "rolo_update.sh")
ANALYZE_PY = os.path.join(PROJECT_ROOT, "analyze_music_dna.py")
CURATE_PY = os.path.join(PROJECT_ROOT, "rolo_curate.py")
CREATE_PY = os.path.join(PROJECT_ROOT, "scripts", "create_work_playlist.py")

def run_command(command, is_shell=False):
    try:
        result = subprocess.run(command, shell=is_shell, capture_output=True, text=True)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def main():
    # Simplified stdio server: reads one JSON request per line and replies with one JSON line.
    # Can later be migrated to the official MCP SDK.
    print("Rolo MCP Server Active. Ready for commands.", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line)
            method = request.get("method")
            
            if method == "rolo.sync":
                response = run_command(["bash", UPDATE_SH, "--force"])
            elif method == "rolo.analyze":
                response = run_command([VENV_PYTHON, ANALYZE_PY])
            elif method == "rolo.context":
                response = run_command([VENV_PYTHON, CURATE_PY, "context"])
            elif method == "rolo.create_playlist":
                response = run_command([VENV_PYTHON, CREATE_PY])
            else:
                response = {"error": "Method not found"}
            
            print(json.dumps({"id": request.get("id"), "result": response}))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
