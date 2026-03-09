
# =============================================================================
#                            CÓDIGO DEFINITIVO
# =============================================================================

from PyQt6.QtWidgets import QFileDialog, QApplication
import sys
from obspy import read, Stream
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from obspy import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

# 1. Pedimos los 3 archivos Guralp (CMG)
print("\nAbriendo explorador... Seleccione los 3 ficheros (Z, N, E) Guralp (CMG).")
rutas_cmg, _ = QFileDialog.getOpenFileNames(None, "Seleccione los 3 ficheros Guralp (CMG)", "", "Archivos MiniSEED (*.mseed);;Todos los ficheros (*)")

# 2. Pedimos los 3 archivos Silex
print("\nAbriendo explorador... Seleccione los 3 ficheros (Z, N, E) del Silex.")
rutas_silex, _ = QFileDialog.getOpenFileNames(None, "Seleccione los 3 ficheros Silex", "", "Archivos MiniSEED (*.mseed);;Todos los ficheros (*)")

# 3. Verificamos que no hayan cancelado
if not rutas_cmg or not rutas_silex:
    print("Error: No se seleccionaron todos los ficheros necesarios. Ejecute el script nuevamente.")
    sys.exit()

print("Cargando ficheros, por favor espere...")

# 4. Juntamos las 3 componentes
st_cmg = Stream()
for ruta in rutas_cmg:
    st_cmg += read(ruta)

st_silex = Stream()
for ruta in rutas_silex:
    st_silex += read(ruta)

print("Ficheros cargados correctamente. Procesando...")


# =============================================================================
#                    ARREGLOS PREVIOS (MERGE, RESAMPLE Y ORIENTACIÓN)

# 1. Unimos los pedacitos (chunks) del Silex para que no se corte la señal
st_silex.merge(method=1, fill_value="interpolate")

# 2. Igualamos el muestreo del Guralp a 100 Hz
#st_cmg.resample(100)

# 3. Corrección FIJA del Guralp: Invertimos Z y E 
for tr in st_cmg:
    if tr.stats.channel.endswith("Z") or tr.stats.channel.endswith("E"):
        tr.data = -1 * tr.data

# 4. Corrección DINÁMICA del Silex: Preguntamos al usuario por consola
print("\n")
orientacion_silex = input("Indique la orientación del sensor Silex en la mesa vibrante (N/S): ").strip().upper()

if orientacion_silex == "S":
    print("Aplicando inversión de polaridad al Silex (Orientación Sur)...")
    for tr in st_silex:
        if tr.stats.channel.endswith("Z") or tr.stats.channel.endswith("N"):
            tr.data = -1 * tr.data
elif orientacion_silex == "N":
    print("Aplicando inversión de polaridad al Silex (Orientación Norte)...")
    for tr in st_silex:
        if tr.stats.channel.endswith("Z") or tr.stats.channel.endswith("E"):
            tr.data = -1 * tr.data
else:
    print("Advertencia: Entrada no reconocida. No se aplicarán cambios de polaridad en el Silex.")


# =============================================================================
#                        PLOTEAMOS LA SEÑAL COMPLETA:

# 1. Quitamos el offset (demean) para que ambos arranquen centrados en el cero
for tr in st_cmg:
    tr.detrend("demean")
for tr in st_silex:
    tr.detrend("demean")

# 2. Aplicamos el factor de conversión al Guralp (CMG)
factor = 2e-4
for tr in st_cmg:
    tr.data = tr.data * factor


# SUAVIZADO (TAPER) Y FILTRO PASA BANDA (BANDPASS)
print("Aplicando suavizado de bordes y filtro pasa banda (1-25 Hz)...")

# Aplicamos un suavizado (taper) con un tope máximo de 5 segundos
st_cmg.taper(max_percentage=0.1, type='hamming', max_length=5.0)
st_silex.taper(max_percentage=0.1, type='hamming', max_length=5.0)

# filtro pasa banda para limpiar frecuencias muy lentas y muy rapidas
frec_min = 1
frec_max = 25.0 
st_cmg.filter("bandpass", freqmin=frec_min, freqmax=frec_max, corners=4, zerophase=True)
st_silex.filter("bandpass", freqmin=frec_min, freqmax=frec_max, corners=4, zerophase=True)

# -----------------------------------------------------------------------------

# 3. Preparamos el lienzo 3x2
fig, ax = plt.subplots(3, 2, figsize=(14, 8), sharex='col') # sharex='col' une el tiempo de cada columna
fig.canvas.manager.set_window_title('Vista Previa Completa - Guralp vs Silex')
formato_hora = mdates.DateFormatter('%H:%M:%S')

componentes = ["Z", "N", "E"]
for i, comp in enumerate(componentes):
    # Buscamos la traza exacta (Z, N o E) en cada sensor
    tr_c = st_cmg.select(component=comp)[0]
    tr_s = st_silex.select(component=comp)[0]

    # --- columna izquierda: GURALP ---
    ax[i, 0].plot(tr_c.times("matplotlib"), tr_c.data, color='blue', lw=0.6)
    ax[i, 0].set_title(f"Guralp (CMG) - Componente {comp}")
    ax[i, 0].set_ylabel("Aceleración (mg)")
    ax[i, 0].grid(True)
    ax[i, 0].xaxis.set_major_formatter(formato_hora)

    # --- columna derecha: SILEX ---
    ax[i, 1].plot(tr_s.times("matplotlib"), tr_s.data, color='black', lw=0.6)
    ax[i, 1].set_title(f"Silex - Componente {comp}")
    ax[i, 1].grid(True)
    ax[i, 1].xaxis.set_major_formatter(formato_hora)

    # le ponemos "Hora (UTC)" a los graficos de abajo del todo
    if i == 2:
        ax[i, 0].set_xlabel("Hora (UTC)")
        ax[i, 1].set_xlabel("Hora (UTC)")

fig.autofmt_xdate() # inclina las horas
plt.tight_layout()

print("\nMostrando gráfica completa. Cierre la ventana cuando haya identificado la hora del evento a analizar.")
plt.show(block=True) 

# =============================================================================
#          DETECCIÓN Y ALINEACIÓN (PIDIENDO HORAS POR CONSOLA)

# función STA/LTA local
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

print("\n" + "="*60)
print("-> Vista previa finalizada. Iniciando proceso de sincronización.")
print("\nIntroduzca la hora aproximada del evento a aislar (Formato HH:MM:SS)")

# Pedimos la hora al usuario
hora_str_cmg = input("-> Hora en el Guralp (CMG): ")
hora_str_silex = input("-> Hora en el Silex: ")

# sacamos la fecha del propio archivo y le pegamos la hora del usuario
fecha_cmg = str(st_cmg[0].stats.starttime.date)
fecha_silex = str(st_silex[0].stats.starttime.date)

hora_aprox_cmg = UTCDateTime(f"{fecha_cmg}T{hora_str_cmg}")
hora_aprox_silex = UTCDateTime(f"{fecha_silex}T{hora_str_silex}")

# detecta el milisegundo exacto en la componente Z
print("\nCalculando el tiempo exacto de inicio mediante STA/LTA. Por favor, espere...")
ventana_busqueda = 60
t_evento_c = detectar_evento_local(st_cmg.select(component="Z")[0], hora_aprox_cmg, ventana_busqueda)
t_evento_s = detectar_evento_local(st_silex.select(component="Z")[0], hora_aprox_silex, ventana_busqueda)

if not t_evento_c or not t_evento_s:
    print("Error: No se detectó un evento claro en la ventana de tiempo especificada. Verifique las horas ingresadas.")
    sys.exit()

print(f"Evento detectado en CMG: {t_evento_c} | Silex: {t_evento_s}")


# =============================================================================
#                 MENÚ INTERACTIVO: RECORTE Y PLOTEO SINCRONIZADO

print("\n" + "="*60)
print("Sincronización completada. Iniciando módulo de visualización.")

while True:
    print("\n-> Seleccione una opción de visualización:")
    print("  a) Evento completo")
    print("  b) Primeros 1.5 segundos (-0.5s  +1.5s)")
    print("  c) Primeros 5 segundos (-0.5s  +5.0s)")
    print("  d) Cerrar programa")
    
    opcion = input("\nIntroduzca su elección (a/b/c/d): ").strip().lower()

    if opcion == 'd':
        print("\nPrograma finalizado.")
        break
    elif opcion == 'a':
        duracion_antes = 3.0
        duracion_despues = 34.0
        titulo_ventana = "Señal Completa"
    elif opcion == 'b':
        duracion_antes = 0.5
        duracion_despues = 1.5
        titulo_ventana = "Primeros 1.5 segundos"
    elif opcion == 'c':
        duracion_antes = 0.5
        duracion_despues = 5.0
        titulo_ventana = "Primeros 5 segundos"
    else:
        print("Error: Opción no reconocida. Por favor, introduzca 'a', 'b', 'c' o 'd'.")
        continue

    print(f"Generando gráfica: {titulo_ventana}. (Cierre la ventana para volver al menú)")

    # hacemos una copia de los datos porque trim() se los carga
    st_cmg_event = st_cmg.copy()
    st_silex_event = st_silex.copy()

    # recortamos exactamente alrededor del trigger calculado según la opción elegida
    st_cmg_event.trim(t_evento_c - duracion_antes, t_evento_c + duracion_despues)
    st_silex_event.trim(t_evento_s - duracion_antes, t_evento_s + duracion_despues)

    # preparamos el lienzo final (2 filas x 3 columnas)
    fig2, ax2 = plt.subplots(2, 3, figsize=(14, 6), sharex='col')
    fig2.canvas.manager.set_window_title(f'Comparación Sincronizada - {titulo_ventana}')

    for j, comp in enumerate(componentes):
        tr_c = st_cmg_event.select(component=comp)[0]
        tr_s = st_silex_event.select(component=comp)[0]

        # Convertimos el eje X a tiempo relativo
        t_rel_c = tr_c.times() - duracion_antes
        t_rel_s = tr_s.times() - duracion_antes

        # Sacamos el valor máximo absoluto de la traza del Guralp para el límite Y
        max_val_guralp = max(abs(tr_c.data.min()), abs(tr_c.data.max()))
        limite_y = int(max_val_guralp * 1.05) + 1

        # Guralp (Fila Superior: índice 0)
        ax2[0, j].plot(t_rel_c, tr_c.data, color='blue', lw=0.8)
        ax2[0, j].set_title(f"Guralp (CMG) - Componente {comp}")
        ax2[0, j].set_ylabel("Aceleración (mg)")
        ax2[0, j].set_ylim(-limite_y, limite_y) 
        ax2[0, j].grid(True)

        # Silex (Fila Inferior: índice 1)
        ax2[1, j].plot(t_rel_s, tr_s.data, color='black', lw=0.8)
        ax2[1, j].set_title(f"Silex - Componente {comp}")
        ax2[1, j].set_ylabel("Aceleración (mg)")
        ax2[1, j].set_ylim(-limite_y, limite_y) 
        ax2[1, j].grid(True)

        # etiquetas de max y min solo para la señal completa
        if opcion == 'a':
            max_c = tr_c.data.max()
            min_c = tr_c.data.min()
            max_s = tr_s.data.max()
            min_s = tr_s.data.min()
            
            # Calculamos el porcentaje (evitando división por cero por si acaso)
            porc_max = (max_s / max_c * 100) if max_c != 0 else 0
            porc_min = (min_s / min_c * 100) if min_c != 0 else 0

            # textos para el Guralp
            texto_c = f"Max: {max_c:.2f} mg\nMin: {min_c:.2f} mg"
            ax2[0, j].text(0.95, 0.95, texto_c, transform=ax2[0, j].transAxes,
                           fontsize=9, verticalalignment='top', horizontalalignment='right',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # textos para el Silex (incluyendo el porcentaje de similitud)
            texto_s = f"Max: {max_s:.2f} mg ({porc_max:.1f}%)\nMin: {min_s:.2f} mg ({porc_min:.1f}%)"
            ax2[1, j].text(0.95, 0.95, texto_s, transform=ax2[1, j].transAxes,
                           fontsize=9, verticalalignment='top', horizontalalignment='right',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Etiqueta X solo en la fila de abajo
        ax2[1, j].set_xlabel("Tiempo desde el inicio (s)")

    plt.tight_layout()
    plt.show(block=True)



