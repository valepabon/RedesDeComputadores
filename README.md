# Red SDN con capacidades de firewall

Proyecto final de Redes de Computadores.

## Componentes

- Servidor controlador SDN en Flask.
- Clientes replicables en Python.
- Generador de tráfico UDP.
- Generador de tráfico TCP.
- Interfaz web para administración de reglas.
- Persistencia en archivos JSON.

## Funcionalidades

- Registro de clientes en LAN.
- Reglas de flujo con IP origen, IP destino, protocolo, puerto, acción y prioridad.
- Acciones: ALLOW, BLOCK y REPORT.
- Contadores de coincidencias por regla.
- Logs de eventos.
- Soporte UDP y TCP.
- Administración desde interfaz web.

## Ejecución

Servidor:

```bash
python app.py
python client.py
python udp_sender.py
python tcp_sender.py
