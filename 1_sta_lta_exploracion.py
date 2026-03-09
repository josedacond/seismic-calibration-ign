#%%

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from obspy import read, UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset

plt.close("all")

st_silex = read("204*")
st_cmg   = read("Cmg5t*")

st_silex.merge(method=1, fill_value="interpolate")
st_cmg.resample(100)

# ========== QUITAMOS EL OFFSET Y CENTRAMOS EN 0 ===========
for tr in st_silex:
    tr.detrend("demean")

for tr in st_cmg:
    tr.detrend("demean")
    
# ========== MULTIPLICAR POR FACTOR DE CONVERSIÓN =============
factor = 2e-4
for tr in st_cmg:
    tr.data = tr.data * factor

# =============== ORIENTACIÓN SILEX (invertir Z y E) =======
for tr in st_silex:
    if tr.stats.channel.endswith("Z") or tr.stats.channel.endswith("E"):
        tr.data = -1 * tr.data
        
# =============== ORIENTACIÓN Guralp (invertir Z y E) =======
for tr in st_silex:
    if tr.stats.channel.endswith("Z") or tr.stats.channel.endswith("E"):
        tr.data = -1 * tr.data
        
        

# ========== FIGURA 1: PLOTEAMOS LA SEÑAL ENTERA ==============

formato = mdates.DateFormatter('%H:%M:%S')
fig1, ax1 = plt.subplots(2, 3, figsize=(14,6), sharex=True)
components = ["Z", "N", "E"]

for j, comp in enumerate(components):

    tr_c = st_cmg.select(component=comp)[0]
    ax1[0, j].plot(tr_c.times("matplotlib"), tr_c.data, lw=0.8)
    ax1[0, j].set_title(f"CMG - {comp}")
    ax1[0, j].set_ylabel("Aceleración (mg)")
    ax1[0, j].grid(True)

    tr_s = st_silex.select(component=comp)[0]
    ax1[1, j].plot(tr_s.times("matplotlib"), tr_s.data, lw=0.8)
    ax1[1, j].set_title(f"Silex - {comp}")
    ax1[1, j].set_ylabel("Aceleración (mg)")
    ax1[1, j].grid(True)

for j in range(3):
    ax1[1, j].xaxis.set_major_formatter(formato)
    ax1[1, j].set_xlabel("Hora (UTC)")

fig1.autofmt_xdate()
plt.tight_layout()
plt.show()



# ========== INTRODUCIMOS LA HORA APROXIMADA DE BUSQUEDA ===========
hora_aprox_silex = UTCDateTime("2025-06-03T10:01:00")
hora_aprox_cmg   = UTCDateTime("2025-06-03T09:57:20")

ventana_busqueda = 60  # segundos alrededor

# DETECCIÓN STA/LTA LOCAL
def detectar_evento_local(tr, t_aprox, ventana):
    fs = tr.stats.sampling_rate
    tr_local = tr.copy()
    tr_local.trim(t_aprox - ventana, t_aprox + ventana)

    nsta = int(0.2 * fs)
    nlta = int(5 * fs)

    cft = classic_sta_lta(tr_local.data, nsta, nlta)
    on_off = trigger_onset(cft, 3.5, 1.0)

    if len(on_off) == 0:
        return None

    primer_trigger = on_off[0][0]

    tiempo_evento = tr_local.stats.starttime + primer_trigger / fs
    return tiempo_evento

# Detectar en Z
t_evento_s = detectar_evento_local(
    st_silex.select(component="Z")[0],
    hora_aprox_silex,
    ventana_busqueda
)

t_evento_c = detectar_evento_local(
    st_cmg.select(component="Z")[0],
    hora_aprox_cmg,
    ventana_busqueda
)

print("Evento detectado Silex:", t_evento_s)
print("Evento detectado CMG:", t_evento_c)


# =============================================================================
# FIGURA 2 → EVENTO ALINEADO (2x3)
# =============================================================================
duracion = 55

st_silex_event = st_silex.copy()
st_cmg_event   = st_cmg.copy()

st_silex_event.trim(t_evento_s - 5, t_evento_s + 50)
st_cmg_event.trim(t_evento_c - 5, t_evento_c + 50)

fig2, ax2 = plt.subplots(2, 3, figsize=(14,6), sharex=True)

for j, comp in enumerate(components):

    # Tiempo relativo
    tr_c = st_cmg_event.select(component=comp)[0]
    tr_s = st_silex_event.select(component=comp)[0]

    t_rel_c = tr_c.times() - 5
    t_rel_s = tr_s.times() - 5

    ax2[0, j].plot(t_rel_c, tr_c.data, lw=0.8)
    ax2[0, j].set_title(f"CMG - {comp}")
    ax2[0, j].set_ylabel("Aceleración (mg)")
    ax2[0, j].grid(True)

    ax2[1, j].plot(t_rel_s, tr_s.data, lw=0.8)
    ax2[1, j].set_title(f"Silex - {comp}")
    ax2[1, j].set_ylabel("Aceleración (mg)")
    ax2[1, j].grid(True)

for j in range(3):
    ax2[1, j].set_xlabel("Duración Terremoto (s)")

plt.tight_layout()
plt.show()

