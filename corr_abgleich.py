import numpy as np
from numpy.fft import fft, ifft
import matplotlib.pyplot as plt

def read_files(tx_name = '*.bin', rx_name = '*.bin'):
    with open(f'N:\Empfang_data\{tx_name}', mode='rb') as file:
        tx = np.fromfile(file, dtype=np.float32)
    with open(f'N:\Empfang_data\{rx_name}', mode='rb') as file:
        rx = np.fromfile(file, dtype=np.complex64)
    return ((tx).astype(np.float32)), ((rx).astype(np.float32))


if __name__ == "__main__":

    fs = 20000
    N = 460800
    Ndelay = 2 * 226667
    Nchain = 80
    c = 299792458 #m/s
    
    tx, rx = read_files('erste_Versuch_tx.bin', 'rx_abgleich.bin')

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
    ax[0,0].plot(t_tx, tx)
    ax[1,0].plot(t_rx_start, rx_start)
    ax[2,0].plot(t_rx_start, start_corr)

    ax[0,1].plot(t_tx, tx)
    ax[1,1].plot(t_rx, rx)
    ax[2,1].plot(t_rx, xcorr)

    relevant = round(1.2*fs)
    peak_rx_start = t_rx_start[np.argmax(start_corr[:relevant])]
    peak_rx_time = t_rx[np.argmax(xcorr)]
    print(peak_rx_start)
    print(peak_rx_time)
    print(peak_rx_time-peak_rx_start)

    plt.show()