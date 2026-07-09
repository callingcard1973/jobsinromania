#!/usr/bin/env python3
"""Taxonomie legume-fructe: normalizeaza numele de produs (RO/EN/DE/IT/FR/PL) la un tag canonic.

Esential pentru trading INTERNATIONAL: un cumparator german care cere "tomaten"
trebuie sa dea match cu un producator roman care ofera "rosii".
"""

# WHY: cheia canonica (RO) -> sinonime multilingve. Match cross-limba prin canonic.
PRODUCE = {
    "rosii":     ["rosii", "tomate", "tomato", "tomatoes", "tomaten", "pomodori", "tomates", "pomidor"],
    "castraveti":["castraveti", "cucumber", "cucumbers", "gurken", "cetrioli", "concombre", "ogorek"],
    "ardei":     ["ardei", "pepper", "peppers", "paprika", "peperoni", "poivron", "papryka"],
    "ceapa":     ["ceapa", "onion", "onions", "zwiebel", "cipolla", "oignon", "cebula"],
    "cartofi":   ["cartofi", "potato", "potatoes", "kartoffeln", "patate", "pomme de terre", "ziemniaki"],
    "varza":     ["varza", "cabbage", "kohl", "cavolo", "chou", "kapusta"],
    "mere":      ["mere", "apple", "apples", "apfel", "mele", "pomme", "jablka"],
    "prune":     ["prune", "plum", "plums", "pflaumen", "prugne", "prune", "sliwki"],
    "struguri":  ["struguri", "grape", "grapes", "trauben", "uva", "raisin", "winogrona"],
    "morcovi":   ["morcovi", "carrot", "carrots", "karotten", "carote", "carotte", "marchew"],
    "usturoi":   ["usturoi", "garlic", "knoblauch", "aglio", "ail", "czosnek"],
    "pepeni":    ["pepeni", "watermelon", "melon", "melone", "anguria", "arbuz"],
    "capsuni":   ["capsuni", "strawberry", "strawberries", "erdbeeren", "fragole", "fraise", "truskawki"],
    "ceapa verde":["ceapa verde", "spring onion", "scallion"],
    "vinete":    ["vinete", "vanata", "eggplant", "aubergine", "melanzane", "auberginen", "oberzyna"],
    "dovlecei":  ["dovlecei", "dovlecel", "zucchini", "courgette", "zucchine", "zucchini"],
    "dovleac":   ["dovleac", "pumpkin", "squash", "kuerbis", "zucca", "potiron", "dynia"],
    "conopida":  ["conopida", "cauliflower", "blumenkohl", "cavolfiore", "chou-fleur", "kalafior"],
    "broccoli":  ["broccoli", "brocoli", "brokkoli", "brokuly"],
    "salata":    ["salata", "salata verde", "lettuce", "salat", "lattuga", "laitue", "salata"],
    "spanac":    ["spanac", "spinach", "spinat", "spinaci", "epinard", "szpinak"],
    "fasole":    ["fasole", "fasole verde", "bean", "beans", "bohnen", "fagioli", "haricot", "fasola"],
    "mazare":    ["mazare", "pea", "peas", "erbsen", "piselli", "pois", "groch"],
    "telina":    ["telina", "celery", "sellerie", "sedano", "celeri", "seler"],
    "patrunjel": ["patrunjel", "parsley", "petersilie", "prezzemolo", "persil", "pietruszka"],
    "marar":     ["marar", "dill", "aneth", "aneto", "koper"],
    "ridichi":   ["ridichi", "ridiche", "radish", "rettich", "ravanelli", "radis", "rzodkiewka"],
    "sfecla":    ["sfecla", "sfecla rosie", "beet", "beetroot", "rote bete", "barbabietola", "burak"],
    "praz":      ["praz", "leek", "lauch", "porro", "poireau", "por"],
    "ciuperci":  ["ciuperci", "mushroom", "mushrooms", "pilze", "funghi", "champignon", "grzyby"],
    "zarzavaturi":["zarzavaturi", "zarzavat", "root vegetables", "wurzelgemuse"],
    "muraturi":  ["muraturi", "muraturi asortate", "pickles", "eingelegtes", "sottaceti"],
    "pere":      ["pere", "para", "pear", "pears", "birnen", "pere", "poire", "gruszki"],
    "piersici":  ["piersici", "peach", "peaches", "pfirsich", "pesche", "peche", "brzoskwinie"],
    "caise":     ["caise", "apricot", "apricots", "aprikosen", "albicocche", "abricot", "morele"],
    "cirese":    ["cirese", "cherry", "cherries", "kirschen", "ciliegie", "cerise", "czeresnie"],
    "visine":    ["visine", "sour cherry", "sauerkirschen", "amarene", "wisnie"],
    "zmeura":    ["zmeura", "raspberry", "raspberries", "himbeeren", "lamponi", "framboise", "maliny"],
    "afine":     ["afine", "blueberry", "blueberries", "heidelbeeren", "mirtilli", "myrtille", "borowki"],
    "gutui":     ["gutui", "quince", "quitten", "mela cotogna", "coing"],
    "nuci":      ["nuci", "walnut", "walnuts", "walnusse", "noci", "noix", "orzechy"],
    "oua":       ["oua", "ou", "oua de gaina", "egg", "eggs", "eier", "uova", "oeuf", "jajka"],
    "gogosari":  ["gogosari", "gogosar", "round pepper", "tomato pepper"],
    "gulii":     ["gulii", "gulie", "kohlrabi", "cavolo rapa"],
    "radacinoase":["radacinoase", "root vegetables", "wurzelgemuse", "radacini"],
}

# scop de piata (tag suplimentar)
MARKET = {"local", "intl", "export", "import"}

_SYN = {}
for canon, syns in PRODUCE.items():
    for s in syns:
        _SYN[s.lower().strip()] = canon


def normalize_tag(tag):
    """Returneaza tag-ul canonic daca e produs cunoscut, altfel tag-ul lowercase neschimbat."""
    t = (tag or "").lower().strip()
    return _SYN.get(t, t)


def normalize_tags(tags):
    if isinstance(tags, str):
        tags = tags.split(",")
    out = {normalize_tag(t) for t in (tags or []) if t and t.strip()}
    return sorted(out)


def is_produce(tag):
    return normalize_tag(tag) in PRODUCE


if __name__ == "__main__":
    import sys
    print(",".join(normalize_tags(sys.argv[1] if len(sys.argv) > 1 else "tomaten,export")))
