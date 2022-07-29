from collections import OrderedDict
from datetime import datetime, timedelta
from random import choices, randrange
import sys
import pandas as pd
import numpy as np
import os
from colorama import init, Fore, Back, Style
from uuid import uuid4
import datatable as dt
from shelve import open

campi_insert = ["DITTA","DEPOSITO","CODMACCHINA","STAZIONE","NUMREG","PROGRIGA","CODARTICOLO","VARIANTE","STARTDATE","ENDDATE","QTAORDINE","TEMPO","TEMPOPEZZO","CONTAPEZZI","CODFASE","CODREPARTO","CODOPERATORE","STATOMACCHINA","DATACONSOLIDAMENTO"]

def save_var(name_key:str, var):
    with open("test-shelf", flag = 'c', protocol=None, writeback = False) as shelf:
        shelf[name_key] = var
        print("Salvato.")
        return

def flat_to_dict(lst:list):
    """
    Crea una lista 2D da una multilivello.
    input lst:lista
    """
    if lst == []:
        return lst
    if isinstance(lst[0], list):
        return flat_to_dict(lst[0]) + flat_to_dict(lst[1:])
    return lst[:1] + flat_to_dict(lst[1:])

def get_righe(lst):
    return lst["righe"]


def print_log(messaggio:str,end="\n", rewritable:bool=False, clear:bool=True):
    """
    Variante custom basata sulla funzione built-in 'print'. 
    (messaggio:str, end="\n", rewritable:bool=False,clear:bool=True) => str '[HH:MM:SS]: messaggio {end}'
    """
    sys_log_orario = datetime.now()
    msg = f"[{sys_log_orario.hour:02d}:{sys_log_orario.minute:02d}:{sys_log_orario.second:02d}]: {messaggio}"
    CLEAN_LINE = "                                                           "
    if clear : print(CLEAN_LINE,end="\r")
    if rewritable:
        print(msg, end="\r")
        return
    elif not rewritable and bool(end):
        print(msg, end=end)

# Se la deviazione rilascia valori negativi. Perchè non pulirli dall'interno?
def distribuzione_normale(mean, sigma, num_valori_richiesti:int=1):
    """
    Calcola la distribuzione normale per creare rumore nei dati mantendo la verosomiglianza.
    ATTENZIONE: viene effettuato un round interno e risoluzione problema numero negativo.
    """
    s = np.random.normal(mean, sigma, num_valori_richiesti)
    res = []
    for item in s:
        while round(item) <= 0:
            item = np.random.normal(mean, sigma,)
        res.append(round(item))
    #if len(res) == 1: return res[0]
    return res

def random_sec(data_in_stringa):
    """
    Randomizza i secondi, pensata per la data di consolidamento
    """
    temp_sec = str(randrange(0,60))
    if len(temp_sec) == 1:
        temp_sec = "0" + temp_sec
    return f"{data_in_stringa}:{temp_sec}"

def straordinari():
    """
    Sceglie se questo straordinario s'ha da fare.
    """
    return choices(population=[True, False], weights=(1,3), k=1)[0]

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
                # TODO Controllare funzionalità condizione
                while index_articolo in tmp_lista_index_articoli and np.isnan(lista_articoli_possibili_macchina[index_articolo]["CODARTOLD"]):
                #TODO ripristinare la condizione sotto
                #or datetime.strptime(lista_articoli_possibili_macchina[index_articolo]["DTINILOG"], "%d/%m/%Y") > orario_corrente:
                    index_articolo = randrange(0, len(lista_articoli_possibili_macchina))
                tmp_lista_index_articoli.append(index_articolo)
                ordine["righe"].append({"NUMREG":ordine["NUMREG_PROV"],"PROGRIGA":x+1, "index articolo":index_articolo, "CODART":lista_articoli_possibili_macchina[index_articolo]["CODART"] if np.isnan(lista_articoli_possibili_macchina[index_articolo]["CODARTOLD"]) else lista_articoli_possibili_macchina[index_articolo]["CODARTOLD"]})
                tmp_articolo_selezionato = lista_articoli_possibili_macchina[index]
                # Andamento produzione:
                # TODO Aggiungere casi di modalità produzione in un secondo momento [sotto, normale, sovra]
                # NOTE Attenzione: per semplificare il programma la feature qta_ordine != contapezzi non è stata implementata
                ordine["righe"][x]["qta_ordine"] = distribuzione_normale(tmp_articolo_selezionato["MEAN_QTALAV"],tmp_articolo_selezionato["DEVSTD_QTALAV"])[0]
                ordine["righe"][x]["tempo_ciclo"] = distribuzione_normale(tmp_articolo_selezionato["MEAN_QTALAV"],tmp_articolo_selezionato["DEVSTD_QTALAV"], ordine["righe"][x]["qta_ordine"])
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
            print_log(f"{Fore.RED}[ERRORE] La macchina {macchina['CODMACCHINA']} non ha la data di inizio elaborazione.\nImpossibile creare il log.{Style.RESET_ALL}")
            return
        data_inizio = datetime.strptime(macchina["INIZIO LOG"], "%d/%m/%Y")
        # Se data fine non è settata ma data inizio sì, significa che deve elaborare fino ad oggi
        if bool(macchina["FINE LOG"]):
            data_fine = datetime.today()
        else:
            data_fine =  datetime.strptime(macchina["FINE LOG"], "%d/%m/%Y")
        codmacchina = macchina["CODMACCHINA"]
    except:
        sys.exit(f"{Fore.RED}[ERRORE]: Riscontrato un problema in fase di lettura. CODMACCHINA: {codmacchina}{Style.RESET_ALL}")

    data_in_elaborazione = data_inizio
    print_log(f"Estrapolazione possibili articoli lavorabili da {codmacchina}.")
    lista_articoli_possibili_macchina = lista_articoli_possibili_full[codmacchina]

    print_log(f"Avvio operazione su LOG per {codmacchina}.")
    # Inizio ciclo Giornate - finichè non ho record per tutti i giorni nel range
    lista_ordini = []
    while(data_in_elaborazione <= data_fine):
        # Identifica orari in base al giorno della settimana
        match data_in_elaborazione.isoweekday():
            # Dom - salta l'elaborazione
            case 7:
                pass
            # Sab - imposta turni da straordinario
            case 6:
                mattina_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=6 )
                mattina_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=13 )
                orario = [(mattina_inizio, mattina_fine)]
                print_log(f"Elaborazione data {data_in_elaborazione.day:02d}/{data_in_elaborazione.month:02d}/{data_in_elaborazione.year}.",rewritable=True, clear=False)
                lista_ordini.append(elabora_giornata(orario, lista_articoli_possibili_macchina, macchina))
            # Lun - Ven - imposta orari standard
            case _:
                mattina_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=8 )
                mattina_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=12, minute=30 )
                pomeriggio_inizio = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=14 )
                pomeriggio_fine = datetime(day=data_in_elaborazione.day, month=data_in_elaborazione.month, year=data_in_elaborazione.year, hour=17, minute=45 )
                orario = [(mattina_inizio, mattina_fine),(pomeriggio_inizio, pomeriggio_fine)]
                print_log(f"Elaborazione data {data_in_elaborazione.day:02d}/{data_in_elaborazione.month:02d}/{data_in_elaborazione.year}.", rewritable=True, clear=False)
                lista_ordini.append(elabora_giornata(orario, lista_articoli_possibili_macchina, macchina))
        

        # Avanzamento ciclo giornate
        data_in_elaborazione += timedelta(days=1)
    print_log(f"{Back.GREEN} COMPLETATO {Style.RESET_ALL}")
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


# Inizializzazione colori
init()
# Lettura file in DATA
print_log("Avvio script...")
script_start_time = datetime.now()
print_log("Lettura dei files nella cartella 'data'.")
print_log("Lettura file 'lista macchine.csv'.")
# Lettura "lista macchine.csv"
try:
    df_lista_macchine = pd.read_csv("data/lista macchine.csv")
    lista_info_macchine = df_lista_macchine.to_dict("records")
except:
    sys.exit(f"{Fore.RED}[ERRORE]: File 'lista macchine.csv' non trovato. Uscita forzata del sistema.{Style.RESET_ALL}")

# Estrapolazione lista articoli su dict 'lista_articoli_possibili_full'
lista_articoli_possibili_full = {}
for file in os.scandir("data"):
    if ".csv" in file.name and file.name != "lista macchine.csv":
        tmp_df = pd.read_csv(f"data/{file.name}")
        for codmacchina in tmp_df["CODMACCHINA"].unique():
            print_log(f"{Back.GREEN} Articoli per {codmacchina} aggiunti. {Style.RESET_ALL}")
            lista_articoli_possibili_full[codmacchina] = tmp_df.to_dict("records")

# Controllo file articoli mancanti (presente in lista macchine ma non ha associati articoli)
for index, riga in enumerate(lista_info_macchine):
    codmacchina = riga["CODMACCHINA"]
    if codmacchina not in lista_articoli_possibili_full:
        continuare = "g"
        while(continuare != "S" and continuare != "N"):
            continuare = input(f"{Back.YELLOW}ATTENZIONE: Nessun articolo trovato per {codmacchina}.\nContinuare con le altre? [S/N] {Style.RESET_ALL}").upper()
        match continuare:
            case "S":
                print_log(f"{Back.YELLOW}L'elaborazione della macchina {codmacchina} verrà ignorata.{Style.RESET_ALL}")
                lista_info_macchine.pop(index)
            case "N":
                sys.exit(f"{Fore.RED}[ARRESTO] Fermato dall'utente.{Style.RESET_ALL}")
# TODO Inserire controllo completezza campi su lista_info_macchine
# Tutte le macchine in lista_info_macchine sono processabili
output, lista_ordini = [],[]
# Senza questa riga le impostazioni di default rischiano di bloccare il ciclo di flat_to_dict()
sys.setrecursionlimit(1600)
for macchina in lista_info_macchine:
    lista_ordini.append(creazione_lista_ordini_per_macchina(macchina, lista_articoli_possibili_full))
# -- Riformattazione
print_log(f"Riformattazione lista ordini raw in righe separate... ")
# Porta la lista in 2D
lista_ordini = flat_to_dict(lista_ordini)
# Elimina la righe non lavorate
tmp_lista_ordini = []
for i,item in enumerate(lista_ordini):
    if "fine lavorazione" in item:
        tmp_lista_ordini.append(item)
    print_log(f"{i+1}/{len(lista_ordini)} righe processate.",rewritable=True)
lista_ordini = tmp_lista_ordini
print_log(f"{Back.GREEN} COMPLETATO {Style.RESET_ALL}")

tmp_old_len_lista_articoli = len(lista_ordini)
tmp_lista_ordini = []

# TODO Lavori in corso
# -- Riordinamento cronologico 
print_log("Riordinamento delle righe in ordine cronologico...")
df_righe = pd.DataFrame(lista_ordini)
# -- Mischia le righe degli ordini considerando solo l'ordine cronologico
df_righe.sort_values(by="fine lavorazione", inplace=True)
print_log(f"{Back.GREEN} COMPLETATO {Style.RESET_ALL}")
# -- Creazione codici NUMREG definitivi
print_log("Creazione NUMREG condizionati.")
print_log("Attendere...", rewritable=True)
# -- Crea una tabella che fa da legenda per il cambio NUMREG
tmp_list_numreg = df_righe.sort_values('inizio lavorazione').groupby('NUMREG').tail(1)[["NUMREG","fine lavorazione"]].copy(deep=True)
list_new_numreg = []
tmp_dates = pd.DatetimeIndex(tmp_list_numreg["fine lavorazione"].values)
for x in range(0,len(tmp_list_numreg)): # LINK https://www.delftstack.com/howto/python/pad-string-with-zeros-in-python/
    tmp_new_NUMREG = str(tmp_dates.year[x])
    tmp_new_NUMREG = tmp_new_NUMREG.ljust(16-(len(str(x))+len(tmp_new_NUMREG)),"0")
    tmp_new_NUMREG += str(x+1)
    #list_new_numreg.append({"old NUMREG": tmp_list_numreg["NUMREG"].values[x], "new NUMREG":tmp_new_NUMREG})
    df_righe.loc[df_righe["NUMREG"] == tmp_list_numreg["NUMREG"].values[x], "NUMREG"] = tmp_new_NUMREG
    print_log(f"NUMREG creati e applicati: {x+1}/{len(tmp_list_numreg)}.",rewritable=True)
print_log(f"{Back.GREEN} COMPLETATO {Style.RESET_ALL}")

# -- Processo di output
print_log("Creazione CSV per INSERT...")
print_log("Attendere...", rewritable=True)
lista_righe = df_righe.to_dict(orient="list")
tmp_num_righe = len(lista_righe["NUMREG"])

# BACKUP LISTA IN CASO DI ERRORE IN SEGUITO
print_log(" |__ Salvataggio per backup come disaster recovery.")
save_var("lista_righe", lista_righe)

# Conversione date
print_log(" |__ Cambio nomi colonne e conversione date.")
tmp_campi_time=["fine lavorazione", "inizio lavorazione", "data consolidamento"]
for x in tmp_campi_time:
    for i,y in enumerate(lista_righe[x]):
        lista_righe[x][i] = y.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")
    print_log(f"   |__ Campo '{x}' convertito.")

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
a.to_csv(to_desktop("output.csv"))
print_log(f"{Fore.GREEN}Creato file 'output.csv' su Desktop.{Style.RESET_ALL}")
print_log(f"{Fore.GREEN}{tmp_num_righe} righe processate in {datetime.now()-script_start_time}.{Style.RESET_ALL}")