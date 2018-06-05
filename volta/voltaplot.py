#!/usr/bin/env python
"""voltaplot.py: plot tool"""
from __future__ import absolute_import, division, print_function

from six import iteritems, itervalues

import json
import threading
import time
import datetime
from matplotlib.dates import date2num
import matplotlib.dates as mdates

import numpy

from matplotlib import pyplot as plt

import errno
import nanomsg

__author__ = "Raido Pahtma"
__license__ = "MIT"


PLOT_WINDOW = 10


class PlottingThread(threading.Thread):

    def __init__(self, source, conf, limits, steps, doblit=False):
        super(PlottingThread, self).__init__()
        self.interrupted = False

        self.source = source
        self.conf = conf
        self.limits = limits
        self.steps = steps

        self.doblit = doblit

        self.soc_sub = nanomsg.Socket(nanomsg.SUB)
        self.soc_sub.set_string_option(nanomsg.SUB, nanomsg.SUB_SUBSCRIBE, "")
        self.soc_sub.set_int_option(nanomsg.SOL_SOCKET, nanomsg.RECONNECT_IVL, 1000)
        self.soc_sub.set_int_option(nanomsg.SOL_SOCKET, nanomsg.RECONNECT_IVL_MAX, 1000 * 30)
        self.soc_sub.connect(self.source)

    def run(self):
        """
        Display the simulation using matplotlib, optionally using blit for speed
        """

        fig, ax = plt.subplots(1, 1)
        # ax.set_aspect('equal')
        # ax.hold(True)

        plt.show(False)
        plt.draw()

        if self.doblit:
            # cache the background
            background = fig.canvas.copy_from_bbox(ax.bbox)

        t = time.time()

        # points = ax.plot(0, 0, 'o')[0]
        st = date2num(datetime.datetime.fromtimestamp(t))
        et = date2num(datetime.datetime.fromtimestamp(t + PLOT_WINDOW))
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

        while not self.interrupted:
            if plt.fignum_exists(fig.number) is False:
                self.interrupted = True
                break

            try:
                while not self.interrupted:
                    try:
                        msg = self.soc_sub.recv(flags=nanomsg.DONTWAIT)
                        msg = json.loads(msg)
                        t = msg["t"]
                        datapoint = msg["data"]

                        # print time.time(), "draw", t, datapoint

                        tdata.append(t)
                        xdata.append(date2num(datetime.datetime.fromtimestamp(t)))
                        for k, v in iteritems(datapoint):
                            if k in ydata:
                                ydata[k].append(v)

                        while tdata[-1] - tdata[0] > PLOT_WINDOW:
                            tdata.pop(0)
                            xdata.pop(0)
                            for data in itervalues(ydata):
                                data.pop(0)

                        ax.set_xlim(date2num(datetime.datetime.fromtimestamp(tdata[0])),
                                    date2num(datetime.datetime.fromtimestamp(tdata[0]+PLOT_WINDOW)))

                    except nanomsg.NanoMsgAPIError as e:
                        if e.errno == errno.EAGAIN:
                            break
                        else:
                            raise

                for k, pts in iteritems(points):
                    pts.set_data(xdata, ydata[k])

                if self.doblit:
                    # restore background
                    fig.canvas.restore_region(background)

                    # redraw just the points
                    for pts in itervalues(points):
                        ax.draw_artist(pts)

                    # fill in the axes rectangle
                    fig.canvas.blit(ax.bbox)

                    plt.pause(0.01)
                else:
                    # redraw everything
                    fig.canvas.draw()
                    plt.pause(0.01)

            except Exception as e:
                print("PLOT {}".format(e))
                break

            except KeyboardInterrupt:
                break

        plt.close(fig)

    def join(self, timeout=None):
        self.interrupted = True
        super(PlottingThread, self).join(timeout)


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Voltaplot")
    parser.add_argument("--configuration", default="volts.json", help="Plotting configuration file")
    parser.add_argument("--source", default="tcp://localhost:12345", help="Nanomessage publisher URL")
    parser.add_argument("--low", type=int, default=-10)
    parser.add_argument("--high", type=int, default=10)
    parser.add_argument("--minor", type=float, default=0.5)
    parser.add_argument("--major", type=float, default=1)
    args = parser.parse_args()

    with open(args.configuration) as f:
        conf = json.loads(f.read())

    plot = PlottingThread(args.source, conf, [args.low, args.high], [args.major, args.minor])
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
