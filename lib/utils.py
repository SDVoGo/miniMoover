from datetime import datetime
from pathlib import Path
from random import choices, randrange
import numpy as np
from rich import print

def print_warning(msg:str):
    print(f"[bright_red]ATTENZIONE: [/bright_red]{msg}")

def get_project_root() -> Path:
    return Path(__file__).parent.parent

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

def print_log(messaggio:str, rewritable:bool=False):
    sys_log_orario = datetime.now()
    msg = f"[[white]{sys_log_orario.hour:02d}:{sys_log_orario.minute:02d}:{sys_log_orario.second:02d}[/white]]: {messaggio}"
    print(msg)

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
            item = np.random.normal(mean, sigma)
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