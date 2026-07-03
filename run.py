"""
start application
initialize components
run development server
suppress tensorflow warnings
"""

import sys
import time
from pathlib import Path
import os
import warnings


# ================ ENV SETUP ================

# suppress tensorflow completely before any imports
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

# suppress library warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*")
warnings.filterwarnings("ignore", message=".*sentencepiece.*")


# ================ PATH SETUP ================

# add project root to python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# import flask app factory
from frontend.flaskr import create_app


# ================ STARTUP ================

if __name__ == "__main__":
    # print startup header
    print("\n" + "=" * 70)
    print("company_profiler SYSTEM STARTUP")
    print("=" * 70 + "\n")

    # track initialization time
    start_time = time.time()

    # create flask application
    app = create_app("production")

    # retrieve components
    comps = app.components

    # calculate initialization time
    init_time = time.time() - start_time

    # print component status
    print("=" * 70)
    print("COMPONENT STATUS")
    print("=" * 70 + "\n")

    # define component keys to check
    components_to_check = {
        "profiles db": "profiles_db",
        "document store": "doc_store",
        "pipeline": "pipeline",
    }

    for name, key in components_to_check.items():
        # compute status label
        status = "[OK]" if comps.get(key) else "[FAIL]"
        print(f"{name:<19}{status}")

    print(f"\nstartup time: {init_time:.2f}s")
    print("server: http://localhost:5000")
    print("press Ctrl+C to shutdown")
    print("=" * 70 + "\n")

    # start periodic seeder
    from backend.configuration.seeding import SEED_SCHEDULER_ENABLED
    if SEED_SCHEDULER_ENABLED:
        from backend.data.seeder.scheduler import start_scheduler
        start_scheduler()

    # run flask server
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)