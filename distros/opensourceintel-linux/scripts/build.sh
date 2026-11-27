#!/bin/sh
# OpenSourceIntel Linux's build script: runs as root while the image is
# built, after the packages, files and repos in linuxlive.yaml.
#
# 1. Python tools from PyPI, each in its own environment (files/osint-uv).
# 2. Go and Rust tools, from their projects' own release builds, each checked
#    against the SHA-256 GitHub gives for it.
# 3. A check that every tool starts.
set -eu
uv=/usr/libexec/opensourceintel/osint-uv

# 1. maigret's libraries are tested up to 3.12; holehe and uro are plain Python.
"$uv" tool install --python 3.12 maigret==0.6.7
"$uv" tool install --python 3.14 holehe==1.61
"$uv" tool install --python 3.14 uro==1.0.2

# 2. name, version, URL, SHA-256, the binary inside the archive.
fetch() {
	name=$1 url=$2 sum=$3 inside=$4
	tmp=$(mktemp -d)
	file=$tmp/$(basename "$url")
	curl -fsSL --retry 3 -o "$file" "$url"
	echo "$sum  $file" | sha256sum -c -
	case $file in
		*.zip) unzip -q "$file" -d "$tmp/x" ;;
		*.tar.gz) mkdir -p "$tmp/x" && tar -xzf "$file" -C "$tmp/x" ;;
	esac
	install -m 0755 "$tmp/x/$inside" "/usr/local/bin/$name"
	rm -rf "$tmp"
}
fetch subfinder \
	https://github.com/projectdiscovery/subfinder/releases/download/v2.17.0/subfinder_2.17.0_linux_amd64.zip \
	a39c3e5c7a26ef3c430915c4d6cbf7716a00f26769a75e9405aba796142eba37 subfinder
fetch findomain \
	https://github.com/Findomain/Findomain/releases/download/11.0.0/findomain-linux.zip \
	67763aef09f74a7cc83e088203ccecb2112d0545535dd753bdee0fe406e765b7 findomain
fetch amass \
	https://github.com/owasp-amass/amass/releases/download/v5.1.3/amass_linux_amd64.tar.gz \
	4c12b725e4ce4981ece93a5e1566bd7391be1f349468856a79d31a43012ae201 amass_linux_amd64/amass

# Nothing else needs uv's download cache once the tools are in place.
rm -rf /var/cache/opensourceintel-uv

# 3. Every tool starts (none of these touch the network). They run with a
# throwaway home of their own, as some write settings there on first start.
mkdir -p /tmp/osint-check
for check in \
	"theHarvester -h" \
	"maigret --help" \
	"holehe --help" \
	"uro --help" \
	"sherlock --version" \
	"subfinder -version" \
	"findomain --version" \
	"amass -version" \
	"assetfinder -h" \
	"dnstwist --help" \
	"instaloader --version" \
	"exiftool -ver" \
	"yt-dlp --version" \
	"metagoofil -h" \
	"spiderfoot -h" \
	"spiderfoot-cli --help" \
	"recon-ng --version"; do
	# Some tools exit non-zero for their help, so what fails is a missing
	# command, a hang, a Python traceback or a missing library.
	rc=0
	out=$(HOME=/tmp/osint-check timeout 120 $check </dev/null 2>&1) || rc=$?
	if [ "$rc" -eq 124 ] || [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ] ||
		printf '%s\n' "$out" | grep -Eq 'Traceback \(most recent call last\)|ModuleNotFoundError|ImportError|error while loading shared libraries'; then
		printf '%s\n' "$out" | tail -n 20
		echo "build.sh: '$check' did not start" >&2
		exit 1
	fi
	echo "ok: $check"
done

# 4. SpiderFoot's web interface serves its pages when started from somewhere
# else, as spiderfoot-web starts it from home (0.1 served a 500 on every page).
(cd / && HOME=/tmp/osint-check exec spiderfoot -l 127.0.0.1:5099 </dev/null >/tmp/osint-check/sf.log 2>&1) &
sf=$!
code=000
for _ in $(seq 1 60); do
	code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5099/ || true)
	[ "$code" = 200 ] && break
	sleep 1
done
kill "$sf" 2>/dev/null || true
wait "$sf" 2>/dev/null || true
if [ "$code" != 200 ]; then
	tail -n 20 /tmp/osint-check/sf.log
	echo "build.sh: SpiderFoot's web interface answered $code, not 200" >&2
	exit 1
fi
echo "ok: SpiderFoot's web interface (200 from /)"
rm -rf /tmp/osint-check
