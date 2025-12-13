import numpy as np
from numpy.fft import fft, ifft
import matplotlib.pyplot as plt
# from Doppler import doppler_fitting
from dopplerTry2 import doppler_change_at_utc

def read_files(tx_name = '*.bin', rx_name = '*.bin'):
    with open(f'N:\Empfang_data\{tx_name}', mode='rb') as file:
        tx = np.fromfile(file, dtype=np.complex64)
    with open(f'N:\Empfang_data\{rx_name}', mode='rb') as file:
        rx = np.fromfile(file, dtype=np.complex64)
    return tx, rx


def calc_distance(tx, rx, fs=20000):

    c = 299792458 #m/s

    t_tx = np.arange(tx.size)/fs
    t_rx = np.arange(rx.size)/fs
    
    rx_fft = fft(rx)
    tx_fft = fft(tx, n=len(rx)).conj()
    xcorr = np.abs(ifft(rx_fft*tx_fft))

    start_samp = round(2.4*fs)
    rx_start = rx[:start_samp]
    t_rx_start = np.arange(rx_start.size)/fs
    rx_start_fft = fft(rx_start)
    tx_start_fft = fft(tx, n=len(rx_start)).conj()
    start_corr = np.abs(ifft(rx_start_fft*tx_start_fft))

    fig ,ax = plt.subplots(3,2)
    # ax[0,0].plot(t_tx, tx)
    # ax[1,0].plot(t_rx_start, rx_start)
    # ax[2,0].plot(t_rx_start, start_corr)

    ax[0,1].plot(t_tx, tx)
    ax[1,1].plot(t_rx, rx)
    ax[2,1].plot(t_rx, xcorr)

    relevant = round(1.2*fs)
    peak_rx_start = t_rx_start[np.argmax(start_corr[:relevant])]
    peak_rx_time = t_rx[np.argmax(xcorr)]
    TOF = peak_rx_time-peak_rx_start
    print(peak_rx_start) # Peak tx signal beginn
    print(peak_rx_time) # Peak rx signal is back
    print(TOF) #TOF
    return ((TOF/fs)*c)/1000

if __name__ == "__main__": 

    fs = 20000
    N = 460800
    Ndelay = 2 * 226667
    Nchain = 80
    c = 299792458 #m/s
    
    tx, rx = read_files('erste_Versuch_tx.bin', 'rx_abgleich.bin')

    # tx, rx_dopp = read_files('erste_Versuch_tx.bin', 'rx_abgleich_dopp.bin')
    
    # print(calc_distance(tx, rx, 20000)) #innetue wennd wider willsh dist messe.

    # print(calc_distance(tx, rx_dopp, 20000))
    # print(calc_distance(tx, doppler_fitting(rx_dopp, -500, 20000), 20000))
    tx, rx_s_CW = read_files('Test_CW.bin', 'rx_Versuch_110400_CW.bin')
    start = 2.3
    l = 1
    t_rx_CW = np.arange(rx_s_CW.size)/fs
    t_tx = np.arange(tx.size)/fs

    fig, ax = plt.subplots(3)
    # ax[0].plot(t_tx, np.real(tx))
    # ax[0].plot(t_tx, np.imag(tx))
    ax[0].plot(t_rx_CW, np.real(rx_s_CW))
    ax[0].plot(t_rx_CW, np.imag(rx_s_CW))

    
    start_s = round(start*fs)
    stop_s = round((start+l)*fs)
    rx_s_CW = rx[start_s:stop_s]
    t_rx_CW = t_rx_CW[start_s:stop_s]

    t = np.arange(len(rx_s_CW))/fs

    fit = np.exp(1j*(doppler_change_at_utc(9, 57, l)[0]*t**2)/2)

    # for i in np.arange(40):
    # fit = np.exp(1j*((-0.2+i*0.01)*t**2)/2)
    window = np.blackman(len(rx_s_CW))
    rx_s_CW -= np.mean(rx_s_CW)
    rx_s_CW = rx_s_CW*fit



    rx_fft_CW = 10*np.log(np.abs(fft(rx_s_CW*window)))
    rx_fft_CW = np.fft.fftshift(rx_fft_CW)
    # t_rx_CW = np.arange(rx_s_CW.size)/fs
        
    freqs = np.fft.fftfreq(len(rx_s_CW), d=(1/fs))
    freqs = np.fft.fftshift(freqs)

    ax[1].plot(t_rx_CW, rx_s_CW)
    ax[2].plot(freqs, rx_fft_CW)
        
    plt.show()

    # t_tx = np.arange(tx.size)/fs
    # t_rx = np.arange(rx.size)/fs
    
    # rx_fft = fft(rx)
    # tx_fft = fft(tx, n=len(rx)).conj()
    # xcorr = np.abs(ifft(rx_fft*tx_fft))

    # start_samp = round(2.4*fs)
    # rx_start = rx[:start_samp]
    # t_rx_start = np.arange(rx_start.size)/fs
    # rx_start_fft = fft(rx_start)
    # tx_start_fft = fft(tx, n=len(rx_start)).conj()
    # start_corr = np.abs(ifft(rx_start_fft*tx_start_fft))

    # fig ,ax = plt.subplots(3,2)
    # ax[0,0].plot(t_tx, tx)
    # ax[1,0].plot(t_rx_start, rx_start)
    # ax[2,0].plot(t_rx_start, start_corr)

    # ax[0,1].plot(t_tx, tx)
    # ax[1,1].plot(t_rx, rx)
    # ax[2,1].plot(t_rx, xcorr)

    # relevant = round(1.2*fs)
    # peak_rx_start = t_rx_start[np.argmax(start_corr[:relevant])]
    # peak_rx_time = t_rx[np.argmax(xcorr)]
    # print(peak_rx_start) # Peak tx signal beginn
    # print(peak_rx_time) # Peak rx signal is back
    # print(peak_rx_time-peak_rx_start) #TOF

    # plt.show()