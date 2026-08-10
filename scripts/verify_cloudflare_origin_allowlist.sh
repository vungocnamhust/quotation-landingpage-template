#!/usr/bin/env sh
set -eu

ipset test quotation_cloudflare_v4 173.245.48.1 >/dev/null
ipset test quotation_cloudflare_v6 2400:cb00::1 >/dev/null
iptables -C DOCKER-USER -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY
ip6tables -C DOCKER-USER -p tcp -m multiport --dports 80,443 -j QUOTATION_CLOUDFLARE_ONLY
