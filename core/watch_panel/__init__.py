"""Kuzatuv paneli — 80 halol coinni kuzatadi, SIGNAL BERMAYDI.

QAT'IY CHEGARA (9-prompt, 0-qism va 6-qism): bu paketning hech bir
joyida Entry, Stop yoki TP hisoblanmaydi va ko'rsatilmaydi. Modul —
faqat KO'Z va QULOQ; qarorni admin o'zi, ko'rgan ma'lumot asosida
qabul qiladi.

Chegara testda ham qulflangan: `tests/core/test_kuzatuv_chegara.py`
bu paketning butun kodini o'qib chiqadi va `entry_stop_tp` yoki
`darajalar_qur` chaqirig'i bor-yo'qligini tekshiradi.

SIGNAL MODULIGA TEGILMAYDI. `core/analysis/chain/block_chain_engine.py`
(Rejim A) o'z holicha qoladi. Bu paket o'sha to'rt blokning
HISOBLASH funksiyalarini chaqiradi, lekin zanjir mantig'ini
(0/4 -> uzilish) QO'LLAMAYDI.
"""
