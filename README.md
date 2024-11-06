# Influence Prediction Experiments

## Descrizione

È stato creato uno script shell denominato experiments.sh che prende un file CSV così formato:
- Il primo valore di ogni riga è sempre il predicato target.
- I valori successivi sono i predicati da includere volta per volta.

Lo script esegue lo script Python di training per ogni riga del file CSV e genera una cartella denominata `$target_predicate_$counter` nel percorso `experiments/training`, dove `$counter` serve a differenziare per uno `$target_predicate` i risultati di esperimenti ottenuti con diverse combinazioni di predicati da includere.

## Esempio del file CSV

```csv
http://w3id.org/friendshipneverends/ontology/admires,http://w3id.org/friendshipneverends/ontology/hasAcquaintance,http://w3id.org/friendshipneverends/ontology/predecessor10YearsOf
http://w3id.org/friendshipneverends/ontology/admires,http://w3id.org/friendshipneverends/ontology/hasFriend
http://w3id.org/friendshipneverends/ontology/admires,http://w3id.org/friendshipneverends/ontology/hasAcquaintance
http://w3id.org/friendshipneverends/ontology/hasFriend,http://w3id.org/friendshipneverends/ontology/admires,http://w3id.org/friendshipneverends/ontology/hasAcquaintance
```

## Struttura delle cartelle

In questo caso verranno create in `experiments/training` 4 cartelle, ossia una per ogni riga del file CSV in questo modo:

```
experiments
└── training
    ├── admires_1
    ├── admires_2
    ├── admires_3
    └── hasFriend_1
```

## Output degli esperimenti

Ogni giro di esperimento produce un file `relationship_weights_summary.txt` dove è immediatamente possibile vedere il predicato target selezionato e i pesi trovati (in questo modo si vedono bene anche i predicati inclusi). Il report è per ogni modello, grado e numero di esperimento.

La generazione del report è a carico di un secondo script che si chiama `report.sh`, abilitare se necessario i permessi di esecuzione con `chmod +x report.sh`.

### Esempio di `relationship_weights_summary.txt`

```
Relationship Weights Summary
=================
Target predicate: http://w3id.org/friendshipneverends/ontology/admires

Experiment 1, Model: fit, Degree: 1
http://w3id.org/friendshipneverends/ontology/hasFriend: 1.9459830864877747
http://w3id.org/friendshipneverends/ontology/hasAcquaintance: 1.9450385235733776
http://w3id.org/friendshipneverends/ontology/predecessor10YearsOf: 1.9593528590621423
http://w3id.org/friendshipneverends/ontology/predecessor20YearsOf: 1.951938364388664
http://w3id.org/friendshipneverends/ontology/predecessor30YearsOf: 1.9524634612326088
http://w3id.org/friendshipneverends/ontology/hasBandmate: 1.9455603397828591
http://w3id.org/friendshipneverends/ontology/hasMentor: 1.9510830771296988
http://w3id.org/friendshipneverends/ontology/hasAdmirator: 1.9510355916960718
http://w3id.org/friendshipneverends/ontology/hasPupil: 1.9462307462120074
```