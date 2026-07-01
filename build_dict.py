"""Costruisce dictionary.db da kaikki.org (Wiktionary italiano).

Scarica it-extract.jsonl.gz e crea un database SQLite con definizioni
complete (tutti i sensi aggregati), etimologie, sinonimi e pronuncia
accentata per ogni parola.
"""

import os
import sqlite3
import json
import gzip
import urllib.request
import sys

URL = "https://kaikki.org/dictionary/downloads/it/it-extract.jsonl.gz"
GZ_FILE = "it-extract.jsonl.gz"
DB_FILE = "dictionary.db"


def _accented_from_hyphenation(parts):
    """Ricostruisce la parola con l'accento tonico dalla sillabazione.
    
    Le sillabazioni di Wiktionary italiano marcano la sillaba tonica
    con un accento grafico, es. ['pu', 'sil', 'là', 'ni', 'me'].
    Restituisce la parola unita, es. 'pusillànime'.
    """
    if not parts:
        return ""
    return "".join(parts)


def build_db():
    # ── 1. Download ────────────────────────────────────────────────
    if not os.path.exists(GZ_FILE):
        print(f"Downloading {URL} ...")
        try:
            urllib.request.urlretrieve(URL, GZ_FILE)
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading: {e}")
            sys.exit(1)
    else:
        print(f"Using existing {GZ_FILE}")

    # ── 2. Prima passata: aggrega tutti i dati per ogni lemma ──────
    print("Pass 1 — Aggregating senses, etymologies, synonyms and pronunciation ...")

    aggregated = {}
    line_count = 0

    with gzip.open(GZ_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            line_count += 1
            try:
                data = json.loads(line)
            except Exception:
                continue

            if data.get("lang_code") != "it":
                continue

            word = data.get("word", "").strip()
            if not word:
                continue

            word_lower = word.lower()
            pos = data.get("pos", "")

            # Glosses
            glosses = []
            for s in data.get("senses", []):
                for g in s.get("glosses", []):
                    g_clean = g.strip()
                    if g_clean and g_clean.lower() != word_lower:
                        if "( approfondimento)" in g_clean or "( citazioni)" in g_clean:
                            continue
                        glosses.append(g_clean)

            # Etimologia
            ety_texts = data.get("etymology_texts", [])

            # Sinonimi
            synonyms_raw = data.get("synonyms", [])
            synonyms = []
            for syn in synonyms_raw:
                sw = syn.get("word", "").strip()
                if sw and sw.lower() != word_lower:
                    synonyms.append(sw)

            # Pronuncia accentata dalle hyphenations
            hyphenations = data.get("hyphenations", [])
            accented = ""
            if hyphenations:
                parts = hyphenations[0].get("parts", [])
                accented = _accented_from_hyphenation(parts)
                # Verifica che l'accento sia effettivamente diverso dalla parola base
                if accented.lower().replace("à", "a").replace("è", "e").replace("é", "e").replace("ì", "i").replace("ò", "o").replace("ó", "o").replace("ù", "u") == word_lower:
                    pass  # OK, ha un accento in più
                else:
                    # Se unendo le sillabe non si ottiene la parola originale, scarta
                    if accented.lower() != word_lower:
                        accented = ""

            if word_lower not in aggregated:
                aggregated[word_lower] = {
                    "word_display": word,
                    "senses": [],
                    "etymologies": set(),
                    "synonyms": set(),
                    "accented": "",
                }

            entry = aggregated[word_lower]

            if glosses:
                entry["senses"].append({"pos": pos, "glosses": glosses})

            for et in ety_texts:
                et_clean = et.strip()
                if et_clean:
                    entry["etymologies"].add(et_clean)

            for syn in synonyms:
                entry["synonyms"].add(syn)

            # Preferisci la forma accentata più lunga (più dettagliata)
            if accented and (not entry["accented"] or len(accented) > len(entry["accented"])):
                entry["accented"] = accented

            if line_count % 200000 == 0:
                print(f"  ... {line_count} lines, {len(aggregated)} unique words")

    print(f"Pass 1 done: {line_count} lines read, {len(aggregated)} unique words aggregated.")

    # ── 3. Seconda passata: costruisci DB ──────────────────────────
    print("Pass 2 — Building SQLite database ...")

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE dictionary (
        word TEXT PRIMARY KEY,
        definition TEXT,
        etymology TEXT,
        synonyms TEXT,
        accented TEXT
    )
    """)

    cursor.execute("BEGIN TRANSACTION")

    inserted = 0
    skipped_empty = 0
    with_synonyms = 0
    with_accented = 0

    POS_MAP = {
        "noun": "s.",
        "verb": "v.",
        "adj": "agg.",
        "adv": "avv.",
        "pron": "pron.",
        "prep": "prep.",
        "conj": "cong.",
        "intj": "inter.",
        "det": "det.",
        "num": "num.",
        "particle": "part.",
        "affix": "affisso",
        "prefix": "pref.",
        "suffix": "suff.",
        "phrase": "loc.",
        "proverb": "prov.",
        "name": "n. proprio",
    }

    for word_lower, entry in aggregated.items():
        senses = entry["senses"]
        etymologies = entry["etymologies"]
        synonyms = entry["synonyms"]
        accented = entry["accented"]

        if not senses:
            skipped_empty += 1
            continue

        # ── Definizione ────────────────────────────────────────────
        definition_parts = []
        seen_glosses = set()

        pos_groups = {}
        for sense_entry in senses:
            pos = sense_entry["pos"]
            if pos not in pos_groups:
                pos_groups[pos] = []
            pos_groups[pos].extend(sense_entry["glosses"])

        for pos, glosses_list in pos_groups.items():
            pos_label = POS_MAP.get(pos, pos)

            unique_glosses = []
            for g in glosses_list:
                g_norm = g.lower().strip().rstrip(".")
                if g_norm not in seen_glosses and len(g_norm) > 1:
                    seen_glosses.add(g_norm)
                    unique_glosses.append(g)

            if not unique_glosses:
                continue

            if len(pos_groups) > 1:
                numbered = [f"{i} {g}" for i, g in enumerate(unique_glosses, 1)]
                block = f"{pos_label} {'; '.join(numbered)}" if len(unique_glosses) <= 2 else f"{pos_label}\n" + "\n".join(numbered)
            else:
                if len(unique_glosses) == 1:
                    block = f"{pos_label} {unique_glosses[0]}"
                else:
                    numbered = [f"{i} {g}" for i, g in enumerate(unique_glosses, 1)]
                    block = f"{pos_label}\n" + "\n".join(numbered)

            definition_parts.append(block)

        definition = "\n\n".join(definition_parts)

        if not definition.strip():
            skipped_empty += 1
            continue

        # ── Etimologia ─────────────────────────────────────────────
        ety_list = sorted(etymologies, key=len, reverse=True)
        if ety_list:
            etymology = ety_list[0]
            for extra in ety_list[1:3]:
                if extra.lower() not in etymology.lower() and len(extra) > 20:
                    etymology += "\n" + extra
        else:
            etymology = ""

        # ── Sinonimi ───────────────────────────────────────────────
        synonyms_str = ", ".join(sorted(synonyms)) if synonyms else ""

        # ── Pronuncia accentata ────────────────────────────────────
        # Solo se ha un accento effettivo diverso dalla parola semplice
        accented_str = ""
        if accented and accented.lower() != word_lower:
            accented_str = accented

        cursor.execute(
            "INSERT OR REPLACE INTO dictionary (word, definition, etymology, synonyms, accented) VALUES (?, ?, ?, ?, ?)",
            (word_lower, definition, etymology, synonyms_str, accented_str),
        )
        inserted += 1
        if synonyms_str:
            with_synonyms += 1
        if accented_str:
            with_accented += 1

        if inserted % 100000 == 0:
            print(f"  ... {inserted} words inserted")

    cursor.execute("COMMIT")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_word ON dictionary(word)")
    conn.close()

    print(f"\nDone! Database built successfully.")
    print(f"  Words inserted:    {inserted}")
    print(f"  With synonyms:     {with_synonyms}")
    print(f"  With accented:     {with_accented}")
    print(f"  Skipped (no def):  {skipped_empty}")
    print(f"  DB size:           {os.path.getsize(DB_FILE) / 1024 / 1024:.1f} MB")

    # Clean up gz file
    if os.path.exists(GZ_FILE):
        os.remove(GZ_FILE)
        print(f"  Cleaned up {GZ_FILE}")


if __name__ == "__main__":
    build_db()
