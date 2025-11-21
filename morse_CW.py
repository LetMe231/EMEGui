import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import max_len_seq
from scipy.signal import find_peaks
import os


MORSE = {
    'A':'.-',   'B':'-...', 'C':'-.-.', 'D':'-..',  'E':'.',    'F':'..-.',
    'G':'--.',  'H':'....', 'I':'..',   'J':'.---', 'K':'-.-',  'L':'.-..',
    'M':'--',   'N':'-.',   'O':'---',  'P':'.--.', 'Q':'--.-', 'R':'.-.',
    'S':'...',  'T':'-',    'U':'..-',  'V':'...-', 'W':'.--',  'X':'-..-',
    'Y':'-.--', 'Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-',
    '5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'
}

def set_text(wpm=20, msg=' ', fs = 50):

    dot_1wpm = 60/50
    dot_f = (dot_1wpm/wpm)*1.2 #time for one dot in s.
    dot = int(round(dot_f * fs)) # convert to sampels per one dot
    dash = 3 * dot
    space_in = dot
    space_letter = 3 * dot
    space_word = 7 * dot
    #print(dot)
    morse = []
    for i, let in enumerate(msg.upper()):
        if let == ' ':
            morse += [-1.0] * space_word
        else:
            code = MORSE.get(let)
            for j, symbol in enumerate(code):
                morse += [1.0] * dot if symbol == '.' else [1.0] * dash
                if j != len(code) - 1:
                    morse += [-1.0] * space_in
            if i != len(msg) - 1:
                morse += [-1.0] * space_letter
    
    morse_f = np.array(morse, dtype=np.float32)
    #print(morse_f)
    length = len(morse_f)/fs

    # output_file = open(r"C:\Users\yves.looser\Documents\morse.bin", 'wb')
    # morse_f.tofile(output_file)
    # output_file.close()

    return morse_f, length

def set_pn_seq(bit = 7, fs = 50):
    seq, _ = max_len_seq(bit)      # 10-Bit m-Sequence, Länge 2**10 - 1 = 1023
    chips = 2 * seq - 1 

    dot_1wpm = 60/50
    dot_f = (dot_1wpm/wpm) #time for one dot in s.
    dot = 7*(int(round(dot_f * fs))) # convert to sampels per one dot
    seq = []
    for sym in chips:
        seq += [1.0] * dot if sym == 1 else [-1.0] * dot
    length = len(seq)/fs
    return seq, length

def add_noise(sig, snr = 0):
    sig_watt = sig ** 2
    sig_watt_avg = np.mean(sig_watt)
    #print(sig_watt_avg)
    sig_db = 10 * np.log10(sig_watt_avg)
    #print(sig_db)
    noise_db = sig_db - snr
    noise_watt = 10 ** (noise_db/10)
    noise = np.random.normal(0, np.sqrt(noise_watt), len(sig))
    noise_double = np.random.normal(0, np.sqrt(noise_watt), 2*len(sig))

    return sig + noise, noise_double

if __name__ == "__main__":
    moon_closest = 363104000 #m
    c = 299792458 #m/s
    closest_time = (moon_closest/c) * 2
    print(closest_time)

    fs = 200000  # samples per second
    wpm = 700  # words per minute
    snr =  80 # target snr
    msg = 'HB9HSR DE HB9HSR AR BT EME RANGE MOON BT RTT MEASUREMENT ONLY BT NO REPLY PSE BT EXPERIMENTAL TX BT TNX BT HB9HSR AR SK' # message

    callsign, lengthc = set_text(70, 'HB9HSR T', fs)
    noisy_callsign, noisec = add_noise(callsign, snr)

    # morse, length = set_text(wpm, msg, fs)
    # noisy_morse, noise = add_noise((morse+1)/2, snr)

    morse1, length1 = set_text(50, 'HB9HSR T', fs)
    # noisy_morse1, noise1 = add_noise((morse1+1)/2, snr)

    # morse2, length2 = set_text(100, 'HB9HSR TEST AR SK', fs)
    # noisy_morse2, noise2 = add_noise((morse2+1)/2, snr)

    # chips, length_pn = set_pn_seq(6, fs)
    # noisy_pn, noise_pn = add_noise((np.array(chips)+1)/2, snr)


    
    save_path = r'C:\Users\yves.looser\OneDrive - OST\Dokumente/binforMorse.bin'  
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    (morse1).astype('<f4').ravel().tofile(save_path)
    print('Saved to:', save_path)
    print(len(morse1))
    
    #noisy_morse_2 = np.concatenate((noisy_morse_2, noise_2))
    #length *= 3
    #noisy_morse_1, noise_1 = add_noise(morse, snr)
    #noisy_morse_1 = np.concatenate((noisy_morse_1, noise_1))
    #length *= 3

    # print(f'{length}. Message length fits!') if length <= closest_time else print(f'{length}. To long message!')
    # print('Human readable!') if wpm <= 50 else print('Non readable!')

    print(f'{length1}. HB9HSR T | length fits!') if length1 <= closest_time else print(f'{length1}. To long message!')
    print('Human readable!') if wpm <= 50 else print('Non readable!')

    # print(f'{length2}. HB9HSR TEST AR SK | length fits!') if length2 <= closest_time else print(f'{length2}. To long message!')
    # print('Human readable!') if wpm <= 50 else print('Non readable!')

    

    # print(f'{length_pn+lengthc}. PN-Message length fits!') if length_pn+lengthc <= closest_time else print(f'{length_pn+lengthc}. To long PN-message!')

    # t_callsign = np.arange(0, lengthc, 1/fs)

    # t_chipc = np.arange(0, length_pn+lengthc, 1/fs)
    # t_chipc_corr = np.arange(0, 2*(length_pn+lengthc), 1/fs)[:-1]

    # t_chip = np.arange(0, length_pn, 1/fs)
    # t_chip_corr = np.arange(0, 2*length_pn, 1/fs)[:-1]

    # t_morse = np.arange(0,length, 1/fs)
    # t_corr = np.arange(0,2*length, 1/fs)[:-1]

    # t_morse1 = np.arange(0,length1, 1/fs)
    # t_corr1 = np.arange(0,2*length1, 1/fs)[:-1]

    # t_morse2 = np.arange(0,length2, 1/fs)
    # t_corr2 = np.arange(0,2*length2, 1/fs)[:-1]

    # fig, ax = plt.subplots(2,4)
    # ax[0,0].plot(t_morse, morse)
    # ax[0,0].set_title('Morse für LANG')
    
    # corr = np.round(np.correlate(morse, noisy_morse, mode='full'))
    # peaks = find_peaks(corr, 1)
    # peaks_v = corr[peaks[0]]
    # ax[1,0].plot(t_corr, corr)
    # n = 0
    # for i in np.sort(peaks_v)[::-1].astype(int):
    #     idx = np.where(corr == i)[0][0]
    #     ax[1,0].scatter(t_corr[idx], corr[idx])
    #     ax[1,0].annotate(i, (t_corr[idx], corr[idx]))
    #     n += 1
    #     if n >= 2:
    #          break


    # ax[0,1].plot(t_morse1, morse1)
    # ax[0,1].set_title('Morse für HB9HSR T')

    # corr1 = np.round(np.correlate(morse1, noisy_morse1, mode='full'))
    # peaks1 = find_peaks(corr1, 1)
    # peaks1_v = corr1[peaks1[0]]
    # ax[1,1].plot(t_corr1, corr1)
    # n = 0
    # for i in np.sort(peaks1_v)[::-1].astype(int):
    #     idx = np.where(corr1 == i)[0][0]
    #     ax[1,1].scatter(t_corr1[idx], corr1[idx])
    #     ax[1,1].annotate(i, (t_corr1[idx], corr1[idx]))
    #     n += 1
    #     if n >= 2:
    #          break


    # ax[0,2].plot(t_morse2, morse2)
    # ax[0,2].set_title('Morse für HB9HSR TEST AR SK')
    
    # corr2 = np.round(np.correlate(morse2, noisy_morse2, mode='full'))
    # peaks2 = find_peaks(corr2, 1)
    # peaks2_v = corr2[peaks2[0]]
    # ax[1,2].plot(t_corr2, corr2)
    # n = 0
    # for i in np.sort(peaks2_v)[::-1].astype(int):
    #     idx = np.where(corr2 == i)[0][0]
    #     ax[1,2].scatter(t_corr2[idx], corr2[idx])
    #     ax[1,2].annotate(i, (t_corr2[idx], corr2[idx]))
    #     n += 1
    #     if n >= 2:
    #          break


    # # ax[0,3].plot(t_chipc, np.concatenate((callsign, chips)))
    # # ax[0,3].set_title('PN-Signal')

    # # corr_pn = np.correlate(np.concatenate((callsign, chips)), np.concatenate((callsign, chips)), mode='full')
    # # peaks3 = find_peaks(corr_pn, 1)
    # # peaks3_v = corr_pn[peaks3[0]]
    # # ax[1,3].plot(t_chipc_corr, corr_pn)
    # # n = 0
    # # for i in np.sort(peaks3_v)[::-1].astype(int):
    # #     idx = np.where(corr_pn == i)[0][0]
    # #     ax[1,3].scatter(t_chipc_corr[idx], corr_pn[idx])
    # #     ax[1,3].annotate(i, (t_chipc_corr[idx], corr_pn[idx]))
    # #     n += 1
    # #     if n >= 2:
    # #          break

    # ax[0,3].plot(t_chip, chips)
    # ax[0,3].set_title('PN-Signal')

    # corr_pn = np.round(np.correlate(chips, noisy_pn, mode='full'))
    # peaks3 = find_peaks(corr_pn, 1)
    # peaks3_v = corr_pn[peaks3[0]]
    # ax[1,3].plot(t_chip_corr, corr_pn)
    # n = 0
    # for i in np.sort(peaks3_v)[::-1].astype(int):
    #     idx = np.where(corr_pn == i)[0][0]
    #     ax[1,3].scatter(t_chip_corr[idx], corr_pn[idx])
    #     ax[1,3].annotate(i, (t_chip_corr[idx], corr_pn[idx]))
    #     n += 1
    #     if n >= 2:
    #          break

    # plt.show()
