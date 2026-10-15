#!/usr/bin/env bash
#
# Railway'da BITTA xizmat ichida uchta jarayon ishga tushadi:
#   1. bot   — fon jarayoni, port ochmaydi
#   2. sayt  — Railway bergan `$PORT` da
#   3. radar — Modul 4.0.0 (`core/portlash_radari`), port ochmaydi.
#              Botdan ALOHIDA: modul faqat sayt uchun (loyiha egasining
#              qarori, 2026-10-14), radar yiqilsa bot va sayt ishlayveradi.
#
# Nima uchun bitta xizmat: Railway'da doimiy disk FAQAT BITTA xizmatga
# ulanadi. Baza esa o'sha diskdagi SQLite fayli. Saytni alohida xizmatga
# (yoki Vercel'ga) qo'ysak, u faylni umuman ko'rmaydi — shuning uchun
# ikkalasi bir konteynerda yashaydi.
set -euo pipefail

ILDIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ILDIZ"

# --- Baza manzili: bot va sayt uchun BITTA manba -------------------------
# `bot/hosting.py` doimiy disk ulangan bo'lsa manzilni o'shanga
# yo'naltiradi. Lekin u buni PYTHON JARAYONI ICHIDA qiladi — Node
# jarayoni bu o'zgarishni ko'rmaydi. Shuning uchun bir marta shu yerda
# hisoblab, ikkalasiga ham eksport qilamiz.
DATABASE_URL="$(python - <<'PY'
from pathlib import Path

from bot.hosting import apply_platform_defaults
from core.storage.database import resolve_database_url

# Botning O'Z zanjiri: doimiy disk -> muhit o'zgaruvchisi -> standart.
# Bu yerda yangi mantiq yozilmaydi, aks holda bot bir faylga, sayt
# boshqasiga qarab qolishi mumkin.
apply_platform_defaults()
url = resolve_database_url()

# Nisbiy yo'lni MUTLAQ qilamiz: sayt `web/` papkasidan ishga tushadi,
# ya'ni uning uchun "data/hcs.db" butunlay boshqa joyni bildiradi.
# SQLAlchemy qoidasi: `:///` nisbiy, `:////` mutlaq.
if url.startswith("sqlite") and ":////" not in url:
    sxema, _, yol = url.partition(":///")
    url = f"{sxema}:///{Path(yol).resolve()}"

print(url)
PY
)"
export DATABASE_URL
echo "Baza: ${DATABASE_URL}"

# --- Sxema va boshlang'ich ma'lumot -------------------------------------
# Ikkisi ham TAKRORIY XAVFSIZ. Yiqilsa bot ham ishga tushmaydi — bu
# ataylab: yarim sozlangan baza bilan ishlagandan ko'ra to'xtagan yaxshi.
alembic upgrade head
python -m scripts.seed

# --- node:sqlite bayrog'i -------------------------------------------------
# Konteynerdagi Node — v22.10.0. `node:sqlite` unda bor, lekin bayroq
# ostida: modul 22.5 da qo'shilgan va faqat 22.13 dan bayroqsiz ochilgan.
# Bayroqsiz sayt "No such built-in module: node:sqlite" deb yiqiladi.
#
# Mavjud qiymat SAQLANADI: Railway yoki nixpacks allaqachon nimadir
# qo'ygan bo'lishi mumkin, uni bosib o'tib ketmaymiz.
case "${NODE_OPTIONS:-}" in
  *--experimental-sqlite*) ;;
  *) export NODE_OPTIONS="--experimental-sqlite ${NODE_OPTIONS:-}" ;;
esac
echo "Node: $(node --version), NODE_OPTIONS=${NODE_OPTIONS}"

# --- Port ----------------------------------------------------------------
# Standart qiymat 8080 — Railway domenning maqsad porti sifatida aynan
# shuni taklif qiladi. Ilgari bu yerda 3000 turgan edi: `PORT`
# o'zgaruvchisi qo'yilmasa sayt 3000 da tinglardi, Railway esa 8080 ga
# yo'naltirardi va tashqaridan "Application failed to respond" ko'rinardi
# — ikkala tomon ham "men ishlayapman" deb turgan holda.
PORT="${PORT:-8080}"
export PORT

# --- Ikkala jarayon ------------------------------------------------------
#
# Sayt OLDIN ko'tariladi va bot bilan nima bo'lishidan qat'i nazar
# ishlab turadi.
#
# Ilgari teskari edi: biri yiqilsa ikkinchisi ham to'xtardi. Mantiq
# shunday edi — "signal dvigateli o'lgan holda sayt eski ma'lumotni
# jonli qilib ko'rsatgani yomonroq". Amalda esa bu diagnostikani
# butunlay o'ldirdi: bot bir soniya qoqilsa, tashqaridan
# "Application failed to respond" ko'rinardi va bu xato bot haqidami,
# sayt haqidami, qurilish haqidami — bilib bo'lmasdi.
#
# Endi mas'uliyat bo'lingan:
#   - sayt DOIM javob beradi (hech bo'lmasa sabab ko'rinadi);
#   - bot yiqilsa shu yerda qayta ko'tariladi, har safar kutish
#     vaqti ikki barobar oshib boradi;
#   - ketma-ket urinishlar tugasa, konteyner butunlay chiqadi va
#     Railway uni noldan qayta ko'taradi.
(cd web && exec node_modules/.bin/next start --port "$PORT" --hostname 0.0.0.0) &
WEB_PID=$!
echo "Sayt ishga tushdi: PID=${WEB_PID}, PORT=${PORT}"

# --- Radar (Modul 4.0.0) — o'z nazoratchisi bilan ----------------------
#
# Bot va sayt kuzatadigan `wait -n` ga ATAYLAB qo'shilmaydi: radar
# yiqilishi konteynerni ham, botni ham qayta ko'tarmasligi kerak. U
# o'z siklida qayta ko'tariladi, kutish har safar ikki barobar oshadi
# (5 daqiqagacha). Chiqish kodi 0 — radar sozlamada o'chirilgan, qayta
# ko'tarish shart emas.
radar_nazoratchisi() {
  local kutish=5 bola=""
  # Nazoratchi to'xtatilsa, avval bolasi (python) to'xtatiladi — aks holda
  # konteyner yopilayotganda radar jarayoni yetim qolardi. `wait` ishlatiladi:
  # oddiy chaqiruvda qobiq bola tugaguncha signalni ushlamaydi.
  trap 'kill "$bola" 2>/dev/null; exit 0' TERM INT
  while true; do
    python -m core.portlash_radari &
    bola=$!
    if wait "$bola"; then
      echo "Radar o'chiq — qayta ko'tarilmaydi."
      return 0
    fi
    echo "RADAR TO'XTADI. Bot va sayt ishlab turibdi. ${kutish} soniyadan keyin qayta urinamiz."
    sleep "$kutish"
    kutish=$((kutish < 300 ? kutish * 2 : 300))
  done
}
radar_nazoratchisi &
RADAR_PID=$!
echo "Radar nazoratchisi ishga tushdi: PID=${RADAR_PID}"

#: Bot ketma-ket necha marta qayta ko'tariladi
BOT_URINISHLAR="${BOT_RESTART_LIMIT:-5}"

to_xtat() {
  kill "$WEB_PID" "${BOT_PID:-}" "$RADAR_PID" 2>/dev/null || true
}
trap to_xtat EXIT INT TERM

kutish=5
for ((urinish = 1; urinish <= BOT_URINISHLAR; urinish++)); do
  echo "Bot ishga tushmoqda (urinish ${urinish}/${BOT_URINISHLAR})"
  python -m bot.main &
  BOT_PID=$!

  # Ikkalasidan qaysi biri birinchi to'xtasa — o'shani bilib olamiz
  wait -n "$BOT_PID" "$WEB_PID" || true

  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "SAYT TO'XTADI — konteyner qayta ko'tariladi."
    exit 1
  fi

  echo "BOT TO'XTADI. Sayt ishlab turibdi. ${kutish} soniyadan keyin qayta urinamiz."
  wait "$BOT_PID" 2>/dev/null || true
  sleep "$kutish"
  kutish=$((kutish * 2))
done

echo "Bot ${BOT_URINISHLAR} marta ishga tushmadi — konteyner qayta ko'tariladi."
exit 1
