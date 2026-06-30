"""Database vocabbolario — gestione file markdown."""

import os
import re
import yaml
from datetime import datetime, timedelta

from constants import debug_log


class WordDatabase:
    def __init__(self, directory):
        self.directory = directory
        self.words = {}
        self.sayings = {}
        os.makedirs(self.directory, exist_ok=True)
        self._init_data()

    def _init_data(self):
        """Singola passata: migrazione + caricamento in memoria."""
        for filename in os.listdir(self.directory):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(self.directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            metadata = {}
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                try:
                    metadata = yaml.safe_load(match.group(1)) or {}
                except Exception:
                    pass

            dirty = False
            definition = ""
            etymology = ""
            synonyms = []

            sig_match = re.search(r'## 📖 Significato\n(.*?)(?=## |\Z)', content, re.DOTALL)
            if sig_match:
                definition = sig_match.group(1).strip()
            else:
                definition = content.split("---")[-1].strip()

            if 'Etimologia:' in definition or 'Origine:' in definition:
                parts = re.split(r'(?i)\n\s*\**\b(Etimologia|Origine)\b\**:', definition, 1)
                if len(parts) == 3:
                    definition = parts[0].strip()
                    etymology = parts[2].strip()
                    dirty = True

            ety_match = re.search(r'## 🏛️ Etimologia\n(.*?)(?=## |\Z)', content, re.DOTALL)
            if ety_match:
                etymology = ety_match.group(1).strip()

            syn_match = re.search(r'## Sinonimi\n(.*)', content, re.DOTALL)
            if not syn_match:
                syn_match = re.search(r'## Detti Simili\n(.*)', content, re.DOTALL)

            if syn_match:
                lines = syn_match.group(1).strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('- [[') and line.endswith(']]'):
                        synonyms.append(line[4:-2])
            else:
                if "Sinonimi" in content or "Detti Simili" in content:
                    dirty = True

            if metadata.get('type') == 'word' and 'campo_semantico' in metadata:
                del metadata['campo_semantico']
                dirty = True

            if dirty:
                item_name = filename.replace(".md", "").replace("_", " ")
                item_type = metadata.get('type', 'word')
                extra = {k: v for k, v in metadata.items() if k not in ['type', 'created', 'campo_semantico']}
                self._write_file(filepath, item_name, definition, etymology, synonyms, metadata.get('created', ''), item_type, extra_metadata=extra)

            # Popola i dict in memoria (stessa logica di load_data)
            item_type = metadata.get('type')
            if item_type not in ['word', 'detto']:
                continue
            item_name = filename.replace(".md", "").replace("_", " ")
            info = {
                "filepath": filepath,
                "word": item_name,
                "definition": definition,
                "etymology": etymology,
                "synonyms": synonyms,
                "metadata": metadata
            }
            if item_type == 'detto':
                self.sayings[item_name] = info
            else:
                self.words[item_name] = info

    def load_data(self):
        """Ricarica tutti i file dal disco (usare solo per bulk refresh)."""
        self.words = {}
        self.sayings = {}
        for filename in os.listdir(self.directory):
            if filename.endswith(".md"):
                filepath = os.path.join(self.directory, filename)
                info = self._parse_file(filepath)
                if info:
                    if info['metadata'].get('type') == 'detto':
                        self.sayings[info['word']] = info
                    else:
                        self.words[info['word']] = info

    def _write_file(self, filepath, item_name, definition, etymology, links, created_date, item_type, extra_metadata=None):
        metadata = {
            "type": item_type,
            "created": created_date or datetime.now().strftime("%Y-%m-%d")
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        yaml_str = yaml.dump(metadata, sort_keys=False, default_flow_style=None, allow_unicode=True).strip()

        links_str = ""
        title_prefix = "Parola: " if item_type == "word" else "Detto: "
        link_heading = "## Sinonimi" if item_type == "word" else "## Detti Simili"

        ety_str = f"\n\n## 🏛️ Etimologia\n{etymology}" if etymology else ""
        if links:
            links_str = f"\n\n{link_heading}\n" + "\n".join(f"- [[{s}]]" for s in links)

        content = f"---\n{yaml_str}\n---\n\n# {title_prefix}{item_name}\n\n## 📖 Significato\n{definition}{ety_str}{links_str}\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def load_data(self):
        self.words = {}
        self.sayings = {}
        for filename in os.listdir(self.directory):
            if filename.endswith(".md"):
                filepath = os.path.join(self.directory, filename)
                info = self._parse_file(filepath)
                if info:
                    if info['metadata'].get('type') == 'detto':
                        self.sayings[info['word']] = info
                    else:
                        self.words[info['word']] = info

    def _parse_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return None

        metadata = {}
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            try:
                metadata = yaml.safe_load(match.group(1)) or {}
            except Exception:
                pass

        item_type = metadata.get('type')
        if item_type not in ['word', 'detto']:
            return None

        item_name = os.path.basename(filepath).replace(".md", "").replace("_", " ")

        definition = ""
        etymology = ""
        links = []

        sig_match = re.search(r'## 📖 Significato\n(.*?)(?=## |\Z)', content, re.DOTALL)
        if sig_match:
            definition = sig_match.group(1).strip()

        ety_match = re.search(r'## 🏛️ Etimologia\n(.*?)(?=## |\Z)', content, re.DOTALL)
        if ety_match:
            etymology = ety_match.group(1).strip()

        syn_match = re.search(r'## (?:Sinonimi|Detti Simili)\n(.*)', content, re.DOTALL)
        if syn_match:
            lines = syn_match.group(1).strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- [[') and line.endswith(']]'):
                    syn = line[4:-2]
                    links.append(syn)

        return {
            "filepath": filepath,
            "word": item_name,
            "definition": definition,
            "etymology": etymology,
            "synonyms": links,
            "metadata": metadata
        }

    def save_item(self, item_name, definition, etymology, links, item_type="word", extra_fields=None):
        clean_name = re.sub(r'[<>:"/\\|?*]', '', item_name).strip().replace(" ", "_")
        filepath = os.path.join(self.directory, f"{clean_name}.md")

        created = datetime.now().strftime("%Y-%m-%d")
        target_dict = self.words if item_type == "word" else self.sayings

        extra_metadata = {}
        if item_name in target_dict:
            old_meta = target_dict[item_name]['metadata']
            created = old_meta.get('created', created)
            for key in ['repetitions', 'interval', 'easiness', 'last_reviewed', 'next_review', 'pronuncia']:
                if key in old_meta:
                    extra_metadata[key] = old_meta[key]

        if extra_fields:
            extra_metadata.update(extra_fields)

        self._write_file(filepath, item_name, definition, etymology, links, created, item_type, extra_metadata=extra_metadata)
        self._refresh_item(filepath)

    def _refresh_item(self, filepath):
        """Aggiorna un singolo item in memoria senza rileggere tutti i file."""
        # Rimuovi prima la vecchia entry che punta a questo filepath
        # (gestisce rename: il nome potrebbe essere cambiato)
        for d in (self.words, self.sayings):
            stale_key = None
            for key, val in d.items():
                if val.get('filepath') == filepath:
                    stale_key = key
                    break
            if stale_key is not None:
                del d[stale_key]

        info = self._parse_file(filepath)
        if not info:
            return
        if info['metadata'].get('type') == 'detto':
            self.sayings[info['word']] = info
        else:
            self.words[info['word']] = info

    def _remove_item(self, item_name, item_type):
        """Rimuovi un item dai dict in memoria."""
        target_dict = self.words if item_type == "word" else self.sayings
        target_dict.pop(item_name, None)

    def update_spaced_repetition(self, item_name, item_type, quality):
        target_dict = self.words if item_type == "word" else self.sayings
        if item_name not in target_dict:
            return

        info = target_dict[item_name]
        old_meta = info['metadata']

        repetitions = int(old_meta.get('repetitions', 0))
        interval = int(old_meta.get('interval', 0))
        easiness = float(old_meta.get('easiness', 2.5))

        # Algoritmo SM-2
        easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if easiness < 1.3:
            easiness = 1.3

        if quality < 3:
            repetitions = 0
            interval = 1
        else:
            repetitions += 1
            if repetitions == 1:
                interval = 1
            elif repetitions == 2:
                interval = 6
            else:
                interval = round(interval * easiness)

        last_reviewed = datetime.now().strftime("%Y-%m-%d")
        next_review = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")

        extra_metadata = {
            "repetitions": repetitions,
            "interval": interval,
            "easiness": round(easiness, 2),
            "last_reviewed": last_reviewed,
            "next_review": next_review
        }
        if "pronuncia" in old_meta:
            extra_metadata["pronuncia"] = old_meta["pronuncia"]

        self._write_file(
            info['filepath'],
            item_name,
            info['definition'],
            info['etymology'],
            info['synonyms'],
            old_meta.get('created', ''),
            item_type,
            extra_metadata=extra_metadata
        )
        self._refresh_item(info['filepath'])

    def delete_item(self, item_name, item_type="word"):
        target_dict = self.words if item_type == "word" else self.sayings
        if item_name in target_dict:
            filepath = target_dict[item_name]['filepath']
            if os.path.exists(filepath):
                os.remove(filepath)
            self._remove_item(item_name, item_type)
