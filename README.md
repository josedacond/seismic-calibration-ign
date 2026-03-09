# 🌍 Seismic Sensor Calibration Tool — IGN

**Prácticas Académicas Externas — Ingeniería Electrónica de Comunicaciones · UCM**  
**Autor:** José David Conde Quispe  
**Entidad:** Instituto Geográfico Nacional (IGN) — Red Sísmica Nacional  

---

## 📌 Descripción

Herramienta de calibración y comparación de sismógrafos desarrollada 
para la Red Sísmica Nacional del IGN. Permite cargar, procesar, 
sincronizar y comparar visualmente las señales sísmicas de dos sensores 
instalados en una mesa vibrante: el sensor patrón **Guralp CMG** y el 
sensor a prueba **Silex**, automatizando un proceso de análisis que 
anteriormente tardaba horas en completarse.

---

## ⚙️ Pipeline del sistema
```
[Archivos MiniSEED] → [GUI PyQt6] → [Preprocesado] → [Filtrado] 
        → [Detección STA/LTA] → [Sincronización] → [Visualización]
```

---

## 🔬 Procesamiento de señal

| Paso | Técnica | Descripción |
|------|---------|-------------|
| 1 | **Merge** | Une fragmentos discontinuos del Silex |
| 2 | **Demean** | Elimina offset DC de ambas señales |
| 3 | **Corrección de orientación** | Inversión de ejes Z/E del Guralp (fija) y Z/N o Z/E del Silex (dinámica según posición N/S) |
| 4 | **Factor de conversión** | Aplica factor 2e-4 al Guralp para convertir a mg |
| 5 | **Taper Hamming** | Suavizado de bordes (máx. 5s) para evitar artefactos |
| 6 | **Filtro pasa banda** | 1–25 Hz, fase cero, orden 4 |
| 7 | **STA/LTA** | Detección automática del inicio del evento sísmico |
| 8 | **Correlación cruzada** | Alineación temporal milimétrica entre sensores |

---

## 🖥️ Funcionalidades

- Interfaz gráfica **PyQt6** para selección de archivos MiniSEED (Z, N, E)
- Corrección dinámica de orientación del Silex según posición en mesa
- Vista previa de la señal completa con hora UTC
- Detección automática del evento con **STA/LTA** a partir de hora aproximada
- Menú interactivo con 3 vistas de análisis:
  - Evento completo
  - Primeros 1.5 segundos
  - Primeros 5 segundos
- Comparación cuantitativa: valores máx/mín y **porcentaje de similitud** del Silex respecto al Guralp

---

## 📁 Estructura del repositorio
```
seismic-calibration-ign/
├── 1_sta_lta_exploracion.py    # Exploración inicial del algoritmo STA/LTA
├── 2_calibrador_sismografos.py # Herramienta completa y definitiva
└── requirements.txt
```

---

## ⚙️ Instalación
```bash
pip install obspy matplotlib PyQt6
```

---

## 🛠️ Uso
```bash
python 2_calibrador_sismografos.py
```

1. Selecciona los 3 ficheros MiniSEED del Guralp (Z, N, E)
2. Selecciona los 3 ficheros MiniSEED del Silex (Z, N, E)
3. Indica la orientación del Silex (N/S)
4. Identifica visualmente la hora del evento en la gráfica completa
5. Introduce la hora aproximada para cada sensor
6. Selecciona la vista de análisis deseada

---

## 📊 Resultado

Reducción del tiempo de análisis de **horas a pocos minutos**, 
con comparación cuantitativa automática de amplitudes entre sensores.
