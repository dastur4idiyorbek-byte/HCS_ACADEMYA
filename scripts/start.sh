#!/usr/bin/env bash
#
# Railway'da BITTA xizmat ichida ikkita jarayon ishga tushadi:
#   1. bot   — fon jarayoni, port ochmaydi
#   2. sayt  — Railway bergan `$PORT` da
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

# --- Ikkala jarayon ------------------------------------------------------
python -m bot.main &
BOT_PID=$!

(cd web && exec node_modules/.bin/next start --port "${PORT:-3000}" --hostname 0.0.0.0) &
WEB_PID=$!

echo "Bot PID=${BOT_PID}, sayt PID=${WEB_PID}, port=${PORT:-3000}"

# Biri to'xtasa ikkinchisini ham to'xtatamiz va konteynerdan chiqamiz:
# Railway uni qayta ko'taradi. Aks holda bot jimgina o'lib, sayt esa
# ishlab turaverardi — tashqaridan hammasi joyida ko'rinardi.
to_xtat() {
  kill "$BOT_PID" "$WEB_PID" 2>/dev/null || true
}
trap to_xtat EXIT INT TERM

wait -n "$BOT_PID" "$WEB_PID"
KOD=$?
echo "Jarayonlardan biri to'xtadi (kod ${KOD}) — konteyner qayta ko'tariladi."
exit "$KOD"
