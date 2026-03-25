import speech_recognition as sr
import pyttsx3
import requests
import threading

class AudioEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.gateway_url = "http://191.252.109.18:18789"
        self.gateway_token = "fc120b7b67a5d8c148e1429d88699e2e51ca80a67ff82af6d9754d5a8e1d4ffb"
        self.worker_id = "LENOVO_YURI"
        
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 170)
        self.is_listening = True

    def speak(self, text):
        print(f"\n🎧 [Jarvis -> Voz] Falando: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen_loop(self):
        with sr.Microphone() as source:
            print("🎙️ [Jarvis] Ajustando redução de ruído ambiental...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print("🎙️ [Jarvis] Pronto e escutando (Wake Word: 'Jarvis')...")

            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio, language='pt-BR').lower()
                    
                    if "jarvis" in text:
                        print(f"\n🗣️ [Wake Word] Você falou: {text}")
                        comando = text.replace("jarvis", "").strip()
                        
                        if comando:
                            self.send_to_brain(comando)
                        else:
                            self.speak("Sim, senhor?")
                            audio2 = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                            comando2 = self.recognizer.recognize_google(audio2, language='pt-BR')
                            self.send_to_brain(comando2)
                            
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    pass

    def send_to_brain(self, spoken_text):
        print(f"☁️ [OpenClaw REST] Enviando comando: '{spoken_text}'")
        try:
            headers = {
                "Authorization": f"Bearer {self.gateway_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openclaw",
                "user": self.worker_id,
                "messages": [{"role": "user", "content": spoken_text}]
            }
            
            resp = requests.post(
                f"{self.gateway_url}/v1/chat/completions",
                json=payload, 
                headers=headers, 
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            
            resposta_cerebro = data["choices"][0]["message"]["content"]
            self.speak(resposta_cerebro)
            
        except requests.exceptions.HTTPError as e:
            self.speak(f"O cérebro rejeitou a conexão com status {e.response.status_code}.")
        except Exception as e:
            self.speak("Infelizmente, ocorreu um erro de comunicação com o Cérebro na nuvem.")
            print(f"❌ [Erro REST] {e}")
            
    def start(self):
        t = threading.Thread(target=self.listen_loop, daemon=True)
        t.start()
