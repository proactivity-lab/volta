#!/usr/bin/env python
"""voltasimulator.py: Generate some graphs"""

import sys
import time
import json
import math
import threading
import nanomsg


__author__ = "Raido Pahtma"
__license__ = "MIT"


class SimulationThread(threading.Thread):

    def __init__(self):
        super(SimulationThread, self).__init__()
        self.interrupted = False

        self.soc_pub = nanomsg.Socket(nanomsg.PUB)
        self.soc_pub.bind("tcp://*:12345")

    def run(self):
        while not self.interrupted:
            t = time.time()
            m = {"t": t, "data": {"1": 10 * math.sin(t),
                                  "2": 10 * math.cos(t),
                                  "3": 5 * (math.cos(t) - math.sin(t)),
                                  "4": 5 * (math.tan(t))}}
            msg = json.dumps(m)
            print(msg)
            self.soc_pub.send(msg)
            time.sleep(0.01)

    def join(self, timeout=None):
        self.interrupted = True
        super(SimulationThread, self).join(timeout)
        print("sim done")


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Voltaplot")
    parser.add_argument("--filename", default=None)
    args = parser.parse_args()

    sim = SimulationThread()
    sim.start()

    logfile = None
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("interrupted")
        if logfile is not None:
            logfile.close()
        sys.stdout.flush()

        sim.join()


if __name__ == "__main__":
    main()
