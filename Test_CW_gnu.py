#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: yves.looser
# GNU Radio version: 3.10.5.1

from gnuradio import blocks
import pmt
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
from datetime import datetime, timezone




class testSpeci(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.t0 = t0 = 0.5
        self.samp_rate = samp_rate = 4e5
        self.guard = guard = 0.05
        self.tone = tone = 100e3
        self.t_tx = t_tx = t0 + guard
        self.nsamps = nsamps = 460800
        self.length = length = 2.304
        self.gain_tx = gain_tx = 60
        self.gain_rx = gain_rx = 80
        self.delay = delay = round(2.3*samp_rate)
        self.center_freq = center_freq = 1296e6
        self.amplitude = amplitude = 0.25

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('type=b200', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='peak=0.003906',
                channels=list(range(0,1)),
            ),
        )
        # self.uhd_usrp_source_0.set_clock_source('default', 0)
        # self.uhd_usrp_source_0.set_time_source('default', 0)
        self.uhd_usrp_source_0.set_subdev_spec('A:B', 0)
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        # No synchronization enforced.

        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(center_freq, samp_rate/40), 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_bandwidth(0.2e6, 0)
        self.uhd_usrp_source_0.set_gain(gain_rx, 0)
        self.uhd_usrp_sink_1 = uhd.usrp_sink(
            ",".join(('type=b200', '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            "",
        )
        # self.uhd_usrp_sink_1.set_clock_source('default', 0)
        # self.uhd_usrp_sink_1.set_time_source('default', 0)
        self.uhd_usrp_sink_1.set_samp_rate(samp_rate)
        # No synchronization enforced.

        self.uhd_usrp_sink_1.set_center_freq(uhd.tune_request(center_freq, samp_rate), 0)
        self.uhd_usrp_sink_1.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_1.set_bandwidth(0.2e6, 0)
        self.uhd_usrp_sink_1.set_gain(gain_tx, 0)
        self.low_pass_filter_0 = filter.fir_filter_ccf(
            20,
            firdes.low_pass(
                1,
                samp_rate,
                10000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, (5*int(samp_rate)))
        self.blocks_file_source_1 = blocks.file_source(gr.sizeof_gr_complex*1, 'N:\\Empfang_data/Test_CW.bin', False, 0, 0)
        self.blocks_file_source_1.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, f'N:\\Empfang_data/rx_Versuch_{datetime.now().strftime("%H%M%S")}_CW.bin', False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_1, 0), (self.uhd_usrp_sink_1, 0))
        self.connect((self.blocks_head_0, 0), (self.low_pass_filter_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_head_0, 0))


    def get_t0(self):
        return self.t0

    def set_t0(self, t0):
        self.t0 = t0
        self.set_t_tx(self.t0 + self.guard)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_delay(round(2.3*self.samp_rate))
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, 10000, 1000, window.WIN_HAMMING, 6.76))
        self.uhd_usrp_sink_1.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.center_freq, self.samp_rate), 0)

    def get_guard(self):
        return self.guard

    def set_guard(self, guard):
        self.guard = guard
        self.set_t_tx(self.t0 + self.guard)

    def get_tone(self):
        return self.tone

    def set_tone(self, tone):
        self.tone = tone

    def get_t_tx(self):
        return self.t_tx

    def set_t_tx(self, t_tx):
        self.t_tx = t_tx

    def get_nsamps(self):
        return self.nsamps

    def set_nsamps(self, nsamps):
        self.nsamps = nsamps

    def get_length(self):
        return self.length

    def set_length(self, length):
        self.length = length

    def get_gain_tx(self):
        return self.gain_tx

    def set_gain_tx(self, gain_tx):
        self.gain_tx = gain_tx
        self.uhd_usrp_sink_1.set_gain(self.gain_tx, 0)

    def get_gain_rx(self):
        return self.gain_rx

    def set_gain_rx(self, gain_rx):
        self.gain_rx = gain_rx
        self.uhd_usrp_source_0.set_gain(self.gain_rx, 0)

    def get_delay(self):
        return self.delay

    def set_delay(self, delay):
        self.delay = delay

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.uhd_usrp_sink_1.set_center_freq(self.center_freq, 0)
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.center_freq, self.samp_rate), 0)

    def get_amplitude(self):
        return self.amplitude

    def set_amplitude(self, amplitude):
        self.amplitude = amplitude




def main(top_block_cls=testSpeci, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    # time.sleep(2.1)
    # coax_toggle_mode()
    tb.wait()


if __name__ == '__main__':
    main()
