"use strict";

// Flagi z promptu ewaluacji (python/analyzer/llm/prompts.py).
// good: true  — „tak” jest dobre dla jakości artykułu
// good: false — „tak” jest złe (np. clickbait)
// good: null  — informacja bez oceny
const LLM_FLAGS = {
  contains_unverified_claims:    { label: "Niezweryfikowane twierdzenia", good: false },
  mixes_facts_with_opinions:     { label: "Miesza fakty z opiniami",      good: false },
  data_is_precise:               { label: "Precyzyjne dane",              good: true  },
  has_internal_contradictions:   { label: "Wewnętrzne sprzeczności",      good: false },
  narrative_is_clear:            { label: "Jasna narracja",               good: true  },
  conclusions_follow_from_facts: { label: "Wnioski wynikają z faktów",    good: true  },
  is_opinion_piece:              { label: "Tekst opinii",                 good: null  },
  has_multiple_perspectives:     { label: "Wiele perspektyw",             good: true  },
  headline_matches_content:      { label: "Nagłówek zgodny z treścią",    good: true  },
  maintains_neutral_tone:        { label: "Neutralny ton",                good: true  },
  clickbait_headline:            { label: "Clickbaitowy nagłówek",        good: false },
};

// Klasa i etykieta odznaki flagi. Kolor mówi, czy odpowiedź jest dobra dla jakości,
// a nie czy flaga jest ustawiona. Nieznana flaga (np. ze starszego promptu) nie ma oceny.
function flagBadge(key, value) {
  const flag = LLM_FLAGS[key] || { label: key.replace(/_/g, " "), good: null };
  const text = `${flag.label}: ${value ? "tak" : "nie"}`;
  if (flag.good === null) return { cls: "", text };
  return { cls: Boolean(value) === flag.good ? "pf-badge--success" : "pf-badge--error", text };
}

module.exports = { flagBadge };
