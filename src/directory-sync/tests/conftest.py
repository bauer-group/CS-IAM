import pathlib
import sys

# Make the flat `src/` modules importable as top-level (config, graph, jobs, ...).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
