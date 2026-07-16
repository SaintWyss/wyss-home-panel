#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Yo uso: $0 <IP-DE-LA-NETBOOK> <panel-id>" >&2
  exit 2
fi

host_ip=$1
panel_id=$2
private_dir=config/private
mkdir -p "$private_dir"
umask 077

openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$private_dir/ca.key"
openssl req -x509 -new -sha256 -days 3650 -key "$private_dir/ca.key" \
  -subj "/CN=Wyss Home Local CA" -out "$private_dir/ca.crt"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$private_dir/server.key"
openssl req -new -key "$private_dir/server.key" -subj "/CN=$host_ip" -out "$private_dir/server.csr"
openssl x509 -req -sha256 -days 825 -in "$private_dir/server.csr" \
  -CA "$private_dir/ca.crt" -CAkey "$private_dir/ca.key" -CAcreateserial \
  -extfile <(printf 'subjectAltName=IP:%s\nextendedKeyUsage=serverAuth\n' "$host_ip") \
  -out "$private_dir/server.crt"

token=$(openssl rand -hex 32)
printf '%s' "$token" > "$private_dir/panel-token.once"
token_sha=$(printf '%s' "$token" | sha256sum | cut -d' ' -f1)

echo "Yo creé la identidad TLS local."
echo "panel.id = $panel_id"
echo "panel.token_sha256 = $token_sha"
echo "bridge.url = wss://$host_ip:8443/v1/panel"
echo "Yo guardé el token de una sola vez en $private_dir/panel-token.once."

