from pathlib import Path
import sys
from himena_relion.external import run_function
from himena_relion.pipeline_watcher import run_watcher


def main():
    argv = sys.argv[1:]
    if argv[0] == "watch":
        if len(argv) < 2:
            relion_dir = Path.cwd()
        else:
            relion_dir = Path(argv[1])
        locked_ok = False
        if len(argv) > 2 and argv[2] == "--lock-ok":
            locked_ok = True
        run_watcher(relion_dir=relion_dir, locked_ok=locked_ok)
    else:
        run_function()


if __name__ == "__main__":
    # `python -m himena_relion watch ...` (see `run_watcher_new_process`)
    main()
