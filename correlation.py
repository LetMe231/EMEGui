import numpy as np
import matplotlib.pyplot as plt

def read_files(tx_name = '*.bin', rx_name = '*.bin'):
    with open(f'N:\Empfang_data\{tx_name}', mode='rb') as file:
        tx = np.fromfile(file, dtype=np.complex64)
    with open(f'N:\Empfang_data\{rx_name}', mode='rb') as file:
        rx = np.fromfile(file, dtype=np.complex64)
    return tx, rx


if __name__ == "__main__":

    fs = 2000000
    z = 2.304
    N = 4608000
    
    tx, rx = read_files('erste_Versuch_tx.bin', 'erste_Versuch_rx.bin')
    tx = tx[:N]
    rx = rx[:N]
    t_tx = np.arange(tx.size)/fs
    t_rx = np.arange(rx.size)/fs
    corr = np.round(np.correlate(np.real(tx)[::1000], np.real(rx)[::1000], mode='full'))
    print(corr)
    t_corr = np.arange(((tx.size)*2)/1000)[:-1]/fs
    fig ,ax = plt.subplots()
    ax.plot(t_corr, corr)
    plt.show()