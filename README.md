# <p align="center">miniMoover</p>
### Panoramica
miniMoover è un software su base Python che crea dati ben strutturati basandosi su csv. Il suo scopo è quelo di creare una proiezione possibile di ordini in un certo periodo di tempo per l'industria 4.0. Dato un file csv di macchinari e un qualsiasi file csv con i dati degli articoli ricava ordini possibili considerando gli orari lavorativi, le possibilità della macchina, la presenza di operatori e altro...

## HowTo
1. Per prima cosa tutti i csv dovranno trovarsi nella cartella "data".
2. Un csv con la lista delle macchine dovrà chiamarsi "lista macchina.csv". Formattazione come segue:

    CODMACCHINA | DESCR MACCHINA | INIZIO LOG | FINE LOG | PRESIDIO | TCARICO | TSCARICO | TSETUP
    ----------------|---------------|----------------------|-------------------|---------------------|--------------------|---------------------|----------------------
    codice macchina | nome macchina | Inizio processazione | Fine processazione| necessita operatore | tempo carico pezzo | tempo scarico pezzo | tempo cambio articolo

3. I csv con gli articoli vanno formattati in questo mo 
    DITTA	DEPOSITO | CODMACCHINA | DTINILOG | CODREP | STAZIONE | CODOPERATORE | CODART | CODARTOLD | MEAN_TEMPOCICLO | DEVSTD_TEMPOCICLO | MEAN_QTALAV | DEVSTD_QTALAV
    ---------|-------|-------------|------------i ----------|------------------------|-----|--------------------|------------------------------|-----------------
    codice ditta | codice macchina | data creazione prodotto | stazione in cui si è svolta | codice del reparto ! vecchio codice (se presente) | media del tempo impeigato per pezzo | Deviazione standard fra gli ordini | media quantità per ordine | deviazione standard della quantità lavorata 

## miniMoover V2
* Utilizzo di Pandas per la lettura dei csv
* Ottimizzazione scrittura con Datatable
* Creazione di CSV MIGLIORATA

   Libreria | Tempo impiegato
  -----------|----------------
  Pandas (v1)| 15 hrs
  Datatable  | 0.22 sec
  
* Aggiunto tempo di carico e scarico per pezzo lavorato
* Fixato controllo su macchina presidiata

## miniMoover V1
* Utilizzo di Pandas per la lettura dei csv necessari.
* Creazione di dati ma non di output.
