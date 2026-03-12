"""
Szablony promptów dla oceny LLM.

Prompt jest napisany po polsku i oczekuje odpowiedzi w formacie JSON.
Pokrywa trzy wymiary niedostępne dla analizy deterministycznej:
  - Faktyczność
  - Logika i spójność narracyjna
  - Standardy dziennikarskie
"""

ARTICLE_EVALUATION_PROMPT = """\
Jesteś ekspertem oceniającym jakość dziennikarstwa. Przeanalizuj poniższy artykuł \
prasowy pod kątem trzech kryteriów i przyznaj oceny od 0 do 100.

════════════════════════════════════════════
KRYTERIA OCENY
════════════════════════════════════════════

1. FAKTYCZNOŚĆ (0–100)
   Oceń, na ile twierdzenia zawarte w artykule są:
   • Weryfikowalne lub oparte na danych / badaniach / dokumentach.
   • Precyzyjne — daty, liczby, nazwy są spójne i właściwe.
   • Odróżniane od opinii (fakty nie są prezentowane jako subiektywne odczucia i odwrotnie).
   • Wolne od spekulacji przedstawianych jako fakty.
   Obniż ocenę jeśli: artykuł zawiera niezweryfikowane twierdzenia, przekłamane dane,
   lub miesza fakty z domysłami.

2. LOGIKA I SPÓJNOŚĆ (0–100)
   Oceń, czy:
   • Artykuł jest wewnętrznie spójny (brak sprzeczności między akapitami).
   • Argumentacja prowadzi logicznie do konkluzji.
   • Narracja jest klarowna i dobrze ustrukturyzowana.
   • Wnioski wynikają z przedstawionych faktów, a nie są arbitralne.
   Obniż ocenę jeśli: artykuł zawiera wewnętrzne sprzeczności, zrywa wątek lub wyciąga
   nieuzasadnione wnioski.

3. STANDARDY DZIENNIKARSKIE (0–100)
   Oceń, czy artykuł:
   • Prezentuje wiele perspektyw (jeśli temat jest kontrowersyjny lub wielostronny).
   • Wyraźnie oddziela fakty od opinii i komentarza.
   • Zachowuje neutralny, zrównoważony ton (lub — jeśli to felieton/komentarz —
     czy jest to wyraźnie zaznaczone).
   • Nagłówek rzetelnie odzwierciedla treść (bez clickbaitu).
   • Przestrzega podstawowych zasad etyki dziennikarskiej.
   Obniż ocenę jeśli: artykuł jest jednostronny, nagłówek mija się z treścią,
   lub prezentuje opinię jako obiektywny fakt.

════════════════════════════════════════════
ARTYKUŁ DO OCENY
════════════════════════════════════════════

Tytuł: {title}

Treść:
{content}

════════════════════════════════════════════
FORMAT ODPOWIEDZI
════════════════════════════════════════════

Odpowiedz WYŁĄCZNIE poprawnym JSON-em (bez żadnego tekstu przed ani po):

{{
  "factuality": {{
    "score": <liczba całkowita 0-100>,
    "description": "<uzasadnienie oceny: max 3 zdania po polsku>",
    "flags": {{
      "contains_unverified_claims": <true|false>,
      "mixes_facts_with_opinions":  <true|false>,
      "data_is_precise":            <true|false>
    }}
  }},
  "logic": {{
    "score": <liczba całkowita 0-100>,
    "description": "<uzasadnienie oceny: max 3 zdania po polsku>",
    "flags": {{
      "has_internal_contradictions":   <true|false>,
      "narrative_is_clear":            <true|false>,
      "conclusions_follow_from_facts": <true|false>
    }}
  }},
  "journalism": {{
    "score": <liczba całkowita 0-100>,
    "description": "<uzasadnienie oceny: max 3 zdania po polsku>",
    "flags": {{
      "is_opinion_piece":           <true|false>,
      "has_multiple_perspectives":  <true|false>,
      "headline_matches_content":   <true|false>,
      "maintains_neutral_tone":     <true|false>,
      "clickbait_headline":         <true|false>
    }}
  }},
  "overall_description": "<ogólna ocena jakości artykułu: max 4 zdania po polsku>"
}}
"""
