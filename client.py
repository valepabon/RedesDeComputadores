import socket
import requests
import time
import select
import threading

# =========================
# CONFIGURACIÓN DEL CLIENTE
# =========================

CLIENT_NAME = "cliente_pc_1"

# IP del servidor controlador
SERVER_URL = "http://192.168.1.41:5000"

# IP real de este cliente
CLIENT_IP = "192.168.1.54"

# IP donde escucha este cliente
LISTEN_IP = "0.0.0.0"

# Puertos UDP que este cliente va a escuchar
LISTEN_PORTS = [6000, 6001, 6002]

TCP_LISTEN_PORTS = [7000, 7001, 7002]

# Cada cuántos segundos actualiza reglas
RULE_REFRESH_INTERVAL = 5

rules = []


# =========================
# REGISTRAR CLIENTE
# =========================

def register_client():
    data = {
        "name": CLIENT_NAME,
        "ip": CLIENT_IP
    }

    try:
        response = requests.post(
            f"{SERVER_URL}/register",
            json=data,
            timeout=3
        )

        if response.status_code == 200:
            print("[+] Cliente registrado correctamente")
        else:
            print("[!] Error registrando cliente:", response.text)

    except requests.exceptions.RequestException as e:
        print("[!] No se pudo conectar con el servidor:", e)


# =========================
# OBTENER REGLAS
# =========================

def fetch_rules():
    global rules

    try:
        response = requests.get(
            f"{SERVER_URL}/rules",
            timeout=3
        )

        if response.status_code == 200:
            rules = response.json()
            print(f"[+] Reglas actualizadas: {len(rules)} regla(s)")
        else:
            print("[!] Error obteniendo reglas:", response.text)

    except requests.exceptions.RequestException as e:
        print("[!] No se pudieron obtener reglas:", e)


# =========================
# ENVIAR REPORTE
# =========================

def send_report(message):
    data = {
        "client": CLIENT_NAME,
        "message": message
    }

    try:
        requests.post(
            f"{SERVER_URL}/report",
            json=data,
            timeout=3
        )
    except requests.exceptions.RequestException as e:
        print("[!] No se pudo enviar reporte:", e)


# =========================
# COMPARAR UNA REGLA
# =========================

def match_rule(rule, src_ip, dst_ip, protocol, port):
    rule_src_ip = rule.get("src_ip", "ANY")
    rule_dst_ip = rule.get("dst_ip", "ANY")
    rule_protocol = rule.get("protocol", "ANY")
    rule_port = rule.get("port", "ANY")

    if rule_src_ip != "ANY" and rule_src_ip != src_ip:
        return False

    if rule_dst_ip != "ANY" and rule_dst_ip != dst_ip:
        return False

    if rule_protocol != "ANY" and rule_protocol.upper() != protocol.upper():
        return False

    if rule_port != "ANY" and int(rule_port) != int(port):
        return False

    return True


# =========================
# EVALUAR PAQUETE
# =========================

def evaluate_packet(src_ip, dst_ip, protocol, port, payload):
    for rule in rules:
        if match_rule(rule, src_ip, dst_ip, protocol, port):
            action = rule.get("action", "ALLOW").upper()

            event = (
                f"Regla {rule.get('id')} coincidió | "
                f"src={src_ip} dst={dst_ip} "
                f"proto={protocol} port={port} "
                f"action={action} payload={payload}"
            )

            if action == "ALLOW":
                print("[ALLOW]", event)
                send_report(event)
                return "ALLOW"

            elif action == "BLOCK":
                print("[BLOCK]", event)
                send_report(event)
                return "BLOCK"

            elif action == "REPORT":
                print("[REPORT]", event)
                send_report(event)
                return "REPORT"

    event = (
        f"Sin coincidencia | "
        f"src={src_ip} dst={dst_ip} "
        f"proto={protocol} port={port} "
        f"action=ALLOW_DEFAULT payload={payload}"
    )

    print("[ALLOW_DEFAULT]", event)
    send_report(event)

    return "ALLOW"


# =========================
# CREAR SOCKETS UDP
# =========================

def create_udp_sockets():
    sockets = []

    for port in LISTEN_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, port))
        sockets.append(sock)

        print(f"[+] Escuchando UDP en {LISTEN_IP}:{port}")

    return sockets


# =========================
# ESCUCHAR VARIOS PUERTOS
# =========================

def start_udp_listener():
    sockets = create_udp_sockets()

    last_rule_update = 0

    print("[+] Cliente multipuerto iniciado")

    while True:
        try:
            now = time.time()

            if now - last_rule_update >= RULE_REFRESH_INTERVAL:
                fetch_rules()
                last_rule_update = now

            readable_sockets, _, _ = select.select(
                sockets,
                [],
                [],
                1
            )

            for sock in readable_sockets:
                data, addr = sock.recvfrom(4096)

                src_ip = addr[0]
                src_port = addr[1]

                dst_ip = CLIENT_IP
                protocol = "UDP"

                # Puerto local donde llegó el paquete
                dst_port = sock.getsockname()[1]

                payload = data.decode(errors="ignore")

                decision = evaluate_packet(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    protocol=protocol,
                    port=dst_port,
                    payload=payload
                )

                if decision == "ALLOW":
                    print(f"[RECIBIDO] {src_ip}:{src_port} -> {CLIENT_IP}:{dst_port} | {payload}")

                elif decision == "REPORT":
                    print(f"[RECIBIDO Y REPORTADO] {src_ip}:{src_port} -> {CLIENT_IP}:{dst_port} | {payload}")

                elif decision == "BLOCK":
                    print(f"[DESCARTADO] Paquete bloqueado de {src_ip}:{src_port} hacia puerto {dst_port}")

        except KeyboardInterrupt:
            print("\n[!] Cliente detenido")
            break

# =========================
# ESCUCHAR TRÁFICO TCP
# =========================

def handle_tcp_client(conn, addr, dst_port):
    try:
        data = conn.recv(4096)

        if not data:
            conn.close()
            return

        src_ip = addr[0]
        src_port = addr[1]
        dst_ip = CLIENT_IP
        protocol = "TCP"
        payload = data.decode(errors="ignore")

        decision = evaluate_packet(
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=protocol,
            port=dst_port,
            payload=payload
        )

        if decision == "ALLOW":
            print(f"[TCP RECIBIDO] {src_ip}:{src_port} -> {CLIENT_IP}:{dst_port} | {payload}")
            conn.sendall(b"ALLOW")

        elif decision == "REPORT":
            print(f"[TCP RECIBIDO Y REPORTADO] {src_ip}:{src_port} -> {CLIENT_IP}:{dst_port} | {payload}")
            conn.sendall(b"REPORT")

        elif decision == "BLOCK":
            print(f"[TCP BLOQUEADO] Conexion de {src_ip}:{src_port} hacia puerto {dst_port}")
            conn.sendall(b"BLOCK")

    except OSError as e:
        print(f"[!] Error manejando conexion TCP: {e}")

    finally:
        conn.close()


def start_tcp_listener_for_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Permite reutilizar el puerto si reinicias el programa
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind((LISTEN_IP, port))
    sock.listen(5)

    print(f"[+] Escuchando TCP en {LISTEN_IP}:{port}")

    while True:
        try:
            conn, addr = sock.accept()

            thread = threading.Thread(
                target=handle_tcp_client,
                args=(conn, addr, port),
                daemon=True
            )

            thread.start()

        except OSError as e:
            print(f"[!] Error en listener TCP puerto {port}: {e}")


def start_tcp_listeners():
    for port in TCP_LISTEN_PORTS:
        thread = threading.Thread(
            target=start_tcp_listener_for_port,
            args=(port,),
            daemon=True
        )

        thread.start()

# =========================
# PROGRAMA PRINCIPAL
# =========================

if __name__ == "__main__":
    print("Cliente SDN multiprotocolo iniciado")
    register_client()
    fetch_rules()

    start_tcp_listeners()

    start_udp_listener()