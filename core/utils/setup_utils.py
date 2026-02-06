import sounddevice as sd
from core.config_manager import ConfigManager

def interactive_setup(config: ConfigManager):
    """
    Interactively setup the application configuration.
    """
    print("\n" + "-" * 60)
    print("[*] Meeting Assistant Setup")
    print("-" * 60)
    
    # 1. Select Audio Device
    print("\n[i] Available Audio Input Devices:")
    devices = sd.query_devices()
    input_devices = []
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append((i, dev['name']))
            print(f"    {len(input_devices)}. {dev['name']} (index {i}, channels {dev['max_input_channels']})")
    
    if not input_devices:
        print("[-] No input devices found!")
        return False
        
    while True:
        try:
            choice = input(f"\nSelect device number (1-{len(input_devices)}) [default: 1]: ").strip()
            if not choice:
                selected_idx = 0
            else:
                selected_idx = int(choice) - 1
                
            if 0 <= selected_idx < len(input_devices):
                device_index, device_name = input_devices[selected_idx]
                config.set_legacy_device_name(device_name)
                print(f"[+] Selected: {device_name}")
                break
            else:
                print(f"[!] Please enter a number between 1 and {len(input_devices)}")
        except ValueError:
            print("[!] Invalid input. Please enter a number.")

    print("\n[+] Setup complete! Configuration saved to config.json")
    print("-" * 60 + "\n")
    return True

def check_first_run(config: ConfigManager):
    """
    Check if this is the first run (no device configured).
    """
    settings = config.get_legacy_settings()
    # If device is "Unit" (default) or empty, we consider it not setup
    # since "Unit" is an aggregate device that might not exist.
    return not settings.get("device_name") or settings.get("device_name") == "Unit"
