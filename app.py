from flask import Flask, request, jsonify, render_template
from datetime import datetime
import re
import json
import os

app = Flask(__name__)
SERVER_IP = "192.168.1.41"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RULES_FILE = os.path.join(BASE_DIR, "rules.json")
LOGS_FILE = os.path.join(BASE_DIR, "logs.json")
CLIENTS_FILE = os.path.join(BASE_DIR, "clients.json")

print("[INFO] Carpeta del proyecto:", BASE_DIR)


def load_json_file(filename, default_value):
    if not os.path.exists(filename):
        return default_value

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"[!] Error leyendo {filename}. Se usará valor por defecto.")
        return default_value


def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_all_data():
    save_json_file(RULES_FILE, rules)
    save_json_file(LOGS_FILE, logs)
    save_json_file(CLIENTS_FILE, clients)
# =========================
# BASES DE DATOS TEMPORALES
# =========================

default_rules = [
    {
        "id": 1,
        "name": "Permitir UDP base puerto 6000",

        "ingress_port": "ANY",
        "mac_src": "ANY",
        "mac_dst": "ANY",
        "eth_type": "IPv4",
        "vlan_id": "ANY",
        "vlan_priority": "ANY",

        "src_ip": "ANY",
        "dst_ip": "ANY",
        "protocol": "UDP",
        "src_port": "ANY",
        "dst_port": 6000,

        "port": 6000,

        "ip_tos": "ANY",

        "action": "ALLOW",
        "priority": 1,

        "matches": 0,
        "bytes": 0
    }
]

clients = load_json_file(CLIENTS_FILE, [])
rules = load_json_file(RULES_FILE, default_rules)
logs = load_json_file(LOGS_FILE, [])
save_all_data()

def normalize_rules():
    for rule in rules:
        rule.setdefault("name", f"Regla {rule.get('id', '')}")

        rule.setdefault("ingress_port", "ANY")
        rule.setdefault("mac_src", "ANY")
        rule.setdefault("mac_dst", "ANY")
        rule.setdefault("eth_type", "IPv4")
        rule.setdefault("vlan_id", "ANY")
        rule.setdefault("vlan_priority", "ANY")

        rule.setdefault("src_ip", "ANY")
        rule.setdefault("dst_ip", "ANY")
        rule.setdefault("protocol", "UDP")

        rule.setdefault("src_port", "ANY")

        if "dst_port" not in rule:
            rule["dst_port"] = rule.get("port", "ANY")

        if "port" not in rule:
            rule["port"] = rule.get("dst_port", "ANY")

        rule.setdefault("ip_tos", "ANY")

        rule.setdefault("action", "ALLOW")
        rule.setdefault("priority", 1)

        rule.setdefault("matches", 0)
        rule.setdefault("bytes", 0)


normalize_rules()
save_json_file(RULES_FILE, rules)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/server-info', methods=['GET'])
def server_info():
    return jsonify({
        "server_ip": SERVER_IP
    })
# =========================
# REGISTRAR CLIENTE
# =========================

@app.route('/register', methods=['POST'])
def register_client():

    data = request.json

    name = data.get("name")
    ip = data.get("ip")

    for client in clients:
        if client["name"] == name:
            client["ip"] = ip
            client["status"] = "ACTIVE"
            client["last_seen"] = str(datetime.now())

            save_json_file(CLIENTS_FILE, clients)

            print(f"[~] Cliente actualizado: {client}")

            return jsonify({
                "message": "Cliente actualizado correctamente"
            }), 200

    client = {
        "name": name,
        "ip": ip,
        "status": "ACTIVE",
        "last_seen": str(datetime.now())
    }

    clients.append(client)

    save_json_file(CLIENTS_FILE, clients)

    print(f"[+] Cliente registrado: {client}")

    return jsonify({
        "message": "Cliente registrado correctamente"
    }), 200

# =========================
# VER CLIENTES
# =========================

@app.route('/clients', methods=['GET'])
def get_clients():
    return jsonify(clients)

# =========================
# OBTENER REGLAS
# =========================

@app.route('/rules', methods=['GET'])
def get_rules():

    # ordenar por prioridad
    sorted_rules = sorted(
        rules,
        key=lambda x: x['priority'],
        reverse=True
    )

    return jsonify(sorted_rules)

# =========================
# AGREGAR REGLA
# =========================

@app.route('/rules', methods=['POST'])
def add_rule():

    data = request.json

    next_id = max([rule["id"] for rule in rules], default=0) + 1

    dst_port = data.get("dst_port", data.get("port", 6000))

    rule = {
        "id": next_id,
        "name": data.get("name", f"Regla {next_id}"),

        "ingress_port": data.get("ingress_port", "ANY"),
        "mac_src": data.get("mac_src", "ANY"),
        "mac_dst": data.get("mac_dst", "ANY"),
        "eth_type": data.get("eth_type", "IPv4"),
        "vlan_id": data.get("vlan_id", "ANY"),
        "vlan_priority": data.get("vlan_priority", "ANY"),

        "src_ip": data.get("src_ip", "ANY"),
        "dst_ip": data.get("dst_ip", "ANY"),
        "protocol": data.get("protocol", "UDP"),
        "src_port": data.get("src_port", "ANY"),
        "dst_port": dst_port,

        # Compatibilidad con el cliente actual
        "port": dst_port,

        "ip_tos": data.get("ip_tos", "ANY"),

        "action": data.get("action", "ALLOW"),
        "priority": data.get("priority", 1),

        "matches": 0,
        "bytes": 0
    }

    rules.append(rule)

    save_json_file(RULES_FILE, rules)

    print(f"[+] Nueva regla: {rule}")

    return jsonify({
        "message": "Regla agregada"
    }), 200



# =========================
# REPORTES DEL CLIENTE
# =========================

@app.route('/report', methods=['POST'])
def report():

    data = request.json

    message = data.get("message", "")

    event = {
        "time": str(datetime.now()),
        "client": data.get("client"),
        "message": message
    }

    logs.append(event)

    # Intentar extraer el ID de la regla desde el mensaje:
    # Ejemplo: "Regla 6 coincidió | src=..."
    match = re.search(r"Regla\s+(\d+)\s+coincidió", message)
    bytes_match = re.search(r"bytes=(\d+)", message)

    packet_bytes = int(bytes_match.group(1)) if bytes_match else 0

    if match:
        rule_id = int(match.group(1))

        for rule in rules:
            if rule["id"] == rule_id:
                rule["matches"] = rule.get("matches", 0) + 1
                rule["bytes"] = rule.get("bytes", 0) + packet_bytes

                print(
                    f"[COUNT] Regla {rule_id} ahora tiene "
                    f"{rule['matches']} coincidencia(s) y "
                    f"{rule['bytes']} bytes"
                )
                break

    save_json_file(LOGS_FILE, logs)
    save_json_file(RULES_FILE, rules)

    print(f"[REPORT] {event}")

    return jsonify({
        "message": "Reporte recibido"
    }), 200

@app.route('/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    global rules

    original_count = len(rules)

    rules = [
        rule for rule in rules
        if rule["id"] != rule_id
    ]

    if len(rules) == original_count:
        return jsonify({
            "message": "Regla no encontrada"
        }), 404
    
    save_json_file(RULES_FILE, rules)

    print(f"[-] Regla eliminada: {rule_id}")

    return jsonify({
        "message": "Regla eliminada correctamente"
    }), 200

# =========================
# VER LOGS
# =========================

@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify(logs)

# =========================
# INICIAR SERVIDOR
# =========================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )