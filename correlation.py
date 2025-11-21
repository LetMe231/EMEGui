# import numpy as np
# import matplotlib.pyplot as plt

# def read_files(tx_name = '*.bin', rx_name = '*.bin'):
#     with open(f'N:\Empfang_data\{tx_name}', mode='rb') as file:
#         tx = np.fromfile(file, dtype=np.complex64)
#     with open(f'N:\Empfang_data\{rx_name}', mode='rb') as file:
#         rx = np.fromfile(file, dtype=np.complex64)
#     return ((tx).astype(np.float32)), ((rx).astype(np.float32))


# if __name__ == "__main__":

#     # fs = 2000000    
    
#     # tx, rx = read_files('erste_Versuch_tx.bin', 'erste_Versuch_rx.bin')
#     # tx = tx*2-np.max(tx)
#     # rx = rx*2-np.max(rx)

#     # N = min(4608000, tx.size, rx.size)
#     # tx = tx[:N]
#     # rx = rx[:N]

#     # t_tx = np.arange(tx.size)/fs
#     # print(len(t_tx))
#     # t_rx = np.arange(rx.size)/fs
#     # #corr = np.round(np.correlate(np.abs(tx), np.abs(rx), mode='full'))

#     # n = len(tx) + len(rx) -1
#     # nfft = 1 << (n-1).bit_length()
#     # TX = np.fft.fft(tx, nfft)
#     # RX = np.fft.fft(rx, nfft) 
#     # corr = np.abs(np.fft.ifft(TX * np.conj(RX))[:n])

#     # lags = np.arange(-(tx.size-1), rx.size)   # Länge = len(tx)+len(rx)-1
#     # t_corr = np.arange(lags.size)/fs

#     # fig ,ax = plt.subplots(3)
#     # ax[0].plot(t_tx, tx)
#     # ax[1].plot(t_rx, rx)
#     # ax[2].plot(t_corr, corr)
#     # plt.show()

#     fs = 200000
#     N = 460800
#     Ndelay = 2 * 226667
#     Nchain = 80
#     c = 299792458 #m/s
    
#     tx, rx = read_files('erste_Versuch_tx.bin', 'erste_Versuch_rx.bin')
#     tx, rx_time = read_files('erste_Versuch_tx.bin', 'rx_abgleich.bin')

#     # tx = tx*2-np.max(tx)
#     # rx = rx*2-np.max(rx)
#     # tx = tx[:N]
#     # rx = rx[:int(2.5*N+2*d)]
#     # print(tx.size)
#     # print(rx.size)
#     t_tx = np.arange(tx.size)/fs
#     t_rx = np.arange(rx.size)/fs
#     t_rx_time = np.arange(rx_time.size)/fs
#     # corr1 = np.round(np.correlate(tx, rx, mode='full'))
#     corr2 = np.round(np.correlate((rx)[::10], (tx)[::10], mode='full'))
#     corrt = np.round(np.correlate((rx_time)[::10], (tx)[::10], mode='full'))



#     t_corr1 = np.arange(np.concatenate((tx, rx)).size)[:-1]
#     t_corr2 = np.arange(np.concatenate((tx, rx)).size/10)[:-1]
#     t_corrt = np.arange(np.concatenate((tx, rx_time)).size/10)[:-1]

#     # print(len(corr2))


#     fig ,ax = plt.subplots(5)
#     ax[0].plot(t_tx, tx)
#     ax[1].plot(t_rx_time, rx_time)
#     ax[2].plot(t_corrt, corrt)
#     ax[3].plot(t_rx, rx)
#     ax[4].plot(t_corr2, corr2)

#     peak_rx_time = t_corrt[np.argmax(np.abs(corrt))]*10
#     Ndely = peak_rx_time - N - 1

#     peak = t_corr2[np.argmax(np.abs(corr2))]*10
#     TOF = (peak - N - 1 - Ndely)/fs
#     print(f'Time of Flight: {TOF} s')
#     dist = (TOF * c)/2000
#     print(f'Distanz: {int(dist)} km') 
#     actualldelay= Ndelay / fs
#     print(f'soll Zeit: {actualldelay}')
#     plt.show()