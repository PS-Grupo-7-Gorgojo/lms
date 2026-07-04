FROM frappe/bench:latest

USER frappe
WORKDIR /home/frappe

RUN bench init --skip-redis-config-generation frappe-bench

WORKDIR /home/frappe/frappe-bench

RUN bench get-app payments && \
    bench get-app https://github.com/PS-Grupo-7-Gorgojo/lms --branch main

RUN sed -i '/redis/d' ./Procfile && \
    sed -i '/watch/d' ./Procfile

RUN bench set-mariadb-host mariadb && \
    bench set-redis-cache-host redis://redis:6379 && \
    bench set-redis-queue-host redis://redis:6379 && \
    bench set-redis-socketio-host redis://redis:6379

RUN bench build

RUN cp -R /home/frappe/frappe-bench/sites/assets /home/frappe/assets_backup
