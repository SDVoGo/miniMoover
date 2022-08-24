from collections import OrderedDict
from rich import print
import rich.progress as pro
from datetime import datetime, timedelta
from random import randrange
import sys
import pandas as pd
import os
from uuid import uuid4
import datatable as dt
from shelve import open
from lib.utils import print_warning, straordinari, distribuzione_normale, flat_to_dict, get_project_root as root, print_log
from pathlib import Path

campi_insert = ["DITTA","DEPOSITO","CODMACCHINA","STAZIONE","NUMREG","PROGRIGA","CODARTICOLO","VARIANTE","STARTDATE","ENDDATE","QTAORDINE","TEMPO","TEMPOPEZZO","CONTAPEZZI","CODFASE","CODREPARTO","CODOPERATORE","STATOMACCHINA","DATACONSOLIDAMENTO"]

# Elaborazione giornata lavorativa
def elabora_giornata(orario:list, lista_articoli_possibili_macchina, macchina):
    # nel ciclo Turni 
    # turno [0]: orario inizio del turno
    # turno [1]: orario fine del turno
    lista_lavorazioni_giornata = []
    for turno in orario:
        local_flag_presidiata = bool(macchina["PRESIDIO"])
        # Orario corrente è l'ora attuale per capire come siamo messi con i tempi, ad inizio turno prende il l'orario di turno[0] ovviamente
        orario_corrente = turno[0]
        # Finchè c'è tempo (Almeno il tempo del setup)
        while orario_corrente + timedelta(seconds=macchina["TSETUP"]) < turno[1]:
            # Creazione dell'ordine (provvisorio)
            # Numero righe
            ordine = {"num_righe_prov":randrange(1,15), "NUMREG_PROV": str(uuid4()), "righe": []}
            # Fase 1: Scelta articoli (X nel ciclo è il PROGRIGA)
            tmp_lista_index_articoli = []
            for x in range(ordine["num_righe_prov"]):
                index_articolo = randrange(0, len(lista_articoli_possibili_macchina))
                # Panic Protocol: Per non rischiare il loop infinito
                tmp_panic_counter = 0
                # Se l'articolo è già presente in una riga dell'ordine o non esisteva al momento della data da elaborare (=> il codartold non esiste)
                while index_articolo in tmp_lista_index_articoli or (datetime.strptime(lista_articoli_possibili_macchina[index_articolo]["DTINILOG"], "%d/%m/%Y") > turno[0] and pd.isnull(lista_articoli_possibili_macchina[index_articolo]["CODARTOLD"])):
                    tmp_panic_counter +=1
                    if tmp_panic_counter == len(lista_articoli_possibili_macchina)*3:
                        # PANIC CHECKER
                        print_warning("Confermato loop infinito. Uscita forzata.")
                        sys.exit()
                        ##
                    index_articolo = randrange(0, len(lista_articoli_possibili_macchina))
                tmp_lista_index_articoli.append(index_articolo)
                ordine["righe"].append({"NUMREG":ordine["NUMREG_PROV"],"PROGRIGA":x+1, "index articolo":index_articolo, "CODART":lista_articoli_possibili_macchina[index_articolo]["CODART"] if datetime.strptime(lista_articoli_possibili_macchina[index_articolo]["DTINILOG"], "%d/%m/%Y")<=turno[0] else lista_articoli_possibili_macchina[index_articolo]["CODARTOLD"]})
                tmp_articolo_selezionato = lista_articoli_possibili_macchina[index]
                # Andamento produzione:
                # TODO Aggiungere casi di modalità produzione in un secondo momento [sotto, normale, sovra]
                # NOTE Attenzione: per semplificare il programma la feature qta_ordine != contapezzi non è stata implementata
                ordine["righe"][x]["qta_ordine"] = distribuzione_normale(tmp_articolo_selezionato["MEAN_QTALAV"],tmp_articolo_selezionato["DEVSTD_QTALAV"])[0]
                ordine["righe"][x]["tempo_ciclo"] = distribuzione_normale(tmp_articolo_selezionato["MEAN_TEMPOCICLO"],tmp_articolo_selezionato["DEVSTD_TEMPOCICLO"], ordine["righe"][x]["qta_ordine"])
            # Fase 2: Controllo fattibilità riga
            # Cicla Righe
            for riga in ordine["righe"]:
                # Aggiungere tempo di setup
                orario_corrente += timedelta(seconds=macchina["TSETUP"])
                tempo_impiegato = 0
                # Setup base
                riga["contapezzi"] = 0
                riga["inizio lavorazione"] = orario_corrente
                # Cicla Pezzi
                for tempo_pezzo in riga["tempo_ciclo"]:
                    # Se il tempo di corrente più il tempo della lavorazione del pezzo (TCARICO + (T)LAVORAZIONE PEZZO + TSCARICO) rientra nel fine turno
                    if orario_corrente + timedelta(seconds=tempo_impiegato+macchina["TCARICO"]+tempo_pezzo+macchina["TSCARICO"]) < turno[1]:
                        # Assoda sia il tempo che il pezzo
                        riga["contapezzi"] += 1
                        tempo_impiegato += tempo_pezzo
                    else:
                        # Nel caso in cui non ci rientri, controllare se la macchina può comunque lavorare il pezzo
                        if local_flag_presidiata:
                            # Assoda sia il tempo che il pezzo
                            riga["contapezzi"] += 1
                            tempo_impiegato += tempo_pezzo
                            # Il "jolly" presidiato è stato giocato, il prossimo pezzo non verrà elaborato
                            local_flag_presidiata = False
                        # In ogno caso esci dal for, inutile elaborare pezzi che già sappiamo che non ci stanno
                        break
                if tempo_impiegato == 0 : 
                    break
                else:
                    orario_corrente += timedelta(seconds=tempo_impiegato)
                    riga["qta_ordine"] = riga["contapezzi"]
                    riga["fine lavorazione"] = orario_corrente
                    riga["data consolidamento"] = orario_corrente.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=31) 
                    riga["media tempo"] = round(tempo_impiegato/riga["contapezzi"],2)
                    riga["tempo impiegato"] = tempo_impiegato
                    riga["CODMACCHINA"] = macchina["CODMACCHINA"]
                    riga["CODREP"] = lista_articoli_possibili_macchina[index]["CODREP"]
                    
            lista_lavorazioni_giornata.append(ordine["righe"])
    return lista_lavorazioni_giornata

def creazione_lista_ordini_per_macchina(macchina, lista_articoli_possibili_full):
    """
    Crea il log di una singola macchina. Params: macchina(riga giusta del csv lista macchine), lista completa degli articoli possibili
    Data Inizio: Data inizio LOG,
    Data Fine: Data fine LOG,
    CodMacchina: Codice della macchina da elaborare,
    Lista Articoli Possibili Macchina: Lista completa delle operazioni attuabili
    """
    try:
        if not bool(macchina["INIZIO LOG"]):
            print_log(f"[red][ERRORE] La macchina {macchina['CODMACCHINA']} non ha la data di inizio elaborazione.\nImpossibile creare il log.[/red]")
            return
        data_inizio = datetime.strptime(macchina["INIZIO LOG"], "%d/%m/%Y")
        # Se data fine non è settata ma data inizio sì, significa che deve elaborare fino ad oggi
        if not bool(macchina["FINE LOG"]):
            data_fine = datetime.today()
        else:
            data_fine =  datetime.strptime(macchina["FINE LOG"], "%d/%m/%Y")
        codmacchina = macchina["CODMACCHINA"]
    except:
        sys.exit(f"[red][ERRORE]: Riscontrato un problema in fase di lettura. CODMACCHINA: {codmacchina}[/red]")

    data_in_elaborazione = data_inizio
    print_log(f"Estrapolazione possibili articoli lavorabili da {codmacchina}.")
    lista_articoli_possibili_macchina = lista_articoli_possibili_full[codmacchina]

    print_log(f"Avvio operazione su LOG per {codmacchina}.")
    # Inizio ciclo Giornate - finichè non ho record per tutti i giorni nel range
    with pro.Progress(pro.SpinnerColumn(style="bold rgb(1,185,255)"),
                    pro.TextColumn("{task.description}",style="bold rgb(1,185,255)",),
                    pro.BarColumn(style="dim rgb(1,185,255)",complete_style="bold rgb(1,185,255)", finished_style="bright_green"),
                    pro.MofNCompleteColumn(),
                    pro.TimeElapsedColumn(),
                    refresh_per_second=60) as progressbar:
        task = progressbar.add_task("In esecuzione...", total=(data_fine-data_inizio).days)
        
        lista_ordini = []
        while(data_in_elaborazione <= data_fine):
            # Identifica orari in base al giorno della settimana
            match data_in_elaborazione.isoweekday():
                # Dom - salta l'elaborazione
                case 7:
                    pass
                # Sab - imposta turni da straordinario
                case 6:
                    if straordinari():
                        mattina_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=6 )
                        mattina_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=13 )
                        orario = [(mattina_inizio, mattina_fine)]
                        # print_log(f"Elaborazione data {data_in_elaborazione.day:02d}/{data_in_elaborazione.month:02d}/{data_in_elaborazione.year}.",rewritable=True)
                        lista_ordini.append(elabora_giornata(orario, lista_articoli_possibili_macchina, macchina))
                # Lun - Ven - imposta orari standard
                case _:
                    mattina_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=8 )
                    mattina_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=12, minute=30 )
                    pomeriggio_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=14 )
                    pomeriggio_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=17, minute=45 )
                    orario = [(mattina_inizio, mattina_fine),(pomeriggio_inizio, pomeriggio_fine)]
                    # print_log(f"Elaborazione data {data_in_elaborazione.day:02d}/{data_in_elaborazione.month:02d}/{data_in_elaborazione.year}.", rewritable=True)
                    lista_ordini.append(elabora_giornata(orario, lista_articoli_possibili_macchina, macchina))


            # Avanzamento ciclo giornate
            data_in_elaborazione += timedelta(days=1)
            progressbar.update(task, advance=1)
        progressbar.update(task, description="[bright_green]Completato!")
    return lista_ordini

def to_desktop(nome:str="test.txt"):
    "Crea il percorso assoluto al Desktop del proprietario e ci aggiunge il nome del file."
    path = os.path.expanduser(f"~\\Desktop\\{nome}")
    return path

def save_var(name_key:str, var):
    with open("test-shelf", flag = 'c', protocol=None, writeback = False) as shelf:
        shelf[name_key] = var
        return

def get_var(name_key):
    with open("test-shelf", flag = 'c', protocol=None, writeback = False) as shelf:
        return shelf[name_key]

# Lettura file in DATA
print_log("Avvio script...")
script_start_time = datetime.now()
print_log("Lettura dei files nella cartella 'data'.")
print_log("Lettura file 'lista macchine.csv'.")
# Lettura "lista macchine.csv"
# try:
# Percorso per la root del progetto. Pyinstaller fa casino altrimenti
global data_path
data_path = Path(f"{root()}/data")
# Pyinstaller fa casino con la versione EXE
try:
    try:
        df_lista_macchine = dt.fread(f"{data_path}/lista macchine.csv").to_pandas()
    except:
        data_path = os.path.join(sys.executable.replace("\miniMoover.exe",""),"data")
        print(data_path)
        df_lista_macchine = dt.fread(os.path.join(data_path,"lista macchine.csv")).to_pandas()
    lista_info_macchine = df_lista_macchine.to_dict("records")
except:
     print(f"[red bold][ERRORE]: File 'lista macchine.csv' non trovato. Uscita forzata del sistema.[/red bold]")
     sys.exit()

# Estrapolazione lista articoli su dict 'lista_articoli_possibili_full'
lista_articoli_possibili_full = {}
for file in os.scandir("data"):
    if ".csv" in file.name and file.name != "lista macchine.csv":    
        tmp_df = dt.fread(f"{data_path}/{file.name}").to_pandas()
        for codmacchina in tmp_df["CODMACCHINA"].unique():
            print_log(f"[bright_green]Articoli per {codmacchina} aggiunti.[/bright_green]")
            lista_articoli_possibili_full[codmacchina] = tmp_df.to_dict("records")

# Controllo file articoli mancanti (presente in lista macchine ma non ha associati articoli)
for index, riga in enumerate(lista_info_macchine):
    codmacchina = riga["CODMACCHINA"]
    if codmacchina not in lista_articoli_possibili_full:
        continuare = "g"
        while(continuare != "S" and continuare != "N"):
            continuare = input(f"[yellow]ATTENZIONE: Nessun articolo trovato per {codmacchina}.\nContinuare con le altre? [S/N] [/yellow]").upper()
        match continuare:
            case "S":
                print_log(f"[yellow]L'elaborazione della macchina {codmacchina} verrà ignorata.[/yellow]")
                lista_info_macchine.pop(index)
            case "N":
                sys.exit(f"[red][ARRESTO] Fermato dall'utente.[/red]")
# TODO Inserire controllo completezza campi su lista_info_macchine
# Tutte le macchine in lista_info_macchine sono processabili
lista_ordini = []
# Senza questa riga le impostazioni di default rischiano di bloccare il ciclo di flat_to_dict()
sys.setrecursionlimit(1600)
for macchina in lista_info_macchine:
    lista_ordini.append(creazione_lista_ordini_per_macchina(macchina, lista_articoli_possibili_full))
# -- Riformattazione
print_log(f"Riformattazione lista ordini raw in righe separate... ")
# Porta la lista in 2D
with pro.Progress(pro.SpinnerColumn(style="bold rgb(1,185,255)"),
                    pro.TextColumn("{task.description}",style="bold rgb(1,185,255)",),
                    pro.BarColumn(pulse_style="dim rgb(1,185,255)",finished_style="bright_green"),
                    pro.TimeElapsedColumn(),
                    refresh_per_second=60) as waitingbar:
    task = waitingbar.add_task("In esecuzione...",total=None)
    lista_ordini = flat_to_dict(lista_ordini)
    waitingbar.update(task, description="[bright_green]Completato!",total=1,completed=1)
# Elimina la righe non lavorate
print_log("Pulizia righe non lavorate...")
tmp_lista_ordini = []
with pro.Progress(pro.SpinnerColumn(style="bold rgb(1,185,255)"),
                    pro.TextColumn("{task.description}",style="bold rgb(1,185,255)",),
                    pro.BarColumn(style="dim rgb(1,185,255)",complete_style="bold rgb(1,185,255)", finished_style="bright_green"),
                    pro.MofNCompleteColumn(),
                    pro.TimeElapsedColumn(),
                    refresh_per_second=60) as progressbar:
    task = progressbar.add_task("In esecuzione...",total=len(lista_ordini))
    for i,item in enumerate(lista_ordini):
        if "fine lavorazione" in item:
            tmp_lista_ordini.append(item)
        progressbar.update(task, advance=1)
    progressbar.update(task, description="[green]Completato![/green]")
lista_ordini = tmp_lista_ordini


tmp_old_len_lista_articoli = len(lista_ordini)
tmp_lista_ordini = []

# -- Riordinamento cronologico 
print_log("Riordinamento delle righe in ordine cronologico...")
df_righe = pd.DataFrame(lista_ordini)
# -- Mischia le righe degli ordini considerando solo l'ordine cronologico
df_righe.sort_values(by="fine lavorazione", inplace=True)
# -- Creazione codici NUMREG definitivi
print_log("Creazione NUMREG condizionati.")
# -- Crea una tabella che fa da legenda per il cambio NUMREG
tmp_list_numreg = df_righe.sort_values('inizio lavorazione').groupby('NUMREG').tail(1)[["NUMREG","fine lavorazione"]].copy(deep=True)
list_new_numreg = []
tmp_dates = pd.DatetimeIndex(tmp_list_numreg["fine lavorazione"].values)
with pro.Progress(pro.SpinnerColumn(style="bold rgb(1,185,255)"),
    pro.TextColumn("{task.description}",style="bold rgb(1,185,255)",),
    pro.BarColumn(style="dim rgb(1,185,255)",complete_style="bold rgb(1,185,255)", finished_style="bright_green"),
    pro.MofNCompleteColumn(),
    pro.TimeElapsedColumn(),
    refresh_per_second=60) as progressbar:
        task = progressbar.add_task("In esecuzione...",total=len(tmp_list_numreg))
        for x in range(0,len(tmp_list_numreg)): # LINK https://www.delftstack.com/howto/python/pad-string-with-zeros-in-python/
            tmp_new_NUMREG = str(tmp_dates.year[x]) + "0" * (12-len(str(tmp_dates.year[x]))-len(str(x+1))) + str(x+1)
            df_righe.loc[df_righe["NUMREG"] == tmp_list_numreg["NUMREG"].values[x], "NUMREG"] = tmp_new_NUMREG
            progressbar.update(task, advance=1)
        progressbar.update(task, description="[green]Completato![/green]")

# -- Processo di output
print_log("Creazione CSV per INSERT...")
lista_righe = df_righe.to_dict(orient="list")
tmp_num_righe = len(lista_righe["NUMREG"])

# BACKUP LISTA IN CASO DI ERRORE IN SEGUITO
print_log("Salvataggio file temporaneo di output per backup.")
save_var("lista_righe", lista_righe)

# Conversione date
print_log("Conversione date formato date.")
tmp_campi_time=["fine lavorazione", "inizio lavorazione", "data consolidamento"]
for x in tmp_campi_time:
    for i,y in enumerate(lista_righe[x]):
        lista_righe[x][i] = y.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")
    print_log(f"Campo '{x}' convertito.")

# Sistemazione Colonne
lista_righe["DITTA"] = [1] * tmp_num_righe
lista_righe["DEPOSITO"] = ["'00"] * tmp_num_righe 
lista_righe["STAZIONE"] = [1] * tmp_num_righe
lista_righe["CODOPERATORE"] = [-1] * tmp_num_righe
lista_righe["VARIANTE"] = [""] * tmp_num_righe
lista_righe["STATOMACCHINA"] = [""] * tmp_num_righe

lista_righe["CODARTICOLO"] = lista_righe.pop("CODART")
lista_righe["CONTAPEZZI"] = lista_righe.pop("contapezzi")
lista_righe["TEMPOPEZZO"] = lista_righe.pop("media tempo")
lista_righe["TEMPO"] = lista_righe.pop("tempo impiegato")
lista_righe["CODREPARTO"] = lista_righe.pop("CODREP")
lista_righe["DATACONSOLIDAMENTO"] = lista_righe.pop("data consolidamento")
lista_righe["QTAORDINE"] = lista_righe.pop("qta_ordine")
lista_righe["STARTDATE"] = lista_righe.pop("inizio lavorazione")
lista_righe["ENDDATE"] = lista_righe.pop("fine lavorazione")
lista_righe["CODFASE"] = lista_righe["CODARTICOLO"]

# Ordinamento colonne
lista_righe = OrderedDict((k, lista_righe[k]) for k in campi_insert)
a = dt.Frame(lista_righe)

# Salvataggio
while True:
    try:
        a.to_csv(to_desktop("output.csv"))
        break
    except:
        scelta = "T"
        while scelta not in ["N","S"]:
            print_warning("Impossibile scrivere su file 'output.csv' perché aperto su un altro processo. Chiudere il file e proseguire.")
            scelta = input("Procedere?[S/N] ").upper()
            if scelta not in ["N","S"]:
                print("Scelta non valida. Riprovare.")
        if scelta == "S" : continue
        elif scelta == "N" : sys.exit("Chiusura programma su comando dell'utente.")
print_log(f"[bright_green]Creato file 'output.csv' su Desktop.[/bright_green]")
print_log(f"[bright_green]{tmp_num_righe} righe processate in {datetime.now()-script_start_time}.[/bright_green]")
try:
    os.system("pause")
except:
    input("Premere Enter per terminare...")
    