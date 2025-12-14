#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def mainstep():
    # ========= Parameter =========
    fs = 3_000_000_000 # Abtastfrequenz [Hz]
    T = 0.1           # Gesamtdauer [s] (10 ms)
    t0 = T / 2         # Zeitpunkt der Flanke

    # ========= Step-Signal erzeugen =========
    t = np.arange(0, T, 1 / fs)   # Zeitachse
    x = np.zeros_like(t)
    x[t >= t0] = 1.0              # einfache Sprungfunktion

    # ========= FFT berechnen =========
    N = len(x)
    X = np.fft.fft(x)
    freqs = np.fft.fftfreq(N, d=1 / fs)

    # Für schönere Darstellung: auf 0 Hz zentrieren
    X_shift = np.fft.fftshift(X)
    freqs_shift = np.fft.fftshift(freqs)

    # ========= Plot + PDF Export =========
    with PdfPages("step_and_fft.pdf") as pdf:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))

        # Zeitsignal
        axes[0].plot(t * 1e3, x)
        axes[0].set_xlabel("Time in ms")
        axes[0].set_ylabel("Amplitude")
        axes[0].set_title("Unit step function u(t)")
        axes[0].grid(True)

        # FFT-Betrag in dB
        magnitude_db = 20 * np.log10(np.abs(X_shift) + 1e-12)  # +1e-12 für log(0)-Schutz
        axes[1].plot(freqs_shift / 1e3, magnitude_db)
        axes[1].set_xlabel("Frequency in kHz")
        axes[1].set_ylabel("|U(j\u03C9)| in dB")
        axes[1].set_title("FFT |U(j\u03C9)|")
        axes[1].grid(True)

        fig.tight_layout()

        # Seite ins PDF schreiben
        pdf.savefig(fig)
        plt.close(fig)

    # Wenn du zusätzlich noch im Fenster anzeigen willst, dann:
    # plt.show()
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def m_sequence(length=301):
    """
    Generate an m-sequence (PN sequence) of length 31
    using a 5-bit LFSR with primitive polynomial:
        x^5 + x^2 + 1   (taps at bits 5 and 2)

    Returns values in {+1, -1}.
    """
    m = 8
    state = np.ones(m, dtype=int)  # non-zero initial state
    seq = []

    for _ in range(2**m - 1):  # 255 states
        out = state[-1]
        seq.append(out)

        # Feedback = XOR of tapped bits: positions 8, 6, 5, 4
        # state[0] -> bit 8, state[1] -> bit 7, ..., state[7] -> bit 1
        feedback = state[0] ^ state[2] ^ state[3] ^ state[4]

        # Shift right and insert feedback at the front
        state[1:] = state[:-1]
        state[0] = feedback

    seq = np.array(seq)
    # Map {0,1} -> {-1,+1}
    seq = 2 * seq - 1
    return seq


def zoh_from_sequence(seq, oversample):
    """
    Zero-order hold (piecewise constant) representation of a discrete sequence.
    Each sample is held constant for 'oversample' points.
    """
    return np.repeat(seq, oversample)


def main():
    # ---- Generate PN sequence ----
    pn = m_sequence(length=301)
    N = len(pn)

    # ---- Oversampling for continuous look ----
    oversample = 2000  # high resolution
    t = np.arange(N)/20000
    pn_zoh = zoh_from_sequence(pn, oversample)

    # ---- Plot and export to PDF ----
    with PdfPages("pn_continuous.pdf") as pdf:
        fig, ax = plt.subplots(figsize=(10, 3))

        ax.plot(t*1000, (pn+1)/2, drawstyle="steps-post")
        ax.set_title(f"PN sequence of length {N}")
        ax.set_xlabel("Time in s")
        ax.set_ylabel("Amplitude")
        ax.grid(True)

        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    # If you also want to see it interactively, uncomment:
    # plt.show()


if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt

    # Parameters (same T as before)
    T = 2.304   # seconds (pulse width)
    A = 1.0     # amplitude of the square pulse

    # Angular frequency axis (rad/s) — choose a range that shows main lobe clearly
    w = np.linspace(-80, 80, 5000)

    # Fourier transform of a time-centered rectangular pulse of height A and width T:
    # F(jw) = ∫_{-T/2}^{T/2} A * e^{-j w t} dt = A * 2 * sin(wT/2) / w
    # with the limit at w=0 being A*T.
    F = np.empty_like(w, dtype=float)
    eps = 1e-15
    mask = np.abs(w) < eps
    F[mask] = A * T
    F[~mask] = A * (2.0 * np.sin(w[~mask] * T / 2.0) / w[~mask])

    # Plot (magnitude; here it's real and even, so abs is fine)
    plt.figure(figsize=(10, 3))
    plt.plot(w, F)
    plt.xlabel(r"$\omega$ in rad/s")
    plt.ylabel("Amplitude")
    plt.title(r"$S(j\omega)$")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    # Save as PDF (no display)
    plt.savefig("Fjw_T_2p304s.pdf")
    plt.close()







