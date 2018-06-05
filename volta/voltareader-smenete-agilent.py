#!/usr/bin/env python
"""voltareader-smenete-agilent.py: Specific test case with Agilen U2354A and smenete board."""

import sys
import time
import json
import threading
import nanomsg

import visa


class ReaderThread(threading.Thread):

    def __init__(self):
        super(ReaderThread, self).__init__()
        self.inst = None
        self.interrupted = False

        self.soc_pub = nanomsg.Socket(nanomsg.PUB)
        self.soc_pub.bind("tcp://*:12345")

    def setup(self, resource):
        rm = visa.ResourceManager("@py")
        print(rm.list_resources())

        self.inst = rm.open_resource(resource)

        print(self.inst.query("*IDN?"))

        print(self.inst.query("SENS:VOLT:RANG? (@101:108)"))
        print(self.inst.write("*RST;*CLS"))
        print(self.inst.query("SENS:VOLT:RANG? (@101:108)"))
        print(self.inst.write("SENS:VOLT:RANG 1.25, (@101)"))  # BAT current
        print(self.inst.write("SENS:VOLT:RANG 5, (@102)"))     # BAT voltage
        print(self.inst.write("SENS:VOLT:RANG 1.25, (@103)"))  # 3V3 current
        print(self.inst.write("SENS:VOLT:RANG 5, (@104)"))     # 3V3 voltage
        print(self.inst.write("SENS:VOLT:RANG 1.25, (@105)"))  # 5V  current
        # print(self.inst.write("SENS:VOLT:RANG 1.25, (@106)"))  # 5V  current
        print(self.inst.write("SENS:VOLT:RANG 10, (@107)"))    # 5V  voltage
        print(self.inst.write("SENS:VOLT:RANG 1.25, (@108)"))  # Solar current
        print(self.inst.write("SENS:VOLT:RANG 5, (@110)"))     # CHRG
        print(self.inst.write("SENS:VOLT:RANG 10, (@112)"))    # Solar voltage
        print(self.inst.write("SENS:VOLT:RANG 5, (@115)"))     # FAULT
        print(self.inst.query("SENS:VOLT:RANG? (@101:108,110,112,115)"))

        print(self.inst.write("SENS:VOLT:STYP DIFF, (@101)"))
        print(self.inst.write("SENS:VOLT:STYP DIFF, (@103)"))
        print(self.inst.write("SENS:VOLT:STYP DIFF, (@105)"))
        # print(self.inst.write("SENS:VOLT:STYP DIFF, (@106)"))
        print(self.inst.write("SENS:VOLT:STYP DIFF, (@108)"))

        print(self.inst.query("ACQ:SRAT?"))  # ACQuire:SRATe?
        # print(self.inst.write("ACQ:SRAT 1000"))

        print(self.inst.query("ACQ:POIN?"))  # Samples per measurement?
        # print(self.inst.write("ACQ:POIN 500"))
        # print(self.inst.query("ACQ:POIN?"))

        print(self.inst.write("ROUT:SCAN (@101:106,107,108,110,112,115)"))

        # print(self.inst.write("ACQ:SRAT 500;:ACQ:POIN 1;:DIG"))
        # values = inst.query("WAV:DATA?")
        # print(self.inst.write("WAV:DATA?"))
        # values = self.inst.read_raw()
        # print(values[:10])
        # print(values[10:].encode("hex"))

    def run(self):
        while not self.interrupted:
            results = self.inst.write("MEAS:VOLT? (@101:105,107,108,110,112,115)")
            # print time.time(), results
            results = self.inst.read()
            # print time.time(), results
            data = map(lambda x: float(x), results.rstrip("\0").rstrip().split(","))
            # print(data)

            t = time.time()
            m = {"t": t, "data": {"BatI": (data[0]/0.1)*1000,
                                  "BatV": data[1],
                                  "3V3I": (data[2]/0.1)*1000,
                                  "3V3":  data[3],
                                  "5VI":  (data[4]/0.1)*1000,
                                  "5V":   data[5],
                                  "SolarI": (data[6]/0.1)*1000,
                                  "CHRG": data[7],
                                  "SolarV": data[8]*3,
                                  "FAULT": data[9]}}
            msg = json.dumps(m)
            # print(msg)
            self.soc_pub.send(msg)

    def join(self, timeout=None):
        self.interrupted = True
        super(ReaderThread, self).join(timeout)
        print("sim done")


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Voltareader")
    parser.add_argument("--instrument", default="USB0::0x0957::0x1218::TW49241595::INSTR", help="Instrument string")
    args = parser.parse_args()

    rdr = ReaderThread()
    rdr.setup(args.instrument)
    rdr.start()

    logfile = None
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("interrupted")
        if logfile is not None:
            logfile.close()
        sys.stdout.flush()

        rdr.join()


if __name__ == "__main__":
    main()
