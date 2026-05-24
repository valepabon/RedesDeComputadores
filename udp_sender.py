import socket
import time
import requests

# =========================
# CONFIGURACIÓN
# =========================

SERVER_URL = "http://192.168.1.41:5000"


# =========================
# UTILIDADES
# =========================

def ask_input(message, default_value):
    value = input(f"{message} [{default_value}]: ").strip()

    if value == "":
        return default_value

    return value


def get_clients():
    try:
        response = requests.get(
            f"{SERVER_URL}/clients",
            timeout=3
        )

        if response.status_code == 200:
            return response.json()

        print("[!] Error consultando clientes:", response.text)
        return []

    except requests.exceptions.RequestException as e:
        print("[!] No se pudo conectar con el servidor:", e)
        return []


def select_client(clients):
    if not clients:
        print("[!] No hay clientes registrados en el servidor")
        return None

    print("\n=== Clientes registrados ===")

    for index, client in enumerate(clients, start=1):
        name = client.get("name", "SIN_NOMBRE")
        ip = client.get("ip", "SIN_IP")
        status = client.get("status", "UNKNOWN")
        last_seen = client.get("last_seen", "N/A")

        print(f"{index}. {name} | IP: {ip} | Estado: {status} | Última vez: {last_seen}")

    while True:
        option = input("\nSeleccione el número del cliente destino: ").strip()

        if not option.isdigit():
            print("[!] Debes ingresar un número")
            continue

        option = int(option)

        if 1 <= option <= len(clients):
            return clients[option - 1]

        print("[!] Opción fuera de rango")


# =========================
# ENVÍO UDP
# =========================

def send_udp(dest_ip, dest_port, count, interval, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\nEnviando tráfico UDP...")
    print(f"Destino: {dest_ip}:{dest_port}")
    print(f"Cantidad: {count}")
    print(f"Intervalo: {interval} segundos\n")

    for i in range(count):
        final_message = f"{message} #{i + 1}"

        sock.sendto(
            final_message.encode(),
            (dest_ip, dest_port)
        )

        print(f"[ENVIADO] {final_message} -> {dest_ip}:{dest_port}")

        time.sleep(interval)

    sock.close()

    print("\nEnvío finalizado")


# =========================
# PROGRAMA PRINCIPAL
# =========================

def main():
    print("=== Generador de tráfico UDP con clientes registrados ===")

    clients = get_clients()

    selected_client = select_client(clients)

    if selected_client is None:
        return

    dest_ip = selected_client.get("ip")

    print(f"\nCliente seleccionado: {selected_client.get('name')} - {dest_ip}")

    dest_port = int(ask_input("Puerto destino", "6000"))
    count = int(ask_input("Cantidad de mensajes", "5"))
    interval = float(ask_input("Intervalo entre mensajes en segundos", "1"))
    message = ask_input("Mensaje", "Hola desde el generador UDP")

    send_udp(
        dest_ip=dest_ip,
        dest_port=dest_port,
        count=count,
        interval=interval,
        message=message
    )


if __name__ == "__main__":
    main()