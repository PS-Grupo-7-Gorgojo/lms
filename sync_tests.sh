#!/bin/bash
# sync_tests.sh - Copia los tests de integración al contenedor

echo "===================================================="
echo " 🔄 Sincronizando tests de integración..."
echo "===================================================="

# Ruta dentro del contenedor donde deben estar los tests
CONTAINER_PATH="/home/frappe/data/frappe-bench/apps/lms/lms/lms/tests"

# Verificar que el contenedor está corriendo
if ! sudo docker ps | grep -q lms-frappe-1; then
    echo " El contenedor lms-frappe-1 no está corriendo."
    echo "   Ejecutar: sudo docker compose up -d"
    exit 1
fi

# Crear el directorio de tests en el contenedor (si no existe)
echo " Creando directorio de tests en el contenedor..."
sudo docker exec -it lms-frappe-1 su - frappe -c "mkdir -p $CONTAINER_PATH"

# --- ELIMINAR ARCHIVOS ANTIGUOS ---
echo " Eliminando archivos anteriores en $CONTAINER_PATH..."
sudo docker exec -it lms-frappe-1 su - frappe -c "
    if [ -d '$CONTAINER_PATH' ]; then
        rm -rf $CONTAINER_PATH/*
        echo '   Archivos eliminados'
    else
        echo '   El directorio no existe, se creará al copiar'
    fi
"

# --- COPIAR ARCHIVOS NUEVOS ---
echo " Copiando archivos de tests desde ./lms/lms/tests/ ..."
sudo docker cp ./lms/lms/tests/. lms-frappe-1:$CONTAINER_PATH/

# --- VERIFICAR COPIA ---
echo " Verificando que los tests se copiaron..."
sudo docker exec -it lms-frappe-1 su - frappe -c "ls -la $CONTAINER_PATH/"
sudo docker exec -it lms-frappe-1 su - frappe -c "ls -la $CONTAINER_PATH/integration/ 2>/dev/null || echo '  ⚠️ No hay carpeta integration'"
sudo docker exec -it lms-frappe-1 su - frappe -c "ls -la $CONTAINER_PATH/utils/ 2>/dev/null || echo '  ⚠️ No hay carpeta utils'"

echo "===================================================="
echo "  Tests sincronizados correctamente."
echo "===================================================="
