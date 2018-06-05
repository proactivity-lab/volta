#!/usr/bin/env python
"""voltacsv.py: csv writer tool"""
import csv
import json

import errno
import nanomsg


__author__ = "Raido Pahtma"
__license__ = "MIT"


class VoltaWriter(object):

    def __init__(self, source, elements, output):
        self.source = source
        self.elements = elements
        self.output = output

        self.interrupted = False

        self.soc_sub = nanomsg.Socket(nanomsg.SUB)

    def run(self):
        self.soc_sub.set_string_option(nanomsg.SUB, nanomsg.SUB_SUBSCRIBE, "")
        self.soc_sub.set_int_option(nanomsg.SOL_SOCKET, nanomsg.RECONNECT_IVL, 1000)
        self.soc_sub.set_int_option(nanomsg.SOL_SOCKET, nanomsg.RECONNECT_IVL_MAX, 1000 * 30)
        self.soc_sub.connect(self.source)

        csvfile = open(self.output, 'wb')
        wrt = csv.DictWriter(csvfile, fieldnames=self.elements,
                             extrasaction="ignore",
                             delimiter=',',
                             quotechar='"', quoting=csv.QUOTE_MINIMAL)
        wrt.writeheader()

        while not self.interrupted:
            try:
                msg = self.soc_sub.recv()
                msg = json.loads(msg)
                t = msg["t"]
                datapoint = msg["data"]

                print("{} {}".format(t, datapoint))
                datapoint["timestamp"] = t
                wrt.writerow(datapoint)

            except nanomsg.NanoMsgAPIError as e:
                if e.errno == errno.EAGAIN:
                    break
                else:
                    raise
            except KeyboardInterrupt:
                break

        csvfile.close()


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Voltaplot")
    parser.add_argument("--header", default="header.csv", help="CSV file header example")
    parser.add_argument("--source", default="tcp://localhost:12345", help="Nanomessage publisher URL")
    parser.add_argument("--output", default="output.csv", help="CSV output file")
    args = parser.parse_args()

    with open(args.header) as f:
        header = map(lambda x: x.rstrip().lstrip(), f.read().split(","))

    wrtr = VoltaWriter(args.source, header, args.output)
    wrtr.run()

    print("exit")


if __name__ == "__main__":
    main()
