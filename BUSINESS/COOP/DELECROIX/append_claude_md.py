import os

target = r"D:\MEMORY\CLAUDE.md"

addition = """

---

## DELECROIX - Parteneriat Utilaje Recoltare Franta->Romania

**Dosar complet**: `D:\\MEMORY\\DELECROIX\\claude.md`

**Ce e**: Delecroix (Franta, 13 angajati) produce benzi transportoare de recoltare, remorci legume, statii sortare, pareuse varza. Toubeaux (gerant) propune parteneriat: Tudor = business finder (~10% comision), Agri Alianta = distribuitor (contract deja semnat, 6 filiale RO).

**Concurenta**: SIMON (DE, site picat), Krukowiak (PL, picat), Domasz (PL, a plecat din utilaje), MTS-SANDEI (IT, activ dar foarte scump). Delecroix e practic singur pe piata benzilor de recoltare la pret accesibil in Romania.

**Distribuitori RO**: Agri Alianta (CONTRACTAT, 6 filiale, 0755 405 555), Agritech (Ograda, vinde SIMON/DOMASZ dar "Sortare" goala), Equinto (Galati, SERIOS, deja importa ERME din FR, 0745389200), MARCOSER (Matca, marketing leads, 20 ani clienti legumicultori), Green Garden (Calarasi, consumabile).

**Comision estimat**: 5K-60K EUR/an (5-35 unitati x ~1500 EUR/unitate)

**Contact Toubeaux**: +33 6 08 09 97 20, contact@delecroix-harvesting.com

**Urmator pas**: Cere preturi exacte de la Toubeaux + contacteaza Agri Alianta pentru coordonare vanzari.
"""

with open(target, "a", encoding="utf-8") as f:
    f.write(addition)

print(f"Appended to {target}")

# Verify
with open(target, "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
print(f"Last 3 lines:")
for line in lines[-3:]:
    print(repr(line))
