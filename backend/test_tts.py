import os
import soundfile as sf
from kokoro_onnx import Kokoro

print("loading Kokoro model..")

kokoro = Kokoro(
    "models/kokoro-v1.0.int8.onnx",
    "models/voices-v1.0.bin"
)

print("generating speech..")

samples, sample_rate = kokoro.create(
    "Welcome to AdCraft AI. Transform your business URL into a professional video ad in seconds. ",
    voice="af_heart",
    speed=1.0,
    lang="en-us"    
)

output_path = "test_voice.wav"
sf.write(output_path, samples , sample_rate)

print(f"Voice generated: {output_path}")
print(f" Sample rate: {sample_rate}Hz")
print(f"Duration{len(samples)/sample_rate:.1f} seconds")