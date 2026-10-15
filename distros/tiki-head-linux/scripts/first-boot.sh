#!/bin/sh
# Once, on a computer Tiki Head was installed on, before its first login:
# PostGIS, ready to use. Each person who can log in gets a database role and
# a database of their own name with PostGIS in it, so `psql` and QGIS's
# PostGIS connection (host: localhost, empty password, your user name) work.
set -eu
systemctl enable --now postgresql.service
tries=0
until runuser -u postgres -- pg_isready -q; do
	tries=$((tries + 1))
	[ "$tries" -lt 90 ] || { echo "Tiki Head: PostgreSQL did not start" >&2; exit 1; }
	sleep 1
done
cd /
getent passwd | awk -F: '$3 >= 1000 && $3 < 60000 {print $1}' | while read -r user; do
	if ! runuser -u postgres -- psql -qtAc "SELECT 1 FROM pg_roles WHERE rolname = '$user'" | grep -q 1; then
		runuser -u postgres -- createuser --createdb "$user"
	fi
	if ! runuser -u postgres -- psql -qtAc "SELECT 1 FROM pg_database WHERE datname = '$user'" | grep -q 1; then
		runuser -u postgres -- createdb --owner "$user" "$user"
	fi
	runuser -u postgres -- psql -q -d "$user" -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
	echo "Tiki Head: PostGIS database '$user' for $user"
done
