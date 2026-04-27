import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="Navegación Rubiales", layout="wide")

# --- FUNCIONES DE SOPORTE (Caché y Conversión) ---
def dms_to_decimal(dms_str):
    try:
        if pd.isna(dms_str) or str(dms_str).strip() == "": return None
        parts = re.findall(r"[-+]?\d*\.\d+|\d+", str(dms_str))
        if len(parts) < 3: return None
        deg, minu, sec = map(float, parts)
        decimal = deg + (minu / 60) + (sec / 3600)
        if any(char in str(dms_str).upper() for char in ['S', 'W', 'O']):
            decimal *= -1
        return decimal
    except:
        return None

@st.cache_data
def cargar_base_coordenadas(file_path):
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    # Agrupamos por clúster para tener puntos únicos de destino
    df_geo = df.groupby('Clúster').agg({
        'lat_dec': 'first',
        'lon_dec': 'first',
        'POZO': lambda x: ', '.join(x.astype(str))
    }).reset_index()
    return df_geo

# --- INTERFAZ DE USUARIO ---
st.title("🚚 Planificador de Rutas - Rubiales & Caño Sur")

try:
    # 1. Cargar la base maestra (Lo que ya hicimos)
    df_maestro = cargar_base_coordenadas("Coordenadas Rubiales.xlsx")

    # 2. SECCIÓN PARA PEGAR LA RUTA
    st.sidebar.header("Configuración de Ruta")
    ruta_input = st.sidebar.text_area(
        "Pega aquí la lista de Clústeres (uno por línea o separados por coma):",
        placeholder="Ejemplo:\nRB-1\nRB-4\nRB-39",
        help="El mapa dibujará la ruta en el orden en que los escribas."
    )

    # Procesar la entrada del usuario
    nombres_ruta = [n.strip().upper() for n in re.split(r'[\n,]+', ruta_input) if n.strip()]

    # Buscar las coordenadas de los clústeres ingresados
    puntos_ruta = []
    for nombre in nombres_ruta:
        match = df_maestro[df_maestro['Clúster'].str.upper() == nombre]
        if not match.empty:
            puntos_ruta.append({
                'nombre': nombre,
                'lat': match.iloc[0]['lat_dec'],
                'lon': match.iloc[0]['lon_dec'],
                'pozos': match.iloc[0]['POZO']
            })
        else:
            if nombre: st.sidebar.warning(f"⚠️ Clúster '{nombre}' no encontrado en la base.")

    # 3. CONSTRUCCIÓN DEL MAPA
    centro = [df_maestro['lat_dec'].mean(), df_maestro['lon_dec'].mean()]
    m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB positron")

    # Dibujar TODOS los clústeres como puntos de referencia (gris suave)
    for _, row in df_maestro.iterrows():
        folium.CircleMarker(
            location=[row['lat_dec'], row['lon_dec']],
            radius=3,
            color="gray",
            fill=True,
            opacity=0.4
        ).add_to(m)

    # Si hay una ruta definida, dibujarla
    if puntos_ruta:
        coords_linea = [[p['lat'], p['lon']] for p in puntos_ruta]
        
        # Dibujar la línea de la ruta (Verde para representar avance)
        folium.PolyLine(
            coords_linea, 
            color="#2ecc71", 
            weight=5, 
            opacity=0.8,
            tooltip="Ruta de Movilización"
        ).add_to(m)

        # Marcar los puntos de la ruta con iconos distintivos
        for i, p in enumerate(puntos_ruta):
            color = 'green' if i == 0 else ('red' if i == len(puntos_ruta)-1 else 'blue')
            label = "INICIO" if i == 0 else ("FIN" if i == len(puntos_ruta)-1 else f"Parada {i}")
            
            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=folium.Popup(f"<b>{label}: {p['nombre']}</b><br>Pozos: {p['pozos']}", max_width=200),
                tooltip=f"{label}: {p['nombre']}",
                icon=folium.Icon(color=color, icon='play' if i==0 else 'stop')
            ).add_to(m)

        st.success(f"Ruta trazada con {len(puntos_ruta)} paradas.")
    else:
        st.info("Escribe o pega los nombres de los clústeres en la barra lateral para ver la ruta.")

    # Mostrar el mapa
    st_folium(m, width=1200, height=600, returned_objects=[])

except Exception as e:
    st.error(f"Error: {e}")
