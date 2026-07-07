#!/bin/bash
# run_test.sh - Ejecuta las pruebas de integración

# Sincronizar tests primero
./sync_tests.sh

# Ejecutar la prueba
echo "===================================================="
echo " Ejecutando prueba de integración..."
echo "===================================================="

# La ruta del módulo dentro del contenedor
MODULE="lms.tests.integration.test_chapter"
TEST="TestChapterAPI.test_upsert_chapter_happy_path"

sudo docker exec -it lms-frappe-1 su - frappe -c "
cd /home/frappe/data/frappe-bench && \
bench --site lms.localhost run-tests --app lms --module $MODULE --test $TEST
"
