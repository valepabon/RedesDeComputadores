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
        "src_ip": "ANY",
        "dst_ip": "ANY",
        "protocol": "UDP",
        "port": 6000,
        "action": "ALLOW",
        "priority": 1,
        "matches": 0
    }
]

clients = load_json_file(CLIENTS_FILE, [])
rules = load_json_file(RULES_FILE, default_rules)
logs = load_json_file(LOGS_FILE, [])
save_all_data()

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

    rule = {
        "id": next_id,
        "src_ip": data.get("src_ip", "ANY"),
        "dst_ip": data.get("dst_ip", "ANY"),
        "protocol": data.get("protocol", "UDP"),
        "port": data.get("port", 6000),
        "action": data.get("action", "ALLOW"),
        "priority": data.get("priority", 1),
        "matches": 0
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

    if match:
        rule_id = int(match.group(1))

        for rule in rules:
            if rule["id"] == rule_id:
                rule["matches"] = rule.get("matches", 0) + 1
                print(f"[COUNT] Regla {rule_id} ahora tiene {rule['matches']} coincidencia(s)")
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