import requests
import json
import logging
import pyodbc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .. import models

logger = logging.getLogger("chatbot")

# Evolution API Endpoint Constants
EVOLUTION_CREATE_INSTANCE_URL = "/instance/create"
EVOLUTION_SEND_TEXT_URL = "/message/sendText"

def get_chatbot_config(db: Session) -> models.ChatbotConfig:
    """Obtiene la configuración activa del chatbot. Si no existe, crea una por defecto."""
    config = db.query(models.ChatbotConfig).first()
    if not config:
        config = models.ChatbotConfig(
            db_host="192.168.1.48",
            db_name="carmal_a",
            db_user="PROFIT",
            db_password="profit",
            whatsapp_number="+5804241931896",
            ai_provider="gemini",
            ollama_api_url="http://192.168.1.79:11434",
            whatsapp_gateway_url="http://192.168.1.79:8050",
            whatsapp_gateway_token="carmal_token_2026",
            is_active=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def test_db_connection(host, name, user, password) -> bool:
    """Prueba la conexión a la base de datos SQL Server (Profit Plus)."""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={host};"
        f"DATABASE={name};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=3;"
    )
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        logger.error(f"Error en test_db_connection: {e}")
        return False

def get_profit_zones(config: models.ChatbotConfig) -> list:
    """Obtiene todas las zonas activas desde la base de datos saZona en SQL Server."""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={config.db_host};"
        f"DATABASE={config.db_name};"
        f"UID={config.db_user};"
        f"PWD={config.db_password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=5;"
    )
    zones = []
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT co_zon, zon_des FROM saZona WHERE inactivo = 0")
        for row in cursor.fetchall():
            zones.append({
                "co_zon": str(row[0]).strip(),
                "zon_des": str(row[1]).strip()
            })
        conn.close()
    except Exception as e:
        logger.error(f"Error al obtener zonas de Profit Plus: {e}")
    return zones

def get_salesman_for_zone(config: models.ChatbotConfig, co_zon: str) -> dict:
    """Busca al vendedor que tiene más clientes registrados en la zona especificada."""
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={config.db_host};"
        f"DATABASE={config.db_name};"
        f"UID={config.db_user};"
        f"PWD={config.db_password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=5;"
    )
    vendedor = None
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Consulta para encontrar el vendedor representativo en esa zona
        query = """
            SELECT TOP 1 c.co_ven, v.ven_des, v.telefonos 
            FROM saCliente c
            JOIN saVendedor v ON c.co_ven = v.co_ven
            WHERE c.co_zon = ? AND v.inactivo = 0
            GROUP BY c.co_ven, v.ven_des, v.telefonos
            ORDER BY COUNT(*) DESC
        """
        cursor.execute(query, (co_zon,))
        row = cursor.fetchone()
        if row:
            vendedor = {
                "co_ven": str(row[0]).strip(),
                "ven_des": str(row[1]).strip(),
                "telefonos": str(row[2]).strip() if row[2] else ""
            }
        conn.close()
    except Exception as e:
        logger.error(f"Error al buscar vendedor para zona {co_zon}: {e}")
    return vendedor

def ask_ai(config: models.ChatbotConfig, prompt: str, system_instruction: str = None) -> str:
    """Consume Gemini API u Ollama local de forma simplificada por peticiones HTTP."""
    if config.ai_provider == "gemini":
        if not config.gemini_api_key:
            logger.warning("Falta la API Key de Gemini. Usando fallback.")
            return "NONE"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={config.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Estructura de la petición para Gemini
        contents = [{"parts": [{"text": prompt}]}]
        if system_instruction:
            system_instruction_part = {"parts": [{"text": system_instruction}]}
            payload = {
                "contents": contents,
                "systemInstruction": system_instruction_part
            }
        else:
            payload = {"contents": contents}
            
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                res_data = res.json()
                text_out = res_data['candidates'][0]['content']['parts'][0]['text']
                return text_out.strip()
            else:
                logger.error(f"Error de Gemini API: {res.status_code} - {res.text}")
                return "NONE"
        except Exception as e:
            logger.error(f"Excepción al llamar a Gemini: {e}")
            return "NONE"
            
    elif config.ai_provider == "ollama":
        url = f"{config.ollama_api_url}/api/chat"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "llama3", # Modelo recomendado
            "messages": messages,
            "stream": False
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                res_data = res.json()
                return res_data['message']['content'].strip()
            else:
                logger.error(f"Error de Ollama API: {res.status_code} - {res.text}")
                return "NONE"
        except Exception as e:
            logger.error(f"Excepción al llamar a Ollama: {e}")
            return "NONE"
            
    return "NONE"

def match_zone_semantically(config: models.ChatbotConfig, user_input: str) -> dict:
    """Realiza coincidencia inteligente/semántica de zonas usando la base de datos y la IA."""
    zones = get_profit_zones(config)
    if not zones:
        return None
        
    # 1. Coincidencia Directa por Texto
    input_lower = user_input.lower().strip()
    for z in zones:
        desc_lower = z['zon_des'].lower()
        # Si la descripción de la zona está contenida en la entrada del usuario (ej: "Guarenas")
        if desc_lower in input_lower or input_lower in desc_lower:
            logger.info(f"Match directo encontrado: {z['zon_des']} -> {z['co_zon']}")
            return z
            
    # 2. Match Semántico mediante Inteligencia Artificial
    system_instruction = (
        "Eres el clasificador geográfico de Inv. Carmal 5537, C.A. Tu tarea es analizar "
        "la ubicación que describe el usuario e indicar a cuál zona comercial de la lista pertenece.\n"
        "Reglas:\n"
        "1. Devuelve ÚNICAMENTE el código co_zon exacto. Ningún saludo ni explicación.\n"
        "2. Si la ubicación no tiene ninguna relación con las zonas comerciales de la lista, responde exactamente con la palabra 'NONE'.\n"
        "3. Sé preciso y evalúa la similitud (ej. estados, ciudades cercanas o municipios correspondientes)."
    )
    
    # Formatear la lista de zonas para el prompt
    zones_list_str = "\n".join([f"- Código: {z['co_zon']} | Nombre: {z['zon_des']}" for z in zones])
    prompt = (
        f"LISTA DE ZONAS DISPONIBLES:\n{zones_list_str}\n\n"
        f"UBICACIÓN DEL CLIENTE: '{user_input}'\n\n"
        f"Responde con el código de la zona que corresponda mejor o 'NONE':"
    )
    
    ai_response = ask_ai(config, prompt, system_instruction)
    ai_response_clean = ai_response.replace('"', '').replace("'", "").strip()
    
    logger.info(f"Respuesta IA de matching: '{ai_response_clean}'")
    
    if ai_response_clean != "NONE":
        # Validar que el código devuelto existe en nuestra lista
        for z in zones:
            if z['co_zon'] == ai_response_clean:
                logger.info(f"Match semántico de IA validado: {z['zon_des']} ({z['co_zon']})")
                return z
                
    return None

def is_saved_contact(config: models.ChatbotConfig, phone_number: str) -> bool:
    """
    Verifica si el número de teléfono ya se encuentra registrado en los contactos del celular corporativo.
    Se conecta a Evolution API para buscar si existe el contacto.
    """
    # Limpiar el número de teléfono
    clean_num = phone_number.replace("+", "").replace(" ", "").split("@")[0]
    
    gateway_url = config.whatsapp_gateway_url.rstrip("/")
    # Endpoint de Evolution API para verificar contacto
    url = f"{gateway_url}/contact/search/carmal_bot"
    headers = {
        "apikey": "carmal_whatsapp_secure_key_2026",
        "Content-Type": "application/json"
    }
    params = {"number": clean_num}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            # Si el endpoint devuelve datos del contacto y tiene nombre asignado en la agenda
            if data and isinstance(data, dict):
                # Si name existe y no es el número telefónico directamente
                name = data.get("name")
                pushname = data.get("pushName")
                logger.info(f"Búsqueda de contacto para {phone_number}: name='{name}', pushname='{pushname}'")
                
                # Si está guardado en la agenda (típicamente tiene un name local guardado)
                if name and not name.startswith("+") and name != clean_num:
                    logger.info(f"El número {phone_number} es un contacto guardado ('{name}'). No se le auto-responderá.")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                contact = data[0]
                name = contact.get("name")
                if name and not name.startswith("+") and name != clean_num:
                    logger.info(f"El número {phone_number} es un contacto guardado ('{name}'). No se le auto-responderá.")
                    return True
        else:
            logger.warning(f"Error al verificar contacto en Gateway: status={res.status_code}")
    except Exception as e:
        logger.error(f"Error al verificar contacto {phone_number} en Gateway: {e}")
        
    return False

def send_whatsapp_message(config: models.ChatbotConfig, to_phone: str, text: str) -> bool:
    """Envía un mensaje de texto de WhatsApp mediante el Gateway (Evolution API)."""
    gateway_url = config.whatsapp_gateway_url.rstrip("/")
    url = f"{gateway_url}{EVOLUTION_SEND_TEXT_URL}/carmal_bot"
    
    clean_num = to_phone.replace("+", "").replace(" ", "").split("@")[0]
    if not clean_num.endswith("@s.whatsapp.net"):
        clean_num = f"{clean_num}@s.whatsapp.net"
        
    headers = {
        "apikey": "carmal_whatsapp_secure_key_2026",
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": clean_num,
        "options": {
            "delay": 1200,
            "presence": "composing"
        },
        "textMessage": {
            "text": text
        }
    }
    
    try:
        logger.info(f"Enviando WhatsApp a {clean_num}...")
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code in [200, 201]:
            logger.info(f"Mensaje enviado exitosamente a {clean_num}")
            return True
        else:
            logger.error(f"Error enviando mensaje: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al enviar WhatsApp: {e}")
        return False

def process_incoming_message(db: Session, sender_phone: str, message_body: str) -> dict:
    """
    Procesa los mensajes entrantes de WhatsApp de forma asíncrona.
    Maneja el estado del cliente y da respuestas automáticas si es un cliente nuevo.
    """
    config = get_chatbot_config(db)
    if not config.is_active:
        return {"status": "inactive"}
        
    # Limpieza del teléfono
    sender_clean = sender_phone.replace("+", "").replace(" ", "").split("@")[0]
    
    # Ignorar mensajes enviados desde el número corporativo del bot
    bot_clean = config.whatsapp_number.replace("+", "").replace(" ", "")
    if sender_clean == bot_clean:
        return {"status": "self_ignore"}
        
    # Verificar si es un contacto guardado en la agenda para filtrarlo
    if is_saved_contact(config, sender_phone):
        return {"status": "saved_contact_ignored"}
        
    # Buscar o crear la sesión de conversación del cliente
    session = db.query(models.ChatbotSession).filter(models.ChatbotSession.phone_number == sender_clean).first()
    if not session:
        session = models.ChatbotSession(phone_number=sender_clean, state="START")
        db.add(session)
        db.commit()
        db.refresh(session)
        
    logger.info(f"Procesando mensaje de chatbot para {sender_clean}. Estado actual: {session.state}")
    
    # --- MÁQUINA DE ESTADOS ---
    
    if session.state == "START":
        # Enviar mensaje de bienvenida y solicitar la zona
        welcome_text = (
            "¡Hola! Qué gusto saludarte. ✨\n\n"
            "Te damos una muy cálida bienvenida a *Inv. Carmal 5537, C.A.*\n"
            "Contamos con una gran amplitud de catálogo de productos de excelente calidad, "
            "y nos encantaría brindarte la experiencia de ser parte de nuestra gran familia de clientes.\n\n"
            "Para poder asignarte al asesor de ventas adecuado y darte la mejor atención, por favor dinos: "
            "*¿En qué zona o localidad te encuentras?* 📍\n\n"
            "_(Te sugerimos indicarnos tu: **Estado**, **Ciudad** y **Sector/Parroquia**. "
            "Por ejemplo: 'Miranda, Guarenas, Las Clavellinas' o 'Caracas, Petare, La Dolorita')_"
        )
        send_whatsapp_message(config, sender_phone, welcome_text)
        
        # Transicionar al estado de espera de zona
        session.state = "AWAITING_LOCATION"
        db.commit()
        return {"status": "welcomed"}
        
    elif session.state == "AWAITING_LOCATION":
        # El cliente responde con su ubicación, intentamos hacer match de zona
        matched_zone = match_zone_semantically(config, message_body)
        
        if matched_zone:
            co_zon = matched_zone['co_zon']
            zon_des = matched_zone['zon_des']
            
            # Buscar el vendedor para esta zona
            vendedor = get_salesman_for_zone(config, co_zon)
            
            # Datos por defecto si no hay vendedor
            vendedor_name = "Gerencia de Ventas"
            vendedor_phone = "584241931896"
            
            if vendedor:
                vendedor_name = vendedor['ven_des']
                # Formatear el teléfono para wa.me (debe ser numérico con código de país sin símbolos)
                raw_phone = vendedor['telefonos'].replace("+", "").replace("-", "").replace(" ", "").strip()
                if raw_phone:
                    # Si no empieza con 58 y es un número celular típico de Venezuela (0412, 0414, 0424, 0416)
                    if not raw_phone.startswith("58") and (raw_phone.startswith("04") or raw_phone.startswith("4")):
                        if raw_phone.startswith("0"):
                            raw_phone = "58" + raw_phone[1:]
                        else:
                            raw_phone = "58" + raw_phone
                    vendedor_phone = raw_phone
                    
            # Formatear el teléfono para mostrarlo al usuario de forma amigable (ej: 0412-9707230)
            friendly_phone = vendedor_phone
            if vendedor_phone.startswith("58") and len(vendedor_phone) >= 12:
                friendly_phone = f"0{vendedor_phone[2:5]}-{vendedor_phone[5:8]}{vendedor_phone[8:]}"
                
            assignment_text = (
                "¡Excelente noticia! Ya hemos ubicado tu zona en nuestro sistema. 📍✨\n\n"
                f"Tu asesor comercial asignado es **{vendedor_name}**. Él/Ella **ya se encuentra al tanto de tu caso y está a la espera de tu contacto** para brindarte una atención grata y totalmente personalizada. 🤝\n\n"
                "Puedes escribirle o llamarle directamente a su WhatsApp haciendo clic en este enlace:\n"
                f"👉 **https://wa.me/{vendedor_phone}**\n\n"
                f"O a su número telefónico directo: **{friendly_phone}**\n\n"
                "¡Estamos muy emocionados de que formes parte de nuestra gran familia de clientes y apoyarte en el crecimiento de tu negocio! 🚀📦"
            )
            
            # Guardar datos en la sesión
            session.state = "COMPLETED"
            session.vendedor_name = vendedor_name
            session.vendedor_phone = vendedor_phone
            session.zona_code = co_zon
            session.zona_name = zon_des
            db.commit()
            
            # Enviar el mensaje de asignación
            send_whatsapp_message(config, sender_phone, assignment_text)
            return {"status": "assigned", "vendedor": vendedor_name, "zone": zon_des}
            
        else:
            # Si no entendió la zona, re-preguntar usando la IA de forma empática
            system_instruction = (
                "Eres el asistente de Inv. Carmal 5537, C.A. El usuario nos indicó su ubicación "
                "pero no pudimos encontrar una coincidencia en nuestra base de datos. Pídele amablemente "
                "que sea más específico con su ubicación, mencionando estados importantes o ciudades principales de Venezuela.\n"
                "Mantén un tono muy cálido, grato y totalmente personalizado. No uses la palabra 'humanizada' en ningún momento."
            )
            prompt = f"Ubicación no entendida proporcionada por el usuario: '{message_body}'. Genera un mensaje corto y amable para pedir aclaración."
            ai_retry_text = ask_ai(config, prompt, system_instruction)
            
            # Fallback si falla la IA
            if ai_retry_text == "NONE" or not ai_retry_text:
                ai_retry_text = (
                    "¡Oh! No logramos ubicar esa zona en nuestro sistema. 📍\n\n"
                    "Para poder darte la atención grata y personalizada que te mereces, por favor, "
                    "¿podrías decirnos de forma más detallada en qué **Estado**, **Ciudad** o **Sector** de Venezuela te encuentras? "
                    "Así podremos asignarte correctamente a tu asesor comercial. ¡Muchas gracias! 😊"
                )
                
            send_whatsapp_message(config, sender_phone, ai_retry_text)
            return {"status": "retry_location"}
            
    elif session.state == "COMPLETED":
        # Si la conversación ya terminó, pero escriben después de un tiempo prudente (ej: 24 horas),
        # podemos reiniciar el ciclo. De lo contrario, respondemos de forma conversacional con la IA.
        time_elapsed = datetime.utcnow() - session.last_interaction.replace(tzinfo=None)
        
        if time_elapsed > timedelta(hours=24):
            # Reiniciar ciclo de bienvenida
            session.state = "START"
            db.commit()
            return process_incoming_message(db, sender_phone, message_body)
            
        # Responder conversacionalmente usando la IA
        system_instruction = (
            f"Eres el asistente de Inv. Carmal 5537, C.A. Ya le hemos asignado un vendedor a este cliente "
            f"(Vendedor: {session.vendedor_name}, WhatsApp: https://wa.me/{session.vendedor_phone}).\n"
            f"Tu tono debe ser muy profesional, atento, grato y totalmente personalizado.\n"
            f"Si el usuario tiene dudas adicionales, recuérdale amablemente que puede contactar directamente a su asesor. "
            f"No uses la palabra 'humanizada' bajo ninguna circunstancia."
        )
        ai_chat_response = ask_ai(config, message_body, system_instruction)
        
        if ai_chat_response == "NONE" or not ai_chat_response:
            ai_chat_response = (
                f"Recuerda que tu asesor asignado es **{session.vendedor_name}**. "
                f"Él/Ella está esperando tu contacto para ayudarte en lo que necesites. "
                f"Puedes escribirle directamente a su WhatsApp en este enlace: https://wa.me/{session.vendedor_phone} 📲"
            )
            
        send_whatsapp_message(config, sender_phone, ai_chat_response)
        return {"status": "chat_reply"}
        
    return {"status": "unknown"}
