# Ishga tushirish qo'llanmasi

Bu hujjat botni **Oracle Cloud bepul serverida** doimiy ishlaydigan qilib
o'rnatishni tushuntiradi. Har bir qadam nima uchun kerakligi bilan.

---

## 0. Ishga tushirishdan OLDIN — majburiy ro'yxat

Quyidagilar bajarilmasdan bot **haqiqiy foydalanuvchilarga ochilmasligi**
kerak. Bu tavsiya emas, spetsifikatsiyaning talabi.

| # | Nima | Nima uchun | Kim bajaradi |
|---|---|---|---|
| 1 | **Harom/mashbooh coinlar ro'yxatini ko'rib chiqish** | `scripts/seed.py` dagi ro'yxat — dastlabki taxmin, diniy hukm emas. 0.4-band: halollik brendning asosi | Bilimdon kishi |
| 2 | **1-2 yillik haqiqiy backtest** | 6.3-band: haqiqiy pul ishlatilishidan oldin natija ko'rilishi SHART | Siz |
| 3 | **`CMC_API_KEY` olish** | Reyting manbai sifatida CoinMarketCap tanlangan. Kalitsiz CoinGecko'ga tushib qoladi | Siz |
| 4 | **Test rejimida 1-2 hafta kuzatish** | Signal chiqishini va kuzatuvni real bozorda ko'rish | Siz |
| 5 | **Zaxira nusxa jadvalini o'rnatish** | To'lovlar va obunalar bazada — yo'qolsa tiklab bo'lmaydi | Siz (7-bo'lim) |

Backtest:

```bash
python -m scripts.backtest --compare --days 730
```

---

## 1. Server tayyorlash (Oracle Cloud bepul)

Oracle Cloud "Always Free" tarifida **ARM (Ampere) 4 yadro / 24 GB**
beriladi. Bu bot uchun ortig'i bilan yetadi.

1. https://cloud.oracle.com -> Compute -> Instances -> **Create Instance**
2. Image: **Ubuntu 22.04** (yoki 24.04)
3. Shape: **Ampere / VM.Standard.A1.Flex** — 2 yadro, 6 GB yetarli
4. SSH kalitingizni qo'shing va instansiyani yarating

Ulanish:

```bash
ssh ubuntu@<SERVER_IP>
```

> **Diqqat:** botga kiruvchi port KERAK EMAS — u polling rejimida
> ishlaydi (6.2-band). Shuning uchun firewall'da hech narsa ochilmaydi.
> Bu webhook'dan xavfsizroq: domen ham, SSL sertifikat ham shart emas.

---

## 2. O'rnatish

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

git clone <REPO_URL> ~/hcs
cd ~/hcs

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Ishlab chiqish uchun `requirements-dev.txt` (testlar, ruff). Serverda
> `requirements.txt` yetarli.

---

## 3. Sozlash

```bash
cp .env.example .env
nano .env
```

To'ldirilishi kerak:

| o'zgaruvchi | qayerdan olinadi |
|---|---|
| `BOT_TOKEN` | Telegram'da [@BotFather](https://t.me/BotFather) -> `/newbot` |
| `ADMIN_IDS` | O'z Telegram ID'ingiz — [@userinfobot](https://t.me/userinfobot) beradi |
| `CMC_API_KEY` | https://pro.coinmarketcap.com/signup -> API Key (bepul reja ham kalit talab qiladi) |

`ADMIN_IDS` da vergul bilan bir nechta ID bo'lishi mumkin: `111,222,333`.

> **Muhim:** `.env` fayli git'ga **tushmaydi** (`.gitignore` da). Tokenni
> hech qachon kodga yozmang.

---

## 4. Ma'lumotlar bazasi

```bash
alembic upgrade head     # jadvallarni yaratadi/yangilaydi
python -m scripts.seed   # boshlang'ich narxlar va coin qarorlari
```

**Har safar yangilanishdan keyin `alembic upgrade head` ni takrorlang** —
sxema o'zgargan bo'lsa u qo'llanadi, o'zgarmagan bo'lsa hech narsa
qilmaydi.

### PostgreSQL ga o'tish (keyinroq)

SQLite bir server uchun yetarli. Foydalanuvchi ko'payganda:

```bash
sudo apt install -y postgresql
sudo -u postgres createuser hcs --pwprompt
sudo -u postgres createdb hcs --owner=hcs
pip install asyncpg
```

`.env` da faqat bitta qatorni o'zgartiring:

```
DATABASE_URL=postgresql+asyncpg://hcs:PAROL@localhost/hcs
```

So'ng `alembic upgrade head`. Kodda **hech narsa o'zgarmaydi** — 6.2-band
shuni talab qiladi.

---

## 5. Sinov

Doimiy xizmat qilishdan oldin qo'lda ishga tushiring:

```bash
python -m bot.main
```

Kutilayotgan chiqish:

```
Konfiguratsiya yuklandi: HALOL CRYPTO SAVDO
Ma'lumotlar bazasi sxemasi tayyor (15 jadval)
Risk Engine tayyor: 13 ta qoida
Adminlar: 1 ta
Strategiyalar: classic_ta(yoq), opening_range_scalp(yoq)
Fon vazifalari ishga tushdi: 5 ta
Bot polling rejimida ishga tushdi
Signal kuzatuvchisi ishga tushdi
```

Telegram'da botga `/start` yuboring. Admin panel: `/panel`.

`Ctrl+C` bilan to'xtating.

### Tez-tez uchraydigan xatolar

| xabar | sabab |
|---|---|
| `BOT_TOKEN o'rnatilmagan` | `.env` yaratilmagan yoki token bo'sh |
| `BOT_TOKEN Telegram tomonidan qabul qilinmadi` | Token noto'g'ri nusxalangan (BotFather -> `/mybots`) |
| `api.telegram.org ga ulanib bo'lmadi` | Internet yo'q yoki Telegram to'silgan tarmoq |
| `CMC_API_KEY o'rnatilmagan` | Ogohlantirish — bot ishlaydi, lekin CoinGecko'ga tushadi |

---

## 6. Doimiy xizmat (systemd)

Bot server qayta yuklanganda ham o'zi ishga tushishi kerak.

```bash
sudo nano /etc/systemd/system/hcs.service
```

```ini
[Unit]
Description=HALOL CRYPTO SAVDO — signal boti
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/hcs
ExecStart=/home/ubuntu/hcs/.venv/bin/python -m bot.main

# Yiqilsa qayta ishga tushadi. 10 soniya — Telegram'ni bezovta qilmaslik uchun.
Restart=always
RestartSec=10

# Xotira chegarasi: sizib ketish butun serverni to'xtatmasin.
MemoryMax=1G

# Xavfsizlik: botga kerak bo'lmagan hech narsaga ruxsat yo'q.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/ubuntu/hcs/data /home/ubuntu/hcs/logs

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hcs
sudo systemctl status hcs
```

Kundalik buyruqlar:

```bash
sudo systemctl restart hcs     # qayta ishga tushirish
sudo systemctl stop hcs        # to'xtatish
sudo journalctl -u hcs -f      # jonli jurnal
tail -f logs/hcs.log           # ilova jurnali
```

> Jurnal fayllari **o'zi aylanadi** (20 MB × 5 nusxa) — `logrotate`
> sozlash shart emas.

---

## 7. Zaxira nusxa

Bazada **to'lovlar, obunalar va foydalanuvchi pozitsiyalari** bor. Yo'qolsa
tiklab bo'lmaydi.

```bash
mkdir -p ~/zaxira
nano ~/zaxira/zaxirala.sh
```

```bash
#!/bin/bash
# Kunlik zaxira; 14 kunlikdan eskisi o'chiriladi.
set -e
SANA=$(date +%F)
cd /home/ubuntu/hcs

# SQLite uchun `.backup` ishlatiladi: oddiy `cp` bot yozayotgan paytda
# buzuq nusxa berishi mumkin.
sqlite3 data/hcs.db ".backup '/home/ubuntu/zaxira/hcs-$SANA.db'"
gzip -f "/home/ubuntu/zaxira/hcs-$SANA.db"

find /home/ubuntu/zaxira -name 'hcs-*.db.gz' -mtime +14 -delete
```

```bash
chmod +x ~/zaxira/zaxirala.sh
sudo apt install -y sqlite3
crontab -e
```

Qo'shing (har kuni 03:00 da):

```
0 3 * * * /home/ubuntu/zaxira/zaxirala.sh >> /home/ubuntu/zaxira/zaxira.log 2>&1
```

> **Zaxirani boshqa joyga ham nusxalang.** Server yo'qolsa, undagi zaxira
> ham yo'qoladi. `rclone` yoki oddiy `scp` bilan oyiga bir marta
> kompyuteringizga tushiring.

Tiklash:

```bash
sudo systemctl stop hcs
gunzip -c ~/zaxira/hcs-2026-01-15.db.gz > ~/hcs/data/hcs.db
sudo systemctl start hcs
```

---

## 8. Yangilash

```bash
cd ~/hcs
sudo systemctl stop hcs

git pull
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # sxema o'zgargan bo'lsa qo'llanadi

sudo systemctl start hcs
sudo journalctl -u hcs -n 30  # xatosiz ishga tushdimi
```

> Yangilashdan oldin zaxira oling — `~/zaxira/zaxirala.sh` ni qo'lda
> ishga tushiring.

---

## 9. Kundalik kuzatuv

| nima | qayerda |
|---|---|
| Bozor Salomatligi | `/panel` -> 💓 Bozor Salomatligi |
| Nima uchun signal chiqmadi | `/panel` -> 🔇 Nega signal yo'q |
| Haftalik o'z-o'zini tekshirish | `/panel` -> 🧾 hisobot (avtomatik yuboriladi) |
| Kutilmagan xatolar | `sudo journalctl -u hcs -p err -n 50` |

**Signal chiqmasligi xato emas.** 0.2-band: "hozir signal berish to'g'ri
emas" — normal javob. Sabablari admin panelda ko'rinadi.

---

## 10. Xavfsizlik

- `.env` git'ga tushmaydi, serverdan tashqariga chiqarilmaydi
- Bot **hech qachon** haqiqiy birja hisobiga ulanmaydi va pul ushlamaydi
  (5-bo'lim) — token o'g'irlansa ham mablag' xavf ostida emas
- Kiruvchi port ochilmaydi (polling rejimi)
- `ProtectSystem=strict` — bot faqat `data/` va `logs/` ga yoza oladi
- SSH uchun parol emas, faqat kalit ishlatiladi (Oracle standarti)

Token o'g'irlangan deb gumon qilsangiz: BotFather -> `/mybots` ->
**Revoke current token** -> yangi tokenni `.env` ga yozing ->
`sudo systemctl restart hcs`.
