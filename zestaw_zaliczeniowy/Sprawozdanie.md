# Sprawozdanie - Zestaw Zaliczeniowy AAP - Sebastian Kowalski

**Przedmiot:** Architektura Aplikacji w Pythonie  
**Uczelnia:** WSEI Kraków · semestr letni 2026  
**Prowadzący:** Michał Madejski  
**Termin oddania:** 27.06.2026

---

## Opis ogólny

Zestaw obejmuje sześć laboratoriów, każde z własnym zadaniem samodzielnym. Wspólnym wątkiem jest dataset `stanfordnlp/imdb` (50 000 recenzji filmów z etykietami sentymentu). Każde zadanie buduje na tym samym zbiorze danych, demonstrując inny aspekt inżynierii oprogramowania w Pythonie.

---

## Lab 1 - Dekoratory: `@retry` + `@cache_to_disk`

### Co zostało zaimplementowane

Dwa dekoratory produkcyjnej jakości:

- **`@retry(max_attempts, delay, backoff)`** - ponawia wywołanie funkcji przy wyjątku, z exponential backoff (`time.sleep(delay * backoff**proba)`). Po wyczerpaniu prób re-raise ostatniego wyjątku.
- **`@cache_to_disk(cache_dir)`** - oblicza MD5 z `repr(args) + repr(kwargs)` jako klucz, zapisuje wynik do `{cache_dir}/{func_name}_{key}.json`. Drugie wywołanie z tymi samymi argumentami pomija ciało funkcji.

Kolejność dekoratorów jest kluczowa: `@cache_to_disk` jest zewnętrzny (stosowany pierwszy) - sprawdza cache *przed* uruchomieniem logiki retry.

### Insight: prawdopodobieństwo sukcesu z retry

Dla `max_attempts=5` i `p_fail=0.5` na każdą próbę:

```
P(sukces) = 1 - 0.5^5 = 0.96875 (96.875%)
```

Eksperyment na 100 wywołaniach potwierdza teorię - uzyskujemy zazwyczaj 95–100 sukcesów. Exponential backoff jest standardem w systemach produkcyjnych (AWS SDK, Google Cloud) - zapobiega *thundering herd problem*, gdy wiele klientów próbuje jednocześnie po awarii serwera.

---

## Lab 2 - Współbieżność: `multiprocessing.Pool`

### Co zostało zaimplementowane

Funkcja `sentiment_score(text)` - prosty lexicon-based classifier (9 słów pozytywnych, 9 negatywnych). Porównanie trzech implementacji na 5000 recenzjach:

| Implementacja | Oczekiwane zachowanie |
|---|---|
| Sekwencyjnie | Baseline |
| `ThreadPoolExecutor(16)` | Minimalny zysk lub brak (GIL) |
| `multiprocessing.Pool` | Wyraźne przyspieszenie |

### Insight: GIL i CPU-bound

`sentiment_score` to czysta operacja CPU-bound - `re.findall()` + iteracja po listach. Python GIL pozwala tylko jednemu wątkowi wykonywać bytecode na raz, więc `ThreadPool` nie przyspiesza. `multiprocessing.Pool` tworzy osobne procesy z własnymi interpreterami - każdy ma swój GIL → pełny parallelism.

`chunksize=100` redukuje narzut IPC: zamiast 5000 wiadomości (jedna per tekst) wysyłamy 50 paczek po 100.

Obserwacja dodatkowa: średni score lexikonowy recenzji pozytywnych jest wyższy od negatywnych, co potwierdza że prosty słownik 9+9 słów ma sygnał predykcyjny.

---

## Lab 3 - Testowanie: `Tokenizer` z pytest

### Co zostało zaimplementowane

Klasa `Tokenizer` z konfigurowalnymi parametrami:
- `lower` - sprowadzenie do małych liter
- `strip_html` - usunięcie tagów HTML przez `re.sub(r"<[^>]+>", " ", text)`  
- `min_length` - odfiltrowanie krótkich tokenów
- `vocab(texts)` - unia unikalnych tokenów ze wszystkich tekstów

Testy w `test_tokenizer.py` z użyciem:
- **fixtures** (`tokenizer`, `imdb_sample`)
- **parametrize** - 6 przypadków brzegowych (pusty string, sam HTML, mieszane case, interpunkcja, polskie znaki diakrytyczne, zwykłe zdanie)
- **xfail** - udokumentowane ograniczenie (regex z grupowaniem)

### Insight: rozmiar słownika

100 losowych recenzji imdb → ~5 000–6 000 unikalnych tokenów. Pełne 50 000 recenzji daje ~90 000 tokenów, ale większość to rzadkie słowa (tytuły, imiona, literówki). Klasyczny bag-of-words z pełnym słownikiem prowadzi do macierzy wysokiej wymiarowości - stąd w praktyce stosuje się truncated vocabulary lub TF-IDF z `max_features`.

`@pytest.mark.xfail` to udokumentowane ograniczenie, nie hańba - dużo lepsze niż pominięty test lub flaky test.

---

## Lab 4 - Bazy danych: NoSQL-style w SQLite

### Co zostało zaimplementowane

Schemat `reviews_json (id, doc TEXT)` gdzie `doc` to JSON zawierający:
```json
{
  "text": "...",
  "label": 0,
  "stats": {"word_count": 150, "sentiment_hint": "neg"},
  "tags": ["pierwsza", "trójka", "długich"]
}
```

Cztery zapytania z `json_extract(doc, '$.path')`:
1. Rozkład klas po `sentiment_hint`
2. Średni `word_count` per klasa
3. Recenzje gdzie `tags LIKE '%movie%'` (szuka słów >5 liter zawierających "movie", np. "movies")
4. Top 5 najdłuższych recenzji pozytywnych

### Insight: który schemat jest lepszy?

Dla **tego problemu** - klasyczny schemat SQL jest lepszy:
- Stały schemat (text, label, word_count) - brak potrzeby elastyczności
- Częste agregacje na `word_count` - kolumna natywna vs `json_extract()` (wolniejszy, ~2×)
- Mniejszy rozmiar bazy (JSON duplikuje klucze dla każdego rekordu)

JSON column warto stosować gdy: pola są nieregularne między rekordami, schema ewoluuje szybko, lub czytamy całe dokumenty bez agregacji na ich polach.

---

## Lab 5 - PySpark: Window Functions

### Co zostało zaimplementowane

Cztery operacje z `pyspark.sql.Window`:

1. **Ranking** `row_number()` per klasa po `word_count DESC`
2. **Top 3** najdłuższych recenzji per klasa (`filter(rank <= 3)`)
3. **Różnica od średniej klasowej** - `word_count - AVG(word_count).over(w_avg)`
4. **Moving average** (okno 50 wierszy) - `rowsBetween(-49, 0)` posortowane po `id`
5. **Wykres liniowy** - dwie linie (klasa 0 i 1) moving average

### Insight: leniwość Sparka w debugowaniu

Kiedy leniwość *boli*: błąd w transformacji (np. odwołanie do nieistniejącej kolumny) nie pojawia się przy `.withColumn()` - Spark buduje tylko DAG. Błąd rzucany jest dopiero przy akcji (`.show()`, `.collect()`), a stack trace wskazuje na akcję, nie transformację - utrudnia lokalizację błędu.

**Window functions vs groupBy:** `groupBy` zwraca jeden wiersz per grupę - tracimy dane oryginalne. Window functions zachowują wszystkie wiersze i *doklejają* agregat, co jest kluczowe dla rankingów i porównań per-wiersz.

Obserwacja: obie klasy sentymentu mają podobny profil długości (moving average przebiega podobnie) - długość recenzji sama w sobie nie jest mocnym sygnałem sentymentu.

---

## Lab 6 - Data Quality: DataContract + DataValidator

### Co zostało zaimplementowane

Dwie klasy:
- **`DataContract`** - kontener na reguły, `add_rule(name, callable, severity)`
- **`DataValidator`** - iteruje po regułach, zwraca raport `{rule_name: {passed, severity, details}}`; przy `severity="error"` i niezaliczeniu rzuca `ValueError` (fail fast)

Kontrakt dla imdb z 7 regułami:

| Reguła | Severity | Opis |
|---|---|---|
| `no_nulls` | error | Brak NULL w text i label |
| `labels_in_set` | error | Wszystkie labele ∈ {0, 1} |
| `min_word_count` | error | Każda recenzja ≥ 5 słów |
| `max_word_count` | warning | Żadna recenzja > 2000 słów |
| `no_duplicates` | warning | Brak duplikatów text |
| `class_balance` | error | Stosunek klas 0.5–1.5 |
| `no_html_tags` | warning | Brak HTML (bonus) |

Raport zapisany do `_workspace/data_quality_report.json` z timestampem.

### Insight: kontrakt vs audyt

**Kontrakt** jest proaktywny - dane muszą spełnić reguły *przed* wejściem do pipeline'u. **Audyt** jest reaktywny - sprawdzamy po przetwarzaniu, czy coś poszło nie tak. W produkcji potrzeba obu.

Obserwacja: reguła `no_html_tags` jest `warning` a nie `error` - bo imdb z definicji zawiera HTML (źródło: strony internetowe). ~87% recenzji ma tagi `<br />`. Gdyby była `error`, żadna próbka nie przeszłaby walidacji. Właściwe działanie: raportujemy jako ostrzeżenie i dodajemy krok czyszczenia HTML w preprocessingu.

---

## Podsumowanie

| Lab | Zadanie | Status |
|-----|---------|--------|
| 1 | `@retry` + `@cache_to_disk` | ✅ Zaimplementowane, testy empiryczne zaliczone |
| 2 | `multiprocessing.Pool` + wykres | ✅ 3 implementacje, bar plot |
| 3 | `Tokenizer` + pytest fixtures/parametrize | ✅ Wszystkie testy przechodzą |
| 4 | JSON column SQLite + 4 zapytania | ✅ NoSQL queries + porównanie schematów |
| 5 | PySpark window functions + wykres | ✅ 4 operacje window + moving average |
| 6 | `DataContract` + `DataValidator` + JSON raport | ✅ 7 reguł, fail-fast, raport z timestampem |

Cały notebook jest uruchamialny od góry do dołu (`Run All`). Brak hardkodowanych ścieżek - wszystko korzysta z `WORKDIR = Path("./_workspace")`.
