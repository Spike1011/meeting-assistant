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

    # 2. Select LLM Provider and Model
    print("\n" + "-" * 60)
    print("[*] LLM Configuration")
    print("    Select which AI model to use for summarization.")
    print("-" * 60)
    
    llm_options = [
        ("deepseek", "deepseek-chat", "DeepSeek V3 (Recommended, requires DEEPSEEK_API_KEY)"),
        ("deepseek", "deepseek-reasoner", "DeepSeek R1 (Thinking Model)"),
        ("chatgpt", "gpt-4o", "ChatGPT 4o (Requires OPENAI_API_KEY)"),
        ("chatgpt", "gpt-4o-mini", "ChatGPT 4o-mini (Faster/Cheaper)"),
        ("gemini", "gemini-2.0-flash", "Gemini 2.0 Flash (Fast)"),
        ("gemini", "gemini-1.5-flash", "Gemini 1.5 Flash (Legacy)")
    ]
    
    print("\nAvailable Models:")
    for i, (provider, model, desc) in enumerate(llm_options):
        print(f"    {i+1}. {model} ({provider}) - {desc}")
        
    while True:
        try:
            choice = input(f"\nSelect model number (1-{len(llm_options)}) [default: 1]: ").strip()
            if not choice:
                selected_idx = 0
            else:
                selected_idx = int(choice) - 1
                
            if 0 <= selected_idx < len(llm_options):
                provider, model, _ = llm_options[selected_idx]
                config.set_llm_provider(provider, model)
                print(f"[+] Selected: {model} ({provider})")
                break
            else:
                print(f"[!] Please enter a number between 1 and {len(llm_options)}")
        except ValueError:
            print("[!] Invalid input. Please enter a number.")

    # 3. Set default method to 'dual'
    config.set_recording_method("dual")
    print(f"\n[*] Recording method set to: dual (Native + Microphone)")
    print("    (Captures both system audio and your microphone)")

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
