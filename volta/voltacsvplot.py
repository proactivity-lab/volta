#!/usr/bin/env python
"""voltaplot.py: plot tool for saved csv files"""

import csv
import json
import threading
import datetime
from matplotlib.dates import date2num
import matplotlib.dates as mdates

import numpy

from matplotlib import pyplot as plt

from six import iteritems, iterkeys

__author__ = "Raido Pahtma"
__license__ = "MIT"


class Plotting(threading.Thread):

    def __init__(self, source, conf, limits, steps):
        super(Plotting, self).__init__()
        self.interrupted = False

        self.source = source
        self.conf = conf
        self.limits = limits
        self.steps = steps

    def run(self):
        fig, ax = plt.subplots(1, 1)
        # ax.set_aspect('equal')
        # ax.hold(True)

        plt.show(False)
        plt.draw()

        t = 0

        # points = ax.plot(0, 0, 'o')[0]
        st = date2num(datetime.datetime.fromtimestamp(t))
        et = date2num(datetime.datetime.fromtimestamp(t + 3600))
        ax.set_xlim(st, et)
        ax.set_ylim(self.limits[0], self.limits[1])

        # Major ticks every 20, minor ticks every 5
        if self.limits[0] < 0 < self.limits[1]:
            # stp = int((self.limits[1] - self.limits[0]) / 10)
            stp = self.steps[0]
            neg = numpy.arange(0, -self.limits[0], stp)
            pos = numpy.arange(0, self.limits[1], stp)
            major_ticks = map(lambda x: -x, reversed(list(neg)))+list(pos)[1:]

            stp = self.steps[1]
            neg = numpy.arange(0, -self.limits[0], stp)
            pos = numpy.arange(0, self.limits[1], stp)
            minor_ticks = map(lambda x: -x, reversed(list(neg)))+list(pos)[1:]
        else:
            # stp = int((self.limits[1]-self.limits[0])/10)
            stp = self.steps[0]
            major_ticks = numpy.arange(self.limits[0], self.limits[1], stp)

            stp = self.steps[1]
            minor_ticks = numpy.arange(self.limits[0], self.limits[1], stp)

        print(major_ticks)

        # ax.set_xticks(major_ticks)
        # ax.set_xticks(minor_ticks, minor=True)

        ax.set_yticks(major_ticks)
        ax.set_yticks(minor_ticks, minor=True)

        ax.grid(which='both')
        # ax.grid(True)

        ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M:%S.%f')

        tdata = [0]
        xdata = [st]
        graphs = self.conf
        ydata = {}
        for k in graphs.keys():
            ydata[k] = [0]

        points = {}
        for k in graphs.keys():
            points[k] = ax.plot_date(xdata, ydata[k], graphs[k])[0]

        fig.canvas.draw()

        with open(self.source, "rb") as f:
            tfirst = 0
            tlast = 0
            tdraw = 0
            twindow = 0
            rows = 0
            for row in csv.DictReader(f):
                rows += 1
                try:
                    if plt.fignum_exists(fig.number) is False:
                        self.interrupted = True
                        break

                    if self.interrupted:
                        break

                    t = float(row["timestamp"])

                    if tfirst == 0:
                        tfirst = t

                    if t - tlast > 60:
                        tlast = t
                        datapoint = {}

                        for k in iterkeys(graphs):
                            if k in row:
                                datapoint[k] = row[k]
                            else:
                                datapoint[k] = 0

                        # print time.time(), "draw", t, datapoint

                        tdata.append(t)
                        xdata.append(date2num(datetime.datetime.fromtimestamp(t)))
                        for k, v in iteritems(datapoint):
                            if k in ydata:
                                ydata[k].append(v)

                        if tlast - tdraw > 1800:
                            tdraw = tlast
                            if tlast > twindow:
                                twindow = tlast + 3600
                                ax.set_xlim(date2num(datetime.datetime.fromtimestamp(tfirst)),
                                            date2num(datetime.datetime.fromtimestamp(twindow)))
                            for k, pts in iteritems(points):
                                pts.set_data(xdata, ydata[k])
                            fig.canvas.draw()
                            plt.pause(0.01)

                        print(rows)

                except KeyboardInterrupt:
                    self.interrupted = True

        if tlast > twindow:
            twindow = tlast + 3600
            ax.set_xlim(date2num(datetime.datetime.fromtimestamp(tfirst)),
                        date2num(datetime.datetime.fromtimestamp(twindow)))
        for k, pts in iteritems(points):
            pts.set_data(xdata, ydata[k])
        fig.canvas.draw()

        while not self.interrupted:
            plt.pause(0.01)

        plt.close(fig)

    def join(self, timeout=None):
        self.interrupted = True
        super(Plotting, self).join(timeout)


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Volta CSV Plot")
    parser.add_argument("--configuration", default="volts.json", help="Plotting configuration file")
    parser.add_argument("--source", default="output.csv", help="CSV input file")
    parser.add_argument("--low", type=int, default=-10)
    parser.add_argument("--high", type=int, default=10)
    parser.add_argument("--minor", type=float, default=0.5)
    parser.add_argument("--major", type=float, default=1)
    args = parser.parse_args()

    with open(args.configuration) as f:
        conf = json.loads(f.read())

    plot = Plotting(args.source, conf, [args.low, args.high], [args.major, args.minor])
    # plot.start()
    plot.run()

    # try:
    #    while not plot.interrupted:
    #        time.sleep(1)
    # except KeyboardInterrupt:
    #    print("interrupted")
    #    #plot.join()


if __name__ == "__main__":
    main()
