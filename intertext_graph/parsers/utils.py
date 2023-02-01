from multiprocessing import cpu_count
from sys import platform
import subprocess


def chunksize(total: int) -> int:
    max_chunksize = 16  # Balance chunksize for context switches and imbalances in processing time of instances
    processes = num_processes()
    return max(1, min(max_chunksize, total // processes))  # Reduce amount of context switches


def num_processes() -> int:
    if platform == 'darwin':
        # On macOS return number of performance cores
        # Otherwise performance cores are throttled to efficiency core speed
        try:
            stdout = subprocess.run(['sysctl', 'hw.perflevel0.physicalcpu'], capture_output=True).stdout
            processes = int(stdout.split()[-1])
            if processes > 0:
                return processes
        except (IndexError, ValueError):
            # If there were no performance cores detected fall back to cpu count
            pass
    return cpu_count()
