#!/bin/bash
set -e

BENCH_DIR="/home/frappe/data/frappe-bench"

# === TRUCO DE PERMISOS: Si somos ROOT, reparamos y cambiamos a usuario frappe ===
if [ "$(id -u)" = "0" ]; then
    echo "===================================================="
    echo " [Docker] Detectado acceso Root. Corrigiendo permisos..."
    echo "===================================================="
    mkdir -p /home/frappe/data
    chown -R frappe:frappe /home/frappe/data
    chown -R frappe:frappe /home/frappe

    echo " [Docker] Permisos corregidos. Cambiando a usuario frappe..."
    # Ejecuta este mismo script otra vez, pero disfrazado del usuario frappe
    exec su frappe -c "bash /workspace/init.sh"
fi

# === TODO LO QUE SIGUE A CONTINUACIÓN SE EJECUTARÁ COMO EL USUARIO FRAPPE ===

if [ -d "$BENCH_DIR/apps/frappe" ]; then
    echo "===================================================="
    echo " El Bench ya está listo. Iniciando backend..."
    echo "===================================================="
    cd "$BENCH_DIR"
    bench start
else
    echo "===================================================="
    echo " Inicializando un entorno Bench limpio..."
    echo "===================================================="

    bench init --skip-redis-config-generation "$BENCH_DIR" --frappe-branch version-16

    cd "$BENCH_DIR"

    echo "===================================================="
    echo " Enlazando con la infraestructura Docker..."
    echo "===================================================="
    bench set-mariadb-host mariadb
    bench set-redis-cache-host redis://redis:6379
    bench set-redis-queue-host redis://redis:6379
    bench set-redis-socketio-host redis://redis:6379

    sed -i '/redis/d' ./Procfile
    sed -i '/watch/d' ./Procfile

    echo "===================================================="
    echo " Descargando dependencias complementarias..."
    echo "===================================================="
    bench get-app payments

    echo "===================================================="
    echo " Vinculando tu Fork de Backend local..."
    echo "===================================================="
    # bench get-app lms /workspace
		bench get-app https://github.com/PS-Grupo-7-Gorgojo/lms --branch main
		# mkdir -p "$BENCH_DIR/apps/lms"
		# cp -r /workspace/. "$BENCH_DIR/apps/lms/"

    echo "===================================================="
    echo " Creando sitio local lms.localhost..."
    echo "===================================================="
    bench new-site lms.localhost \
        --force \
        --mariadb-root-password 123 \
        --admin-password admin \
        --no-mariadb-socket

    bench --site lms.localhost install-app payments
    bench --site lms.localhost install-app lms
    bench --site lms.localhost set-config developer_mode 1
    bench --site lms.localhost clear-cache
    bench use lms.localhost

    echo "===================================================="
    echo " ¡Servidor listo! Iniciando..."
    echo "===================================================="
    bench start
fi
