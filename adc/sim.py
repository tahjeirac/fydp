import time
import numpy as np
import scipy.fftpack
import matplotlib.pyplot as plt

# Set up pigpio and configure SPI settings (though not used here, keeping for consistency)


SPI_BUS = 0  # SPI bus (0 or 1)
SPI_CS = 8   # Chip select GPIO pin (adjust as needed)
SAMPLE_FREQ = 50000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
POWER_THRESH = 9e-4 # tuning is activated if the signal power exceeds this threshold
NOISE_LEVEL = 0.02  # Noise level (0 to 1, where 1 is full scale)


# Parameters for Harmonics and ADSR Envelope
HARMONIC_COUNT = 5  # Number of harmonics to include
ADSR_ATTACK = 0.1  # Attack time in seconds
ADSR_SUSTAIN = 0.7  # Sustain level (0-1)
ADSR_RELEASE = 0.1  # Release time in seconds

# Function to simulate ADC readings with a sine wave (for testing purposes)
def simulate_adc_signal1(frequency, sample_freq, duration=1.0):
    """Simulates ADC readings for a sine wave at a given frequency"""
    print("sim start")
    t = np.arange(0, duration, 1/sample_freq)
    # Generate a sine wave with the given frequency and scale it to the voltage range
    sine_wave = np.sin(2 * np.pi * frequency * t)
    print("sine")
    # Simulate ADC readings (scaled to voltage and then to ADC range)
    adc_values = np.round((sine_wave * (2**BIT_DEPTH - 1) / 2) + (2**(BIT_DEPTH - 1)))  # Center the waveform
    print ("sim")
    return adc_values

def generate_adsr_envelope(duration, attack, sustain, release, sample_rate):
    """Generates an ADSR envelope for the sound"""
    attack_samples = int(attack * sample_rate)
    sustain_samples = int(sustain * sample_rate)
    release_samples = int(release * sample_rate)
    
    envelope = np.zeros(int(duration * sample_rate))
    
    # Attack phase
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    
    # Sustain phase
    envelope[attack_samples:attack_samples+sustain_samples] = 1.0
    
    # Release phase
    envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    
    return envelope

# Function to simulate the ADC signal with harmonics and ADSR envelope
def simulate_adc_signal(frequency, sample_freq, duration=1.0, noise_level=0.02):
    """Simulates ADC readings for a piano-like wave with harmonics and ADSR envelope"""
    t = np.arange(0, duration, 1/sample_freq)  # Time vector
    
    # Generate harmonics (integer multiples of the fundamental frequency)
    signal = np.zeros_like(t)
    for n in range(1, HARMONIC_COUNT + 1):
        signal += (1/n) * np.sin(2 * np.pi * n * frequency * t)
    
    # Generate ADSR envelope
    envelope = generate_adsr_envelope(duration, ADSR_ATTACK, ADSR_SUSTAIN, ADSR_RELEASE, sample_freq)
    
    # Apply the envelope to the signal
    signal *= envelope
    
    noise = np.random.normal(0, noise_level, size=signal.shape)  # Gaussian noise
    signal += noise
    
    # Simulate ADC readings (scaled to voltage and then to ADC range)
    adc_values = np.round((signal * (2**BIT_DEPTH - 1) / 2) + (2**(BIT_DEPTH - 1)))  # Center the waveform
    return adc_values


def ConvertToVoltage(value, bitdepth, vref):
    return vref * (value / (2 ** bitdepth - 1))

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2 ** BIT_DEPTH - 1))

def ConvertToDB(value, bitdepth):
    return 20 * np.log10(value / (2 ** bitdepth - 1))

def get_frequency(samples):
    """Get the dominant frequency from ADC samples using FFT"""
    # Perform FFT
    fft_result = scipy.fftpack.fft(samples)
    fft_freqs = scipy.fftpack.fftfreq(len(samples), d=1/SAMPLE_FREQ)

    # Get the magnitude of the FFT result
    magnitude = np.abs(fft_result)
    magnitude[0] = 0

    plt.figure(figsize=(10, 6))
    plt.plot(fft_freqs[:len(samples)//2], magnitude[:len(samples)//2])
    plt.title('Magnitude Spectrum')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.grid(True)
    plt.show()

    # Find the index of the peak frequency
    peak_index = np.argmax(magnitude)
    peak_freq = np.abs(fft_freqs[peak_index])

    # Since the FFT gives both positive and negative frequencies, ensure we use the positive part
    if peak_freq > SAMPLE_FREQ / 2:
        peak_freq -= SAMPLE_FREQ

    return peak_freq

def calculate_signal_power(adc_samples):
    """Calculate the power of the signal from ADC samples"""
    # Square the ADC values and take the average (mean)
    power = np.mean(np.square(adc_samples))
    return power

try:
    print("hi")
    samples = []
    freq = 261.63  # Frequency of Middle C (261.63 Hz)
    # Simulate an ADC reading (for testing with sine wave of Middle C)
    adc_values = simulate_adc_signal(frequency=freq, sample_freq=SAMPLE_FREQ, duration=1.0)
    plt.figure(figsize=(10, 6))
    plt.plot(adc_values[:100])  # Show first 100 samples
    plt.title("First 100 ADC Values for Piano Middle C with Harmonics, ADSR Envelope, and Noise")
    plt.xlabel("Sample Number")
    plt.ylabel("ADC Value")
    plt.grid(True)
    plt.show()
    samples.extend(adc_values)
    print ("samples")
    if len(samples) >= WINDOW_SIZE:
        # Get the frequency of the signal in the collected samples
        dominant_frequency = get_frequency(samples)
        real_f = dominant_frequency / 8.3
        power = calculate_signal_power(samples)
        print(f"Signal Power: {power:.6f}")
        if power > POWER_THRESH:
            print(f"Dominant frequency: {dominant_frequency:.2f} Hz")
            print(f" real_f: {real_f:.2f} Hz")

        # Clear the sample window to collect the next set of data
        samples = []


except KeyboardInterrupt:
    print("Program interrupted")

