import os
import sqlite3
import json
import gzip
import urllib.request
import sys

URL = "https://kaikki.org/dictionary/downloads/it/it-extract.jsonl.gz"
GZ_FILE = "it-extract.jsonl.gz"
DB_FILE = "dictionary.db"

def build_db():
    if not os.path.exists(GZ_FILE):
        print(f"Downloading {URL}...")
        try:
            urllib.request.urlretrieve(URL, GZ_FILE)
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading: {e}")
            sys.exit(1)

    print("Building SQLite database...")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dictionary (
        word TEXT PRIMARY KEY,
        definition TEXT,
        etymology TEXT
    )
    ''')
    
    # We will use a transaction for speed
    cursor.execute('BEGIN TRANSACTION')
    
    count = 0
    with gzip.open(GZ_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
            except:
                continue
                
            # Kaikki dumps are already filtered if downloaded from /it/, but just to be sure:
            if data.get('lang_code') != 'it':
                continue
                
            word = data.get('word')
            if not word:
                continue
                
            # Extract first meaning
            definition = ""
            if 'senses' in data and data['senses']:
                senses = data['senses']
                # Sometimes a sense has glosses
                glosses = []
                for s in senses:
                    if 'glosses' in s:
                        glosses.extend(s['glosses'])
                if glosses:
                    # Join multiple glosses or just take the first
                    definition = glosses[0]
                    
            if not definition:
                continue # Skip if no definition
                
            # Extract etymology
            etymology = ""
            if 'etymology_texts' in data and data['etymology_texts']:
                etymology = "\n".join(data['etymology_texts'])
            elif 'etymology_templates' in data and data['etymology_templates']:
                # sometimes it's just templates, try to extract args
                pass # usually etymology_texts is populated in kaikki
                
            # Insert or ignore (there can be multiple POS for the same word, we just take the first or update)
            # Actually, insert or replace is better to capture the one with etymology if earlier didn't have it
            # But let's just insert or ignore for speed and simplicity. 
            cursor.execute('''
            INSERT OR IGNORE INTO dictionary (word, definition, etymology)
            VALUES (?, ?, ?)
            ''', (word.lower(), definition, etymology))
            
            count += 1
            if count % 100000 == 0:
                print(f"Processed {count} entries...")
                
    cursor.execute('COMMIT')
    cursor.execute('CREATE INDEX idx_word ON dictionary(word)')
    conn.close()
    
    print(f"Done! Database built successfully with {count} processed entries.")
    
    # Clean up gz file
    if os.path.exists(GZ_FILE):
        os.remove(GZ_FILE)

if __name__ == "__main__":
    build_db()
