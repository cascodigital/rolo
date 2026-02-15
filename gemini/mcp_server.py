import os
import subprocess
import json
import sys

# Caminhos base
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")
UPDATE_SH = os.path.join(PROJECT_ROOT, "utils", "update_database.sh")
ANALYZE_PY = os.path.join(PROJECT_ROOT, "analysis", "analyze_music_dna.py")
CREATE_PY = os.path.join(PROJECT_ROOT, "scripts", "create_work_playlist.py")

def run_command(command, is_shell=False):
    try:
        result = subprocess.run(command, shell=is_shell, capture_output=True, text=True)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def main():
    # Este é um servidor MCP simplificado que responde a comandos via stdio
    # No futuro, pode ser expandido usando a SDK oficial do MCP
    print("Rolo MCP Server Active. Ready for commands.", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line)
            method = request.get("method")
            
            if method == "rolo.sync":
                response = run_command([UPDATE_SH])
            elif method == "rolo.analyze":
                response = run_command([VENV_PYTHON, ANALYZE_PY])
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
