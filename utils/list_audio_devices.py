import pyaudiowpatch as pyaudio


def list_devices():
    p = pyaudio.PyAudio()
    count = p.get_device_count()
    print(f"\nFound {count} audio devices:\n")
    print(f"{'Index':<6} {'Channels':<10} {'Name'}")
    print("-" * 60)

    for i in range(count):
        info = p.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            print(f"  [{i}]  ch={info['maxInputChannels']:<6}  {info['name']}")

    print("\n--- Default Loopback Device (what Python will capture) ---")
    try:
        loopback = p.get_default_wasapi_loopback()
        print(f"  ✓ {loopback['name']}")
        print(f"    Index : {loopback['index']}")
        print(f"    Rate  : {int(loopback['defaultSampleRate'])} Hz")
        print(f"    Ch    : {loopback['maxInputChannels']}")
        print("\n  This is the device that will capture your meeting audio.")
    except Exception as e:
        print(f"  ✗ Could not find loopback device: {e}")
        print("    Make sure audio is playing and try again.")

    p.terminate()


if __name__ == "__main__":
    list_devices()