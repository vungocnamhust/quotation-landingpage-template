#!/usr/bin/env sh
# Synchronize Cloudflare's published proxy CIDRs into the host firewall.
# Run as root on the VPS, then schedule it through the paired systemd timer.
set -eu

for tool in curl ipset iptables ip6tables grep mktemp; do
  command -v "$tool" >/dev/null 2>&1 || { echo "missing required tool: $tool" >&2; exit 1; }
done

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
curl --fail --silent --show-error --proto '=https' --tlsv1.2 https://www.cloudflare.com/ips-v4 -o "$workdir/ips-v4"
curl --fail --silent --show-error --proto '=https' --tlsv1.2 https://www.cloudflare.com/ips-v6 -o "$workdir/ips-v6"
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$' "$workdir/ips-v4"
grep -Eq '^[0-9a-fA-F:]+/[0-9]+$' "$workdir/ips-v6"

ipset create quotation_cloudflare_v4_next hash:net family inet -exist
ipset flush quotation_cloudflare_v4_next
while IFS= read -r cidr; do ipset add quotation_cloudflare_v4_next "$cidr"; done < "$workdir/ips-v4"
ipset create quotation_cloudflare_v6_next hash:net family inet6 -exist
ipset flush quotation_cloudflare_v6_next
while IFS= read -r cidr; do ipset add quotation_cloudflare_v6_next "$cidr"; done < "$workdir/ips-v6"

ipset create quotation_cloudflare_v4 hash:net family inet -exist
ipset create quotation_cloudflare_v6 hash:net family inet6 -exist
ipset swap quotation_cloudflare_v4_next quotation_cloudflare_v4
ipset swap quotation_cloudflare_v6_next quotation_cloudflare_v6

iptables -N QUOTATION_CLOUDFLARE_ONLY 2>/dev/null || true
iptables -F QUOTATION_CLOUDFLARE_ONLY
iptables -A QUOTATION_CLOUDFLARE_ONLY -m set --match-set quotation_cloudflare_v4 src -j RETURN
iptables -A QUOTATION_CLOUDFLARE_ONLY -j REJECT
iptables -C DOCKER-USER -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY 2>/dev/null || \
  iptables -I DOCKER-USER 1 -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY

ip6tables -N QUOTATION_CLOUDFLARE_ONLY 2>/dev/null || true
ip6tables -F QUOTATION_CLOUDFLARE_ONLY
ip6tables -A QUOTATION_CLOUDFLARE_ONLY -m set --match-set quotation_cloudflare_v6 src -j RETURN
ip6tables -A QUOTATION_CLOUDFLARE_ONLY -j REJECT
ip6tables -C DOCKER-USER -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY 2>/dev/null || \
  ip6tables -I DOCKER-USER 1 -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY
