"""Text-to-Speech — riproduzione audio tramite macOS `say`."""

import re
import subprocess
import threading


class TTS:
    _cached_voice = None
    _voice_resolved = False

    @staticmethod
    def get_all_italian_voices():
        try:
            res = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
            voices = res.stdout.splitlines()
            available_voices = []
            for line in voices:
                if "it_IT" in line:
                    idx = line.find("it_IT")
                    if idx != -1:
                        voice_name = line[:idx].strip()
                        available_voices.append(voice_name)
            return available_voices
        except Exception:
            return []

    @staticmethod
    def get_best_italian_voice():
        if TTS._voice_resolved:
            return TTS._cached_voice
        available_voices = TTS.get_all_italian_voices()
        # Preferisci esplicitamente la voce Alice
        for v in available_voices:
            if "alice" in v.lower():
                TTS._cached_voice = v
                TTS._voice_resolved = True
                return v
        # Fallback ad altre voci italiane se Alice non è disponibile
        preferences = ["Eddy", "Flo", "Luca", "Paola", "Grandpa", "Rocko", "Sandy", "Shelley"]
        for pref in preferences:
            for v in available_voices:
                if pref.lower() in v.lower():
                    TTS._cached_voice = v
                    TTS._voice_resolved = True
                    return v
        TTS._cached_voice = available_voices[0] if available_voices else None
        TTS._voice_resolved = True
        return TTS._cached_voice

    @staticmethod
    def clean_text_for_speech(text):
        if not text:
            return ""
        # Rimuovi link markdown
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Rimuovi formattazione markdown
        text = text.replace("*", "").replace("#", "").replace("_", "")
        # Rimuovi caratteri non leggibili lasciando accenti e punteggiatura utile
        text = re.sub(r'[^\x00-\x7FàèéìòùÀÈÉÌÒÙ\s,.;:!?\'"\-]', '', text)
        return text.strip()

    @staticmethod
    def speak(text):
        if not text:
            return
        cleaned = TTS.clean_text_for_speech(text)
        voice = TTS.get_best_italian_voice()

        def _run():
            try:
                cmd = ["say"]
                if voice:
                    cmd.extend(["-v", voice])
                cmd.append(cleaned)
                subprocess.run(cmd)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()
