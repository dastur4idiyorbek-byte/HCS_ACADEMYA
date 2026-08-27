import { copyFileSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

/** Test uchun bazadan vaqtinchalik nusxa oladi.
 *
 * NEGA ALOHIDA FUNKSIYA VA NEGA `-wal` HAM KO'CHIRILADI: baza WAL
 * rejimida ishlaydi — yangi yozuvlar avval `hcs.db-wal` fayliga
 * tushadi va faqat keyinroq asosiy faylga ko'chadi. Faqat `hcs.db`
 * nusxalansa, ENG YANGI o'zgarishlar (masalan yangi migratsiya
 * qo'shgan ustun) nusxada BO'LMAYDI.
 *
 * Bu jimgina adashtiradi: migratsiya ishlaydi, baza to'g'ri, lekin
 * test "no such column" deydi va sabab kodda izlanadi. Bir marta
 * shunday bo'ldi — shundan keyin bu yerga chiqarildi.
 */
export function bazadanNusxa(prefiks: string): string {
  const jild = mkdtempSync(path.join(tmpdir(), prefiks));
  const manba = path.resolve(process.cwd(), "..", "data", "hcs.db");
  const nishon = path.join(jild, "test.db");

  copyFileSync(manba, nishon);
  for (const qoshimcha of ["-wal", "-shm"]) {
    if (existsSync(manba + qoshimcha)) {
      copyFileSync(manba + qoshimcha, nishon + qoshimcha);
    }
  }
  return nishon;
}
