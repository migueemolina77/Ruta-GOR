import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="Logística Rubiales - Clústeres", layout="wide")

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
def cargar_datos_agrupados(file_path):
    # Cargar desde la fila 7 (header=6)
    df = pd.read_excel(file_path, header=6)
    df.columns = df.columns.astype(str).str.strip()
    
    # Convertir coordenadas
    df['lat_dec'] = df['Latitud'].apply(dms_to_decimal)
    df['lon_dec'] = df['Longitud'].apply(dms_to_decimal)
    df = df.dropna(subset=['lat_dec', 'lon_dec'])

    # --- LÓGICA DE AGRUPACIÓN POR CLÚSTER ---
    # Agrupamos por nombre de Clúster y coordenadas para listar los pozos
    df_clusters = df.groupby(['Clúster', 'lat_dec', 'lon_dec']).agg({
        'POZO': lambda x: ', '.join(x.astype(str)) # Une los nombres de los pozos con comas
    }).reset_index()
    
    return df_clusters

st.title("📍 Mapa de Clústeres: Rubiales & Caño Sur")
st.info("Visualización simplificada por Clúster para mejorar la navegación.")

try:
    df_clusters = cargar_datos_agrupados("Coordenadas Rubiales.xlsx")

    if not df_clusters.empty:
        # Centrar mapa
        m = folium.Map(
            location=[df_clusters['lat_dec'].mean(), df_clusters['lon_dec'].mean()], 
            zoom_start=12,
            tiles="CartoDB positron"
        )

        # Añadir marcadores por Clúster
        for _, row in df_clusters.iterrows():
            # El popup ahora muestra el nombre del Clúster y la lista de todos sus pozos
            info_html = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <b style="color: #1f77b4;">CLÚSTER: {row['Clúster']}</b><br>
                <hr>
                <b>Pozos:</b> {row['POZO']}
            </div>
            """
            
            folium.Marker(
                location=[row['lat_dec'], row['lon_dec']],
                popup=folium.Popup(info_html, max_width=250),
                tooltip=f"Clúster {row['Clúster']}",
                icon=folium.Icon(color='blue', icon='home') # Icono de 'home' para representar clúster
            ).add_to(m)

        st_folium(m, width=1200, height=600, returned_objects=[])
        
        st.success(f"Se están visualizando {len(df_clusters)} clústeres operativos.")
    else:
        st.error("No se encontraron datos para mostrar.")

except Exception as e:
    st.error(f"Error al cargar la visualización: {e}")
