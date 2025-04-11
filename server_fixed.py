from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
import uvicorn
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Modelo para os dados recebidos na API
class ImageData(BaseModel):
    screen_id: str
    image_data: str

app = FastAPI(title="HayDay WebSocket Server")

# Armazenar conexões WebSocket ativas
active_connections: List[WebSocket] = []
connection_info: Dict[WebSocket, str] = {}  # Armazena info adicional sobre cada conexão

@app.get("/")
async def get_status():
    """Retorna o status do servidor e as conexões ativas"""
    # Lista as conexões ativas com identificação
    connections = [{"id": connection_info.get(conn, "unknown")} for conn in active_connections]
    
    return {
        "status": "online",
        "active_connections": len(active_connections),
        "connections": connections
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para conexões do frontend"""
    await websocket.accept()
    active_connections.append(websocket)
    connection_info[websocket] = f"viewer-{len(active_connections)}"
    
    try:
        # Notifica sobre a conexão
        print(f"👤 Nova conexão WebSocket estabelecida. Total: {len(active_connections)}")
        
        # Mantém a conexão aberta e recebe mensagens
        while True:
            # Recebe dados (pode ser texto ou imagem base64)
            data = await websocket.receive_text()
            
            # Tenta processar como JSON
            try:
                message = json.loads(data)
                # Se for um ping, responde com pong
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "time": datetime.now().isoformat()})
                # Se for uma identificação, registra
                elif message.get("type") == "identify" and message.get("id"):
                    connection_info[websocket] = message.get("id")
                    print(f"👤 Cliente identificado como: {message.get('id')}")
                # Se for uma imagem, envia para todos os clientes
                elif message.get("type") == "image" and message.get("data"):
                    await broadcast_image(message.get("data"), message.get("id", "screen"))
            except Exception as e:
                print(f"Erro ao processar mensagem WebSocket: {e}")
                
    except WebSocketDisconnect:
        # Remove a conexão quando desconectada
        if websocket in active_connections:
            client_id = connection_info.get(websocket, "unknown")
            active_connections.remove(websocket)
            if websocket in connection_info:
                del connection_info[websocket]
            print(f"👤 Conexão WebSocket '{client_id}' fechada. Restantes: {len(active_connections)}")

# API para receber imagens do bot - USANDO OBJETO JSON
@app.post("/api/send-image")
async def send_image(data: ImageData):
    """Recebe uma imagem base64 como JSON e envia para todos os clientes WebSocket"""
    print(f"📸 Recebida imagem de {data.screen_id}, enviando para {len(active_connections)} clientes")
    
    # Broadcast para todos os clientes conectados
    await broadcast_image(data.image_data, data.screen_id)
    return {"success": True, "sent_to": len(active_connections)}

# Função para enviar imagem para todos os clientes
async def broadcast_image(image_data: str, screen_id: str):
    """Envia uma imagem para todos os clientes WebSocket"""
    timestamp = datetime.now().isoformat()
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": "image",
                "id": screen_id,
                "data": image_data,
                "timestamp": timestamp
            })
        except Exception as e:
            print(f"Erro ao enviar para cliente: {e}")
            disconnected.append(connection)
    
    # Remove conexões que falharam
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)
            if conn in connection_info:
                del connection_info[conn]

if __name__ == "__main__":
    # Define caminhos para certificados SSL
    cert_dir = Path("/etc/ssl/hayday")
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"
    
    # Verifica se os certificados existem
    ssl_available = cert_file.exists() and key_file.exists()
    
    # Parâmetros para uvicorn
    params = {
        "app": app,
        "host": "0.0.0.0",
        "port": 8000
    }
    
    # Adiciona SSL se os certificados existirem
    if ssl_available:
        print("🔒 Certificados SSL encontrados, iniciando com HTTPS/WSS")
        params["ssl_keyfile"] = str(key_file)
        params["ssl_certfile"] = str(cert_file)
    else:
        print("⚠️ Certificados SSL não encontrados, iniciando sem segurança")
        print(f"Procurando certificados em: {cert_dir}")
    
    print("🚀 Iniciando servidor WebSocket HayDay na porta 8000...")
    uvicorn.run(**params)
