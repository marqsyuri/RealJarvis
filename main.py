import sys
import time
from audio_engine import AudioEngine
from iot_bridge import IoTBridge

sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🔥 JARVIS DISTRIBUTABLE WORKER (Voz + IoT) 🔥")
    print("==================================================")
    
    print("\n[1] Inicializando a Ponte IoT (Protocolo Mãos de Ouro V3)...")
    bridge = IoTBridge()
    bridge.start()

    print("[2] Inicializando Motor de Escuta (Microfone)...")
    audio = AudioEngine()
    
    try:
        audio.listen_loop()
    except KeyboardInterrupt:
        print("\n[Main] Encerrando Jarvis Worker de forma limpa...")
        audio.is_listening = False

if __name__ == "__main__":
    main()
