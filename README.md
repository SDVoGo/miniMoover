# miniMoover

## Panoramica

miniMoover è un software Python progettato per generare **dati simulati** per l'industria 4.0, al fine di creare **proiezioni di ordini** basate su dati reali di macchinari e articoli. Questi dati vengono utilizzati per effettuare **confronti e analisi** in scenari di test, simulando la produzione in un determinato periodo di tempo e tenendo conto di vari fattori come orari lavorativi, capacità delle macchine, disponibilità di operatori e altro.

L'obiettivo è fornire uno strumento utile per **analizzare la capacità di produzione** e **testare applicazioni aziendali** senza utilizzare dati reali o sensibili.

---

## Table of Contents
1. [HowTo](#howto)
2. [Versioni](#versioni)
   - [V2](#v2)
   - [V1](#v1)

---

## HowTo

1. **Preparazione dei file CSV**:
    - Posiziona tutti i file CSV nella cartella `data/`.
    - Il file CSV delle macchine deve essere chiamato **`lista_macchina.csv`** e deve seguire il formato:

    | CODMACCHINA | DESCR MACCHINA | INIZIO LOG | FINE LOG | PRESIDIO | TCARICO | TSCARICO | TSETUP |
    |-------------|----------------|------------|----------|----------|---------|----------|--------|
    | codice macchina | nome macchina | orario inizio | orario fine | necessita operatore | tempo carico | tempo scarico | tempo setup |

    <br>

    - I file CSV degli articoli devono seguire il formato:

    | DITTA | DEPOSITO | CODMACCHINA | DTINILOG | CODREP | STAZIONE | CODOPERATORE | CODART | CODARTOLD | MEAN_TEMPOCICLO | DEVSTD_TEMPOCICLO | MEAN_QTALAV | DEVSTD_QTALAV |
    |-------|----------|-------------|----------|--------|----------|--------------|--------|-----------|-----------------|-------------------|-------------|----------------|
    | codice ditta | codice deposito | codice macchina | data creazione | codice reparto | stazione | codice operatore | codice articolo | vecchio codice (se presente) | tempo ciclo medio | deviazione tempo ciclo | quantità media per ordine | deviazione quantità |

    <br>

2. **Esecuzione dello script**:
    - Dopo aver configurato i CSV, esegui lo script principale:
    ```bash
    python generatore_ordini.py
    ```

3. **Output**:
    - I dati generati saranno salvati nei formati configurati (es. CSV), contenenti **simulazioni di ordini** e informazioni sui tempi di produzione.

---

## Versioni

### V2

- **Utilizzo di Pandas** per la lettura dei CSV.
- **Ottimizzazione della scrittura con Datatable**:
  - Tempo di elaborazione con Pandas (v1): **15 ore**
  - Tempo di elaborazione con Datatable (v2): **0.22 secondi**
- **Aggiunto il calcolo dei tempi di carico e scarico per pezzo lavorato.**
- **Fixato il controllo su macchina presidiata.**

### V1

- **Utilizzo di Pandas** per la lettura dei file CSV.
- **Generazione di dati simulati** per test e proiezioni aziendali.

---
