import uvicorn
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    print("=" * 50)
    print("IDX Stock Analyzer")
    print("=" * 50)
    print("Server starting at http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
