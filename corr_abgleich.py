import numpy as np
import matplotlib.pyplot as plt

def read_files(tx_name = '*.bin', rx_name = '*.bin'):
    with open(f'N:\Empfang_data\{tx_name}', mode='rb') as file:
        tx = np.fromfile(file, dtype=np.complex64)
    with open(f'N:\Empfang_data\{rx_name}', mode='rb') as file:
        rx = np.fromfile(file, dtype=np.complex64)
    return ((tx).astype(np.float32)), ((rx).astype(np.float32))


if __name__ == "__main__":

    fs = 200000
    N = 460800
    Ndelay = 2 * 226667
    Nchain = 80
    c = 299792458 #m/s
    
    tx, rx_time = read_files('erste_Versuch_tx.bin', 'rx_abgleich.bin')

    t_tx = np.arange(tx.size)/fs

    t_rx_time = np.arange(rx_time.size)/fs
    # corr1 = np.round(np.correlate(tx, rx, mode='full'))
    corrt = np.round(np.correlate((rx_time)[::10], (tx)[::10], mode='full'))


    t_corr1 = np.arange(np.concatenate((tx, rx_time)).size)[:-1]
    t_corrt = np.arange(np.concatenate((tx, rx_time)).size/10)[:-1]



    fig ,ax = plt.subplots(3)
    ax[0].plot(t_tx, tx)
    ax[1].plot(t_rx_time, rx_time)
    ax[2].plot(t_corrt, corrt)

    peak_rx_time = t_corrt[np.argmax(np.abs(corrt))]*10
    print(peak_rx_time)
    dely = (peak_rx_time - N - 1)
    print(dely)
    # print(f'Time of Flight: {TOF} s')
    # dist = (TOF * c)/2000
    # print(f'Distanz: {int(dist)} km') 
    # actualldelay= Ndelay / fs
    # print(f'soll Zeit: {actualldelay}')
    plt.show()