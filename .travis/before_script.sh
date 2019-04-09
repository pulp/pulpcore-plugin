#!/usr/bin/env sh
set -v

psql -U postgres -c 'CREATE USER pulp WITH SUPERUSER LOGIN;'
psql -U postgres -c 'CREATE DATABASE pulp3 OWNER pulp;'

mkdir -p ~/.config/pulp_smash
cp .travis/pulp-smash-config.json ~/.config/pulp_smash/settings.json

sudo mkdir -p /var/lib/pulp/tmp
sudo mkdir /etc/pulp/
sudo chown -R travis:travis /var/lib/pulp

echo "SECRET_KEY: \"$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)\"" | sudo tee -a /etc/pulp/settings.py

echo "DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pulp3',
        'USER': 'pulp',
        'CONN_MAX_AGE': 0,
    },
}" | sudo tee -a /etc/pulp/settings.py

# Run migrations.
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
export PULP_CONTENT_HOST=localhost:24816

django-admin makemigrations pulp_app --noinput
if [ "$TEST" != 'docs' ]; then
  django-admin makemigrations file --noinput
fi

django-admin migrate auth --noinput
django-admin migrate --noinput

django-admin reset-admin-password --password admin
django-admin runserver 24817 >> ~/django_runserver.log 2>&1 &
gunicorn pulpcore.content:server --bind 'localhost:24816' --worker-class 'aiohttp.GunicornWebWorker' -w 2 >> ~/content_app.log 2>&1 &
rq worker -n 'resource-manager@%h' -w 'pulpcore.tasking.worker.PulpWorker' -c 'pulpcore.rqconfig' >> ~/resource_manager.log 2>&1 &
rq worker -n 'reserved-resource-worker-1@%h' -w 'pulpcore.tasking.worker.PulpWorker' -c 'pulpcore.rqconfig' >> ~/reserved_worker-1.log 2>&1 &
sleep 5
