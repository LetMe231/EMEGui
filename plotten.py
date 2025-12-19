import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ---- Deine MORSE Tabelle ----
MORSE = {
    'A':'.-',   'B':'-...', 'C':'-.-.', 'D':'-..',  'E':'.',    'F':'..-.',
    'G':'--.',  'H':'....', 'I':'..',   'J':'.---', 'K':'-.-',  'L':'.-..',
    'M':'--',   'N':'-.',   'O':'---',  'P':'.--.', 'Q':'--.-', 'R':'.-.',
    'S':'...',  'T':'-',    'U':'..-',  'V':'...-', 'W':'.--',  'X':'-..-',
    'Y':'-.--', 'Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-',
    '5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'
}

def set_text(wpm=20, msg=' ', fs=50):
    dot_1wpm = 60/50
    dot_f = (dot_1wpm/wpm) * 1.2
    dot = int(round(dot_f * fs))
    dash = 3 * dot
    space_in = dot
    space_letter = 3 * dot
    space_word = 7 * dot

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
    length = len(morse_f) / fs
    return morse_f, length

def xcorr_fft(x, y, fs, remove_mean=True, normalize=True):
    """
    Lineare Kreuzkorrelation via FFT:
    r_xy[k] = sum_n x[n] * conj(y[n-k])
    -> Ausgabe zentriert: Lags von -(Ny-1) .. +(Nx-1)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if remove_mean:
        x = x - np.mean(x)
        y = y - np.mean(y)

    Nx, Ny = len(x), len(y)
    if Nx == 0 or Ny == 0:
        return np.array([]), np.array([])

    nfft = 1 << int(np.ceil(np.log2(Nx + Ny - 1)))

    X = np.fft.fft(x, n=nfft)
    Y = np.fft.fft(y, n=nfft)

    # Kreuzkorrelation im Frequenzbereich
    r = np.fft.ifft(X * np.conj(Y)).real
    r = r[:(Nx + Ny - 1)]  # linearer Teil

    # Lags zentrieren: negative lags zuerst
    r = np.concatenate([r[-(Ny-1):], r[:Nx]])
    lags = np.arange(-(Ny-1), Nx) / fs

    if normalize and np.max(np.abs(r)) > 0:
        r = r / np.max(np.abs(r))

    return lags, r

if __name__ == "__main__":
    # --- exakt wie bei dir fürs Plot: fs=20000, wpm=50, (morse+1)/2 ---
    fs = 20000
    wpm = 50
    msg = "HB9HSR T"

    morse_tx, _ = set_text(wpm, msg, fs)
    x = (morse_tx + 1) / 2   # 0/1 Signal wie in deinem PDF-Plot

    # "Kreuzkorrelation ... mit sich selbst" => xcorr(x, x)
    lags_s, rxx = xcorr_fft(x, x, fs=fs, remove_mean=True, normalize=True)

    # --- Kreuzkorrelation (x mit x) ---
lags_s, rxx = xcorr_fft(x, x, fs=fs, remove_mean=True, normalize=True)

# --- nur positive Lags ---
pos = lags_s >= 0
lags_pos = lags_s[pos]
rxx_pos = rxx[pos]

# --- spiegeln für negative Seite ---
lags_sym = np.concatenate((-lags_pos[:0:-1], lags_pos))
rxx_sym  = np.concatenate(( rxx_pos[:0:-1],  rxx_pos))

# --- Plot + PDF ---
import os
out_pdf = os.path.abspath("xcorr_fft_self_symmetric.pdf")
print("Saving to:", out_pdf)

with PdfPages(out_pdf) as pdf:
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(lags_sym, rxx_sym)
    ax.set_title("Cross-correlation via FFT 'HB9HSR T'")
    ax.set_xlabel("Lag [s]")
    ax.set_ylabel("Correlation")
    ax.grid(True)

    # optional: auf relevanten Bereich zoomen
    ax.set_xlim(-0.5, 0.5)   # Sekunden – nach Bedarf anpassen

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

print("Saved:", out_pdf)