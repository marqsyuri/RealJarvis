import asyncio
import websockets
import json
import os
import hashlib
import base64
import time
import subprocess
import threading
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

class IoTBridge:
    def __init__(self):
        self.ws_url = "ws://191.252.109.18:18789"
        self.gateway_token = "fc120b7b67a5d8c148e1429d88699e2e51ca80a67ff82af6d9754d5a8e1d4ffb"
        self.client_id = "node-host"
        self.worker_id = "LENOVO_YURI"
        
        self.key_file = os.path.expanduser("~/.worker_ed25519.pem")
        self.private_key, self.device_id, self.pubkey_b64 = self.load_or_generate_keys()
        
        self.device_token = None
        self.tick_interval_ms = 15000

    def load_or_generate_keys(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                priv = serialization.load_pem_private_key(f.read(), password=None)
        else:
            priv = Ed25519PrivateKey.generate()
            with open(self.key_file, "wb") as f:
                f.write(priv.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
        
        pub_raw = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        device_id = hashlib.sha256(pub_raw).hexdigest()
        pubkey_b64 = base64.urlsafe_b64encode(pub_raw).decode('utf-8').rstrip('=')
        return priv, device_id, pubkey_b64

    def sign_challenge(self, nonce, signed_at_ms, current_token):
        payload_str = "|".join([
            "v3",
            self.device_id,
            self.client_id,
            "node",
            "node",
            "",
            str(signed_at_ms),
            current_token,
            nonce,
            "windows",
            "desktop"
        ])
        sig = self.private_key.sign(payload_str.encode("utf-8"))
        return base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')

    async def connect_loop(self):
        backoff = 2
        while True:
            try:
                print(f"🔌 [IoT Bridge] Conectando ao OpenClaw V3: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    print("🔄 [IoT Bridge] Socket TCP aberto. Aguardando Challenge...")
                    backoff = 2
                    while True:
                        msg = await ws.recv()
                        await self.handle_message(ws, msg)
            except websockets.exceptions.ConnectionClosed:
                print(f"⚠️ [IoT Bridge] Conexão Perdida. Reconectando em {backoff}s...")
            except Exception as e:
                print(f"❌ [IoT Bridge Error] {e}. Reconectando em {backoff}s...")
                
            await asyncio.sleep(backoff)
            backoff = min(60, backoff * 2)

    async def handle_message(self, ws, message):
        data = json.loads(message)
        type_ = data.get("type")
        event = data.get("event")
        
        if type_ == "event" and event == "connect.challenge":
            nonce = data["payload"]["nonce"]
            now_ms = int(time.time() * 1000)
            token_to_use = self.device_token if self.device_token else self.gateway_token
            
            sig_b64 = self.sign_challenge(nonce, now_ms, token_to_use)
            
            req = {
                "type": "req",
                "id": f"connect-{now_ms}",
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {"id": self.client_id, "version": "1.0.0", "platform": "windows", "mode": "node"},
                    "role": "node",
                    "scopes": [],
                    "caps": ["local-exec", "iot", "desktop"],
                    "commands": ["turn_on_plug", "turn_off_plug", "open_app", "close_app", "run_command", "get_status"],
                    "permissions": {},
                    "auth": {"token": token_to_use},
                    "locale": "pt-BR",
                    "userAgent": "conceitto-worker/1.0.0",
                    "device": {
                        "id": self.device_id,
                        "publicKey": self.pubkey_b64,
                        "signature": sig_b64,
                        "signedAt": now_ms,
                        "nonce": nonce
                    }
                }
            }
            await ws.send(json.dumps(req))
            
        elif type_ == "res" and data.get("payload", {}).get("type") == "hello-ok":
            print("✅ [IoT Bridge] Autenticado no Cérebro (Hello-OK recebido)!")
            self.device_token = data["payload"]["auth"].get("deviceToken", self.device_token)
            
            await ws.send(json.dumps({
                "type": "event",
                "event": "node.ready",
                "payload": {"worker_id": self.worker_id, "status": "online", "platform": "Windows"}
            }))

        elif type_ == "event" and event == "ping":
            # FIX #3: responder com type "res" usando o id do evento recebido
            await ws.send(json.dumps({
                "type": "res",
                "id": data.get("id", f"pong-{int(time.time())}"),
                "ok": True,
                "payload": {"ts": data.get("payload", {}).get("ts", int(time.time() * 1000))}
            }))

        elif type_ == "event" and event == "node.invoke.request":
            # FIX #1: evento correto é "node.invoke.request", não "node.invoke"
            # FIX #2: payload usa "id" (não "requestId") e "paramsJSON" (string JSON, não objeto)
            req_id  = data["payload"]["id"]
            node_id = data["payload"]["nodeId"]
            cmd     = data["payload"]["command"]

            params_json = data["payload"].get("paramsJSON")
            params = json.loads(params_json) if params_json else {}
            
            print(f"\n🔔 [Ação PUSH do Cérebro] Comando: {cmd} | Params: {params}")
            
            try:
                if cmd == "open_app" and "name" in params:
                    if params["name"].lower() == "notepad":
                        subprocess.Popen(["notepad.exe"])
                elif cmd == "lock_screen":
                    subprocess.run("rundll32.exe user32.dll,LockWorkStation")
                elif cmd == "turn_on_plug":
                    print(f"👉 Ligando tomada inteligente IP: {params.get('ip')}")
                
                # FIX #2b: result usa "id" (não "requestId"), "nodeId" obrigatório, "payload" (não "result")
                await ws.send(json.dumps({
                    "type": "req",
                    "id": f"res-{req_id}-{int(time.time())}",
                    "method": "node.invoke.result",
                    "params": {
                        "id": req_id,
                        "nodeId": node_id,
                        "ok": True,
                        "payload": {"status": "done", "output": f"Comando {cmd} executado localmente."}
                    }
                }))
            except Exception as e:
                await ws.send(json.dumps({
                    "type": "req",
                    "id": f"res-{req_id}-{int(time.time())}",
                    "method": "node.invoke.result",
                    "params": {
                        "id": req_id,
                        "nodeId": node_id,
                        "ok": False,
                        "error": {"code": "exec_error", "message": str(e)}
                    }
                }))

    def start(self):
        def run_it():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect_loop())
            
        t = threading.Thread(target=run_it, daemon=True)
        t.start()
