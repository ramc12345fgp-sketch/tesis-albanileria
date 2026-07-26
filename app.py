import streamlit as st
import math
import pandas as pd
import numpy as np
import tempfile
import os
import plotly.graph_objects as go
import streamlit.components.v1 as components

try:
    import ezdxf
    EXDXF_DISPONIBLE = True
except ImportError:
    EXDXF_DISPONIBLE = False

# --- Funciones Matematicas para Geometria CAD ---
def poly_area_centroid(pts):
    if not pts: return 0, 0, 0
    p = list(pts)
    if p[0] != p[-1]: 
        p.append(p[0])
    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(p)-1):
        x0, y0 = p[i][0], p[i][1]
        x1, y1 = p[i+1][0], p[i+1][1]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area = area / 2.0
    if area != 0:
        cx = cx / (6.0 * area)
        cy = cy / (6.0 * area)
    return abs(area), cx, cy

# -----------------------------------------
# CONFIGURACION DE PAGINA Y ESTILOS MODERNOS (TIPO SOFTWARE)
# -----------------------------------------
st.set_page_config(page_title="Software de Diseno Estructural", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* Fondo del aplicativo (Gris para que resalte la hoja) */
    .stApp {
        background-color: #e2e8f0;
    }
    
    /* Contenedor Principal simulando una HOJA A4/Software */
    .block-container {
        background-color: #ffffff;
        max-width: 1050px !important;
        padding: 3rem 4rem !important;
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
        border-radius: 8px;
        box-shadow: 0px 10px 30px -5px rgba(0, 0, 0, 0.15);
    }
    
    /* Titulos formales */
    h1, h2, h3, h4 { color: #0f172a; font-weight: 700; letter-spacing: -0.5px; }
    h1 { font-size: 1.8rem; border-bottom: 2px solid #1e3a8a; padding-bottom: 0.5rem; margin-bottom: 1.5rem; text-transform: uppercase; }
    h2 { font-size: 1.4rem; color: #1e3a8a; margin-top: 1.5rem; }
    h3 { font-size: 1.1rem; color: #334155; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }
    
    /* Tarjetas y Alertas */
    .resultado-caja {
        background-color: #f8fafc; padding: 15px 20px; border-radius: 6px; 
        border-left: 4px solid #2563eb; border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;
        margin-top: 10px; margin-bottom: 10px; color: #1e293b; font-size: 0.95rem;
    }
    
    /* Inputs Editables Destacados */
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div[class*="ValueContainer"] {
        background-color: #f1f5f9 !important; border-radius: 4px; border: 1px solid #cbd5e1;
        color: #0f172a !important; font-weight: 600 !important;
    }
    
    /* Dataframes Formato Limpio */
    table.dataframe th {
        background-color: #f8fafc !important; color: #475569 !important; 
        font-weight: 700 !important; font-size: 0.85rem; text-transform: uppercase;
        border-bottom: 2px solid #cbd5e1 !important;
    }
    table.dataframe td { font-size: 0.9rem; color: #1e293b; }

    /* ESTILOS DE IMPRESION (Ocultar UI de Streamlit y liberar scroll) */
    @media print {
        header, footer, nav, [data-testid="stSidebar"], .stTabs [data-baseweb="tab-list"], button { 
            display: none !important; 
        }
        html, body, .stApp, .main, section[data-testid="stMain"], .block-container { 
            background: white !important; 
            box-shadow: none !important; 
            margin: 0 !important; 
            padding: 0 !important; 
            max-width: 100% !important; 
            height: auto !important;
            overflow: visible !important;
            position: static !important;
        }
        @page { margin: 1.5cm; size: A4 portrait; }
        table { page-break-inside: avoid; margin-bottom: 20px; width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #cbd5e1 !important; padding: 6px !important; }
        h1, h2, h3 { page-break-after: avoid; }
        .resultado-caja { border: 1px solid #cbd5e1; break-inside: avoid; }
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------
# INICIALIZACION DE LA MEMORIA (SESSION STATE)
# -----------------------------------------
if "muros_x" not in st.session_state:
    st.session_state.muros_x = {i: pd.DataFrame(columns=["ITEM", "L(m)", "t=e(m)", "X(m)", "Y(m)"]) for i in range(1, 11)}
    st.session_state.muros_y = {i: pd.DataFrame(columns=["ITEM", "L(m)", "t=e(m)", "X(m)", "Y(m)"]) for i in range(1, 11)}
    st.session_state.areas_at = {i: pd.DataFrame(columns=["Muro", "At (m2)"]) for i in range(1, 11)}
    st.session_state.espesor_general = {i: 0.23 for i in range(1, 11)}
    st.session_state.losa_area = 614.0
    st.session_state.losa_cx = 13.50
    st.session_state.losa_cy = 13.50
    st.session_state.alturas = {i: 2.5 for i in range(1, 11)}

st.markdown("<h1>SOFTWARE DE DISEÑO ESTRUCTURAL</h1>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["1. MATERIALES Y SISMO", "2. GEOMETRIA Y ALTURAS", "3. ANALISIS ESTRUCTURAL", "4. REPORTE Y RESULTADOS"])

# =========================================
# FUNCIONES GLOBALES DE CALCULO Y ESTILOS
# =========================================
def obtener_data_nivel(n, modo_dist, esp_gen, dict_mx, dict_my):
    if modo_dist == "Tipica (Igual todos)" and n > 1:
        df_x_calc, df_y_calc = dict_mx[1].copy(), dict_my[1].copy()
        df_x_calc["t=e(m)"] = esp_gen[n]
        df_y_calc["t=e(m)"] = esp_gen[n]
    else:
        df_x_calc, df_y_calc = dict_mx[n].copy(), dict_my[n].copy()
    for col in ["L(m)", "t=e(m)", "X(m)", "Y(m)"]:
        df_x_calc[col] = pd.to_numeric(df_x_calc[col], errors='coerce').fillna(0)
        df_y_calc[col] = pd.to_numeric(df_y_calc[col], errors='coerce').fillna(0)
    return df_x_calc, df_y_calc

def color_ratio_general(val):
    if pd.isna(val): return ''
    if val >= 1.0: return 'background-color: #ef4444; color: white; font-weight: 600;'
    elif val >= 0.7: return 'background-color: #f59e0b; color: white; font-weight: 600;'
    elif val >= 0.5: return 'background-color: #fde047; color: #1e293b; font-weight: 600;'
    else: return 'background-color: #dcfce7; color: #065f46; font-weight: 600;'

def color_cumple_general(val):
    if val == "Cumple": return 'background-color: #dcfce7; color: #065f46; font-weight: 600;'
    elif val == "No Cumple": return 'background-color: #fee2e2; color: #991b1b; font-weight: 600;'
    return ''

# Función blindada para aplicar estilos sin importar la versión de Pandas
def aplicar_estilo_seguro(styler, func, subset):
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    else:
        return styler.applymap(func, subset=subset)

# =========================================
# TAB 1: CONDICIONES DE ESTRUCTURACION
# =========================================
with tab1:
    st.markdown("### 1. CONDICIONES DE ESTRUCTURACION Y MATERIALES")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**Albanileria (Ladrillo y Mortero)**")
        fm = st.number_input("Resistencia a compresion f'm (kg/cm2)", value=65.0, step=1.0)
        vm = st.number_input("Resistencia al corte v'm (kg/cm2)", value=8.1, step=0.1)
        fb = st.number_input("Resistencia del ladrillo f'b (kg/cm2)", value=130.0, step=1.0)
    with col2:
        st.write("**Concreto**")
        fc = st.number_input("Resistencia Nominal f'c (kg/cm2)", value=175.0, step=1.0)
    with col3:
        st.write("**Acero Corrugado**")
        fy = st.number_input("Fluencia fy (kg/cm2)", value=4200.0, step=100.0)

    Em = 500 * fm
    Gm = 0.4 * Em
    Ec = 15000 * math.sqrt(fc)

    st.markdown(f"""
    <div class="resultado-caja">
        <b>Modulo de Elasticidad de la Albanileria (Em):</b> {Em:,.2f} kg/cm2 <br>
        <b>Modulo de Corte de la Albanileria (Gm):</b> {Gm:,.2f} kg/cm2 <br>
        <b>Modulo de Elasticidad del Concreto (Ec):</b> {Ec:,.2f} kg/cm2
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 2. PARAMETROS SISMORRESISTENTES (NORMA E.030)")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        zona_z_opt = st.selectbox("Zona Sismica (Z)", ["Z4", "Z3", "Z2", "Z1"], index=0)
        uso_u_opt = st.selectbox("Categoria de Edificacion (U)", ["A", "B", "C"], index=2)
        suelo_s_opt = st.selectbox("Perfil de Suelo (S)", ["S0", "S1", "S2", "S3"], index=2)
    with col_s2:
        coef_ct_opt = st.number_input("Coeficiente CT", value=60.0, step=5.0)
        r0_opt = st.number_input("Coeficiente Basico de Reduccion (R0)", value=6.0, step=0.5)
    with col_s3:
        ia_opt = st.number_input("Irregularidad en Altura (Ia)", value=1.00, step=0.05)
        ip_opt = st.number_input("Irregularidad en Planta (Ip)", value=0.90, step=0.05)
        
    z_dict = {"Z4": 0.45, "Z3": 0.35, "Z2": 0.25, "Z1": 0.10}
    u_dict = {"A": 1.5, "B": 1.3, "C": 1.0}
    s_dict = {"S0": {"S": 0.80, "Tp": 0.3}, "S1": {"S": 1.00, "Tp": 0.4}, "S2": {"S": 1.05, "Tp": 0.6}, "S3": {"S": 1.10, "Tp": 1.0}}
    
    Z_val = z_dict[zona_z_opt]
    U_val = u_dict[uso_u_opt]
    S_val = s_dict[suelo_s_opt]["S"]
    Tp_val = s_dict[suelo_s_opt]["Tp"]

# =========================================
# TAB 2: GEOMETRIA Y ALTURAS
# =========================================
with tab2:
    st.markdown("### 1. CONFIGURACION DEL MODELO Y ALTURAS")
    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        num_niveles = st.number_input("Numero Total de Niveles", min_value=1, max_value=10, value=5)
    with col_cfg2:
        modo = st.radio("Distribucion de Planta", ["Tipica (Igual todos)", "Diferente por Nivel"])
    with col_cfg3:
        modo_altura = st.radio("Configuracion de Alturas", ["Altura Tipica", "Alturas Diferentes"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.write("**Definicion de Alturas de Entrepiso**")
    if modo_altura == "Altura Tipica":
        h_tipica = st.number_input("Altura de Entrepiso General (m)", value=2.50, step=0.10)
        for i in range(1, int(num_niveles) + 1):
            st.session_state.alturas[i] = h_tipica
    else:
        cols_h = st.columns(int(num_niveles))
        for i in range(1, int(num_niveles) + 1):
            with cols_h[i-1]:
                st.session_state.alturas[i] = st.number_input(f"Piso {i}", value=float(st.session_state.alturas.get(i, 2.50)), step=0.10, key=f"h_{i}")

    alturas_acumuladas = {}
    acum = 0
    for n in range(1, int(num_niveles) + 1):
        acum += st.session_state.alturas[n]
        alturas_acumuladas[n] = acum
    hm_opt = acum
    
    st.markdown(f"""
    <div class="resultado-caja">
        <b>Altura Total de la Edificacion (Hm):</b> {hm_opt:.2f} m
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 2. PLANIMETRIA Y BASE DE DATOS DE MUROS")
    
    nivel_actual = st.selectbox("Seleccione Nivel de Trabajo:", range(1, int(num_niveles) + 1))
    metodo_ingreso = st.radio("Metodo de importacion:", ["Cargar Plano CAD (DXF)", "Ingreso Manual (Excel)"], horizontal=True)
    
    bloquear_tablas = False
    if modo == "Tipica (Igual todos)" and nivel_actual > 1:
        st.info(f"El Nivel {nivel_actual} adopta la geometria del Nivel 1. Espesor ajustable:")
        bloquear_tablas = True 
        nuevo_t = st.number_input(f"Espesor general Nivel {nivel_actual} (m):", min_value=0.05, max_value=0.50, value=float(st.session_state.espesor_general[nivel_actual]), step=0.01)
        if st.session_state.espesor_general[nivel_actual] != nuevo_t:
            st.session_state.espesor_general[nivel_actual] = nuevo_t
            st.rerun() 

    if metodo_ingreso == "Cargar Plano CAD (DXF)" and not bloquear_tablas:
        if not EXDXF_DISPONIBLE:
            st.error("Libreria 'ezdxf' no instalada en el entorno.")
        else:
            archivo_dxf = st.file_uploader(f"Archivo DXF (Nivel {nivel_actual})", type=["dxf"], key=f"dxf_{nivel_actual}")
            if archivo_dxf is not None:
                if st.button("Procesar Archivo DXF", key=f"btn_dxf_{nivel_actual}"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_file:
                        tmp_file.write(archivo_dxf.getvalue())
                        tmp_path = tmp_file.name
                    try:
                        doc = ezdxf.readfile(tmp_path)
                        msp = doc.modelspace()
                        muros_raw, losa_raw, cols_raw = [], [], []
                        min_x, min_y = float('inf'), float('inf')
                        for entity in msp:
                            if entity.dxftype() == 'LWPOLYLINE':
                                layer = entity.dxf.layer.upper()
                                pts = list(entity.get_points(format='xy'))
                                for p in pts:
                                    if p[0] < min_x: min_x = p[0]
                                    if p[1] < min_y: min_y = p[1]
                                if layer == 'MURO': muros_raw.append(pts)
                                elif layer == 'LOSA': losa_raw.append(pts)
                                elif layer == 'C_CONFINAMIENTO': cols_raw.append(pts)
                        if min_x == float('inf'): min_x, min_y = 0.0, 0.0
                        st.session_state[f"muros_raw_{nivel_actual}"] = muros_raw
                        st.session_state[f"losa_raw_{nivel_actual}"] = losa_raw
                        st.session_state[f"cols_raw_{nivel_actual}"] = cols_raw
                        st.session_state[f"min_x_{nivel_actual}"] = min_x
                        st.session_state[f"min_y_{nivel_actual}"] = min_y
                    except Exception as e:
                        st.error(f"Error procesando DXF: {e}")
                    finally:
                        if os.path.exists(tmp_path): os.remove(tmp_path)
                
                if f"muros_raw_{nivel_actual}" in st.session_state:
                    st.write("**Visualizacion y Set de Coordenadas de Origen**")
                    col_origen1, col_origen2 = st.columns(2)
                    with col_origen1: origen_x = st.number_input("Origen X (m)", value=float(st.session_state[f"min_x_{nivel_actual}"]), step=0.1)
                    with col_origen2: origen_y = st.number_input("Origen Y (m)", value=float(st.session_state[f"min_y_{nivel_actual}"]), step=0.1)
                    
                    fig_cad = go.Figure()
                    def add_poly_trace(fig, polys, color, name):
                        for pts in polys:
                            x = [p[0] - origen_x for p in pts]
                            y = [p[1] - origen_y for p in pts]
                            if x[0] != x[-1] or y[0] != y[-1]:
                                x.append(x[0]); y.append(y[0])
                            fig.add_trace(go.Scatter(x=x, y=y, fill='toself', mode='lines', line=dict(color=color), name=name, showlegend=False))

                    add_poly_trace(fig_cad, st.session_state[f"losa_raw_{nivel_actual}"], '#cbd5e1', 'Losa')
                    add_poly_trace(fig_cad, st.session_state[f"muros_raw_{nivel_actual}"], '#0f172a', 'Muro')
                    add_poly_trace(fig_cad, st.session_state[f"cols_raw_{nivel_actual}"], '#3b82f6', 'Columna')
                    fig_cad.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(size=10, color='#ef4444', symbol='cross'), name='Origen(0,0)'))
                    fig_cad.update_layout(height=400, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), yaxis=dict(scaleanchor="x", scaleratio=1))
                    st.plotly_chart(fig_cad, use_container_width=True)

                    if st.button("Procesar Muros y Extraer Base de Datos", type="primary"):
                        muros_x_data, muros_y_data = [], []
                        idx_x, idx_y = 1, 1
                        for pts in st.session_state[f"muros_raw_{nivel_actual}"]:
                            pts_adj = [(p[0] - origen_x, p[1] - origen_y) for p in pts]
                            area, cx, cy = poly_area_centroid(pts_adj)
                            xs, ys = [p[0] for p in pts_adj], [p[1] for p in pts_adj]
                            dx, dy = max(xs) - min(xs), max(ys) - min(ys)
                            if dx >= dy:
                                muros_x_data.append({"ITEM": f"X{idx_x}", "L(m)": round(dx, 2), "t=e(m)": round(dy, 2), "X(m)": round(cx, 3), "Y(m)": round(cy, 3)})
                                idx_x += 1
                            else:
                                muros_y_data.append({"ITEM": f"Y{idx_y}", "L(m)": round(dy, 2), "t=e(m)": round(dx, 2), "X(m)": round(cx, 3), "Y(m)": round(cy, 3)})
                                idx_y += 1
                        if muros_x_data: st.session_state.muros_x[nivel_actual] = pd.DataFrame(muros_x_data)
                        if muros_y_data: st.session_state.muros_y[nivel_actual] = pd.DataFrame(muros_y_data)
                        if st.session_state[f"losa_raw_{nivel_actual}"]:
                            losa_adj = [(p[0] - origen_x, p[1] - origen_y) for p in st.session_state[f"losa_raw_{nivel_actual}"][0]]
                            a_losa, cx_losa, cy_losa = poly_area_centroid(losa_adj)
                            st.session_state.losa_area = round(a_losa, 2)
                            st.session_state.losa_cx = round(cx_losa, 3)
                            st.session_state.losa_cy = round(cy_losa, 3)
                        st.success("Planimetria procesada con exito.")

    elif metodo_ingreso == "Ingreso Manual (Excel)" and not bloquear_tablas and (modo != "Tipica (Igual todos)" or nivel_actual == 1):
        archivo_subido = st.file_uploader(f"Archivo Excel Muros (Nivel {nivel_actual})", type=["xlsx", "xls"], key=f"up_{nivel_actual}")
        if archivo_subido is not None:
            try:
                df_raw = pd.read_excel(archivo_subido, header=None)
                fila_headers = -1
                for index, row in df_raw.iterrows():
                    if "ITEM" in row.astype(str).str.strip().str.upper().values:
                        fila_headers = index; break
                if fila_headers != -1:
                    row_vals = df_raw.iloc[fila_headers].astype(str).str.strip().str.upper().values
                    indices_item = [i for i, val in enumerate(row_vals) if val == "ITEM"]
                    if len(indices_item) >= 1:
                        col_x_start = indices_item[0]
                        df_x_ext = df_raw.iloc[fila_headers+1:, col_x_start:col_x_start+5].copy()
                        df_x_ext.columns = ["ITEM", "L(m)", "t=e(m)", "X(m)", "Y(m)"]
                        st.session_state.muros_x[nivel_actual] = df_x_ext.dropna(subset=["ITEM", "L(m)"])
                    if len(indices_item) >= 2:
                        col_y_start = indices_item[1]
                        df_y_ext = df_raw.iloc[fila_headers+1:, col_y_start:col_y_start+5].copy()
                        df_y_ext.columns = ["ITEM", "L(m)", "t=e(m)", "X(m)", "Y(m)"]
                        st.session_state.muros_y[nivel_actual] = df_y_ext.dropna(subset=["ITEM", "L(m)"])
                    st.success("Datos importados.")
            except Exception as e:
                st.error(f"Error de lectura: {e}")

    col_tx, col_ty = st.columns(2)
    df_x_vista = st.session_state.muros_x[nivel_actual].copy() if modo == "Diferente por Nivel" or nivel_actual == 1 else st.session_state.muros_x[1].copy()
    df_y_vista = st.session_state.muros_y[nivel_actual].copy() if modo == "Diferente por Nivel" or nivel_actual == 1 else st.session_state.muros_y[1].copy()
    
    if bloquear_tablas:
        df_x_vista["t=e(m)"] = st.session_state.espesor_general[nivel_actual]
        df_y_vista["t=e(m)"] = st.session_state.espesor_general[nivel_actual]

    for col in ["L(m)", "t=e(m)", "X(m)", "Y(m)"]:
        df_x_vista[col] = pd.to_numeric(df_x_vista[col], errors='coerce')
        df_y_vista[col] = pd.to_numeric(df_y_vista[col], errors='coerce')

    with col_tx:
        st.write(f"**MUROS DIRECCION X-X**")
        edit_x = st.data_editor(df_x_vista, num_rows="dynamic" if not bloquear_tablas else "fixed", disabled=bloquear_tablas, key=f"tbl_x_{nivel_actual}", width="stretch")
        if not bloquear_tablas: st.session_state.muros_x[nivel_actual] = edit_x

    with col_ty:
        st.write(f"**MUROS DIRECCION Y-Y**")
        edit_y = st.data_editor(df_y_vista, num_rows="dynamic" if not bloquear_tablas else "fixed", disabled=bloquear_tablas, key=f"tbl_y_{nivel_actual}", width="stretch")
        if not bloquear_tablas: st.session_state.muros_y[nivel_actual] = edit_y

    st.markdown("---")
    st.markdown("### 3. VERIFICACION DE DENSIDAD DE MUROS (Global)")
    area_construida = st.number_input("Area Construida del Edificio (Ap) [m2]", step=10.0, value=float(st.session_state.losa_area))
    st.session_state.losa_area = area_construida
    
    zusn_56_base = [0.0442, 0.0354, 0.0265, 0.0177, 0.0088, 0.005, 0.005, 0.005, 0.005, 0.005] 
    verif_data = []
    for n in range(1, int(num_niveles) + 1):
        df_x_calc, df_y_calc = obtener_data_nivel(n, modo, st.session_state.espesor_general, st.session_state.muros_x, st.session_state.muros_y)
        area_x = (pd.to_numeric(df_x_calc["L(m)"], errors='coerce') * pd.to_numeric(df_x_calc["t=e(m)"], errors='coerce')).sum()
        area_y = (pd.to_numeric(df_y_calc["L(m)"], errors='coerce') * pd.to_numeric(df_y_calc["t=e(m)"], errors='coerce')).sum()
        densidad_x = area_x / area_construida if area_construida > 0 else 0
        densidad_y = area_y / area_construida if area_construida > 0 else 0
        zusn_val = zusn_56_base[n-1] if n <= len(zusn_56_base) else 0.005
        ratio_x = zusn_val / densidad_x if densidad_x > 0 else 0
        ratio_y = zusn_val / densidad_y if densidad_y > 0 else 0
        verif_data.append({"Nivel": n, "Area X": area_x, "Area Y": area_y, "Ap": area_construida, "∑tLx/Ap": densidad_x, "∑tLy/Ap": densidad_y, "ZUSN/56": zusn_val, "Ratio X": ratio_x, "Ratio Y": ratio_y, "Verif. X": "Cumple" if ratio_x <= 1.0 else "No Cumple", "Verif. Y": "Cumple" if ratio_y <= 1.0 else "No Cumple"})
        
    df_verificacion = pd.DataFrame(verif_data)
    styled_df_v = df_verificacion.style
    styled_df_v = aplicar_estilo_seguro(styled_df_v, color_ratio_general, subset=['Ratio X', 'Ratio Y'])
    styled_df_v = aplicar_estilo_seguro(styled_df_v, color_cumple_general, subset=['Verif. X', 'Verif. Y'])
    styled_df_v = styled_df_v.format({'Area X': '{:.2f}', 'Area Y': '{:.2f}', 'Ap': '{:.2f}', '∑tLx/Ap': '{:.4f}', '∑tLy/Ap': '{:.4f}', 'ZUSN/56': '{:.4f}', 'Ratio X': '{:.2%}', 'Ratio Y': '{:.2%}'})
    st.dataframe(styled_df_v, width="stretch", hide_index=True)


# =========================================
# TAB 3: ANALISIS ESTRUCTURAL Y AXIAL
# =========================================
with tab3:
    st.markdown("### 1. CARGAS UNITARIAS Y CENTROIDES")
    col_cm1, col_cm2, col_cm3 = st.columns(3)
    with col_cm1:
        st.write("**Cargas Muertas (CM)**")
        p_muro = st.number_input("Peso Especifico Muro (ton/m3)", value=1.80, step=0.10)
        p_losa = st.number_input("Peso Especifico Losa (ton/m2)", value=0.30, step=0.05)
        p_acabados = st.number_input("Peso Acabados (ton/m2)", value=0.10, step=0.05)
        p_piso = st.number_input("Peso Piso Terminado (ton/m2)", value=0.10, step=0.05)
    with col_cm2:
        st.write("**Cargas Vivas (CV)**")
        cv_tipico = st.number_input("Sobrecarga Tipica (ton/m2)", value=0.20, step=0.05)
        cv_azotea = st.number_input("Sobrecarga Azotea (ton/m2)", value=0.10, step=0.05)
        categoria = st.selectbox("Categoria Edificacion", ["C (25% CV)", "A o B (50% CV)"])
    with col_cm3:
        st.write("**Centroides de Losa (CAD/Manual)**")
        xlosa = st.number_input("Centro Losa Xi (m)", step=0.5, value=float(st.session_state.losa_cx))
        ylosa = st.number_input("Centro Losa Yi (m)", step=0.5, value=float(st.session_state.losa_cy))

    # --- CALCULO GLOBAL DE PESOS ---
    porcentaje_sismo = 0.25 if "C" in categoria else 0.50
    data_cm, data_pesos = [], []
    for n in range(1, int(num_niveles) + 1):
        df_x_calc, df_y_calc = obtener_data_nivel(n, modo, st.session_state.espesor_general, st.session_state.muros_x, st.session_state.muros_y)
        h_piso = st.session_state.alturas[n]
        
        peso_mx = df_x_calc["L(m)"] * df_x_calc["t=e(m)"] * h_piso * p_muro
        peso_my = df_y_calc["L(m)"] * df_y_calc["t=e(m)"] * h_piso * p_muro
        px_mx, py_mx = peso_mx * df_x_calc["X(m)"], peso_mx * df_x_calc["Y(m)"]
        px_my, py_my = peso_my * df_y_calc["X(m)"], peso_my * df_y_calc["Y(m)"]
        
        peso_muros_total = peso_mx.sum() + peso_my.sum()
        peso_losa_total = st.session_state.losa_area * p_losa
        peso_cm_piso = peso_muros_total + peso_losa_total
        
        cm_x = (px_mx.sum() + px_my.sum() + peso_losa_total * xlosa) / peso_cm_piso if peso_cm_piso > 0 else 0
        cm_y = (py_mx.sum() + py_my.sum() + peso_losa_total * ylosa) / peso_cm_piso if peso_cm_piso > 0 else 0
        data_cm.append({"Nivel": n, "Peso Total (t)": peso_cm_piso, "CMx": cm_x, "CMy": cm_y})
        
        cm_muerta = peso_cm_piso + (st.session_state.losa_area * p_acabados) + (st.session_state.losa_area * p_piso)
        cv_piso = st.session_state.losa_area * cv_azotea if n == int(num_niveles) else st.session_state.losa_area * cv_tipico
        peso_total_piso = cm_muerta + cv_piso
        peso_sismico = cm_muerta + (porcentaje_sismo * cv_piso)
        data_pesos.append({"Nivel": n, "CM": cm_muerta, "CV": cv_piso, "Peso Total": peso_total_piso, "Peso Sismico": peso_sismico})

    df_pesos = pd.DataFrame(data_pesos)
    peso_sismico_total = df_pesos['Peso Sismico'].sum()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 2. CENTRO DE RIGIDEZ POR NIVEL (CR)")
    st.info("Calculado evaluando la altura real de cada nivel y su longitud.")
    nivel_cr = st.selectbox("Seleccionar Nivel para Rigidez:", range(1, int(num_niveles) + 1), key="niv_cr")
    df_x_cr, df_y_cr = obtener_data_nivel(nivel_cr, modo, st.session_state.espesor_general, st.session_state.muros_x, st.session_state.muros_y)
    altura_cr = st.session_state.alturas[nivel_cr]

    def calcular_rigideces_abasto(df, h_piso_m):
        rigideces = []
        for idx, row in df.iterrows():
            l_m, t_m = row["L(m)"], row["t=e(m)"]
            if l_m <= 0 or t_m <= 0:
                rigideces.append(0)
                continue
            l_cm, t_cm, h_cm = l_m * 100.0, t_m * 100.0, h_piso_m * 100.0
            ratio_hl = h_cm / l_cm
            denominador = 4.0 * (ratio_hl ** 3) + 3.0 * ratio_hl
            K = (Em * t_cm) / denominador if denominador > 0 else 0
            rigideces.append(K)
        return rigideces

    df_x_cr["K (kg/cm)"] = calcular_rigideces_abasto(df_x_cr, altura_cr)
    df_y_cr["K (kg/cm)"] = calcular_rigideces_abasto(df_y_cr, altura_cr)

    col_crx, col_cry = st.columns(2)
    with col_crx:
        st.write(f"**Aporte X (Nivel {nivel_cr} | h={altura_cr}m)**")
        st.dataframe(df_x_cr.style.format({'L(m)': '{:.2f}', 't=e(m)': '{:.2f}', 'X(m)': '{:.2f}', 'Y(m)': '{:.2f}', 'K (kg/cm)': '{:,.2f}'}), width="stretch", hide_index=True)
    with col_cry:
        st.write(f"**Aporte Y (Nivel {nivel_cr} | h={altura_cr}m)**")
        st.dataframe(df_y_cr.style.format({'L(m)': '{:.2f}', 't=e(m)': '{:.2f}', 'X(m)': '{:.2f}', 'Y(m)': '{:.2f}', 'K (kg/cm)': '{:,.2f}'}), width="stretch", hide_index=True)

    sum_Ky, sum_Kx = df_y_cr["K (kg/cm)"].sum(), df_x_cr["K (kg/cm)"].sum()
    Crx = ((df_y_cr["K (kg/cm)"] * df_y_cr["X(m)"]).sum()) / sum_Ky if sum_Ky > 0 else 0
    Cry = ((df_x_cr["K (kg/cm)"] * df_x_cr["Y(m)"]).sum()) / sum_Kx if sum_Kx > 0 else 0

    st.markdown(f"""
    <div class="resultado-caja">
        <b>Coordenadas del Centro de Rigidez (Nivel {nivel_cr}):</b> &nbsp; <b>Crx:</b> {Crx:.3f} m &nbsp; | &nbsp; <b>Cry:</b> {Cry:.3f} m
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 3. VERIFICACION DE ESFUERZOS AXIALES")
    st.info("Registro de Areas Tributarias (At) para carga axial ultima vs capacidad.")
    nivel_axial = st.selectbox("Nivel para Control Axial:", range(1, int(num_niveles) + 1), key="niv_axial_at")
    df_x_ax, _ = obtener_data_nivel(nivel_axial, modo, st.session_state.espesor_general, st.session_state.muros_x, st.session_state.muros_y)

    if st.session_state.areas_at[nivel_axial].empty:
        muros_base = df_x_ax["ITEM"].tolist() if not df_x_ax.empty else ["X1"]
        st.session_state.areas_at[nivel_axial] = pd.DataFrame({"Muro": muros_base, "At (m2)": [0.0] * len(muros_base)})

    st.write(f"**Set de Areas Tributarias - Nivel {nivel_axial}**")
    edit_at = st.data_editor(st.session_state.areas_at[nivel_axial], num_rows="dynamic", key=f"editor_at_{nivel_axial}", width="stretch")
    st.session_state.areas_at[nivel_axial] = edit_at

    peso_acumulado_cm = df_pesos[df_pesos["Nivel"] >= nivel_axial]["CM"].sum()
    peso_acumulado_cv = df_pesos[df_pesos["Nivel"] >= nivel_axial]["CV"].sum()
    
    axial_data = []
    for idx, row in edit_at.iterrows():
        muro_item = row["Muro"]
        at_val = float(row["At (m2)"]) if pd.notna(row["At (m2)"]) else 0.0
        if at_val > 0:
            sum_at_total = edit_at["At (m2)"].astype(float).sum()
            factor = at_val / sum_at_total if sum_at_total > 0 else 0
            ps_val = (peso_acumulado_cm + peso_acumulado_cv) * factor
            pu_val = (1.3 * peso_acumulado_cm + peso_acumulado_cv) * factor
            capacidad_axial = (0.15 * fm * (at_val * 10000)) / 1000.0
            ratio = pu_val / capacidad_axial if capacidad_axial > 0 else 0
            verif = "Cumple" if ratio <= 1.0 else "No Cumple"
        else:
            ps_val, pu_val, capacidad_axial, ratio, verif = 0, 0, 0, 0, "No Aplica"

        axial_data.append({"Muro": muro_item, "At (m2)": round(at_val, 3), "Ps (ton)": round(ps_val, 2), "Pu (ton)": round(pu_val, 2), "Cap Adm (ton)": round(capacidad_axial, 2), "Verificacion": verif, "Ratio": ratio})

    df_axial_res = pd.DataFrame(axial_data)
    styled_axial = df_axial_res.style
    styled_axial = aplicar_estilo_seguro(styled_axial, color_ratio_general, subset=['Ratio'])
    styled_axial = aplicar_estilo_seguro(styled_axial, color_cumple_general, subset=['Verificacion'])
    styled_axial = styled_axial.format({'At (m2)': '{:.3f}', 'Ps (ton)': '{:.2f}', 'Pu (ton)': '{:.2f}', 'Cap Adm (ton)': '{:.2f}', 'Ratio': '{:.1%}'})
    st.dataframe(styled_axial, width="stretch", hide_index=True)


# =========================================
# TAB 4: REPORTE DE IMPRESION (ESTILO SOFTWARE HTML)
# =========================================
with tab4:
    components.html(
        """
        <style>
        .header-soft { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #cbd5e1; padding-bottom: 12px; margin-bottom: 15px; font-family: 'Segoe UI', sans-serif;}
        .title-left h1 { margin: 0; font-size: 22px; color: #0f172a; font-weight: 800; }
        .title-left p { margin: 2px 0 0 0; font-size: 13px; color: #475569; font-weight: 600; text-transform: uppercase; }
        .toolbar { display: flex; gap: 8px; }
        .btn-tool { background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; cursor: pointer; color: #334155; display: flex; align-items: center; gap: 6px; font-weight: 600; font-size: 13px; transition: 0.2s; }
        .btn-tool:hover { background: #f1f5f9; border-color: #94a3b8; }
        .btn-print { background: #1e3a8a; color: white; border: none; }
        .btn-print:hover { background: #1e40af; }
        @media print { .toolbar { display: none !important; } }
        </style>
        <div class="header-soft">
            <div class="title-left">
                <h1>SOFTWARE E.030</h1>
                <p>ANALISIS SISMICO Y DISENO - v1.0</p>
            </div>
            <div class="toolbar">
                <button class="btn-tool" onclick="document.body.style.filter='invert(1) hue-rotate(180deg)'">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M6 .278a.77.77 0 0 1 .08.858 7.2 7.2 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277q.792-.001 1.533-.16a.79.79 0 0 1 .81.316.73.73 0 0 1-.031.893A8.35 8.35 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.75.75 0 0 1 6 .278"/></svg> 
                </button>
                <button class="btn-tool btn-print" onclick="window.parent.print()">
                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M2.5 8a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1"/><path d="M5 1a2 2 0 0 0-2 2v2H2a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h1v1a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-1h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1V3a2 2 0 0 0-2-2zM4 3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2H4zm1 5a2 2 0 0 0-2 2v1H2a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v-1a2 2 0 0 0-2-2zm7 2v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1"/></svg>
                    IMPRIMIR
                </button>
            </div>
        </div>
        """, height=70
    )

    st.markdown(f"**PROYECTO:** EDIFICACION DE ALBANILERIA CONFINADA ({num_niveles} NIVELES)")
    st.markdown(f"**ALTURA TOTAL DEL MODELO (Hm):** {hm_opt:.2f} m")

    # REPORTE: DENSIDAD DE MUROS
    st.markdown("### 1. VERIFICACION DE DENSIDAD DE MUROS")
    df_verificacion_print = df_verificacion.copy()
    
    # Aplicar estilos y generar tabla nativa HTML para que se imprima perfecto
    styled_df_v_print = df_verificacion_print.style
    styled_df_v_print = aplicar_estilo_seguro(styled_df_v_print, color_ratio_general, subset=['Ratio X', 'Ratio Y'])
    styled_df_v_print = aplicar_estilo_seguro(styled_df_v_print, color_cumple_general, subset=['Verif. X', 'Verif. Y'])
    styled_df_v_print = styled_df_v_print.format({'Area X': '{:.2f}', 'Area Y': '{:.2f}', 'Ap': '{:.2f}', '∑tLx/Ap': '{:.4f}', '∑tLy/Ap': '{:.4f}', 'ZUSN/56': '{:.4f}', 'Ratio X': '{:.2%}', 'Ratio Y': '{:.2%}'})
    st.table(styled_df_v_print)

    # REPORTE: MASAS Y PESOS
    st.markdown("### 2. MASAS Y PESO SISMICO DE LA EDIFICACION")
    st.table(df_pesos.style.format({'CM': '{:.2f}', 'CV': '{:.2f}', 'Peso Total': '{:.2f}', 'Peso Sismico': '{:.2f}'}))
    st.markdown(f"**PESO SISMICO TOTAL (P):** {peso_sismico_total:,.2f} ton")

    # REPORTE: FUERZAS SISMICAS
    st.markdown("### 3. ANALISIS ESTATICO DE FUERZAS EQUIVALENTES")
    T_val = hm_opt / coef_ct_opt if coef_ct_opt > 0 else 0.1
    C_val = 2.5 if T_val < Tp_val else min(2.5 * (Tp_val / T_val), 2.5)
    vx_sev_base = (Z_val * U_val * C_val * S_val / 3.0) * peso_sismico_total
    vx_mod_base = (Z_val * U_val * C_val * S_val / 6.0) * peso_sismico_total
    vx_sev_final = vx_sev_base + 0.3 * vx_sev_base
    vx_mod_final = vx_mod_base + 0.3 * vx_mod_base

    def calcular_distribucion_print(v_basal_val, df_p):
        k_val = 1.0 if T_val <= 0.5 else min(0.75 + 0.5 * T_val, 2.0)
        temp_calculos, suma_p_hk = [], 0
        for idx, row in df_p.iterrows():
            n, peso = row["Nivel"], row["Peso Sismico"]
            altura_n = alturas_acumuladas[n]
            p_hk = peso * (altura_n ** k_val)
            suma_p_hk += p_hk
            temp_calculos.append({"nivel": n, "Peso": peso, "altura": altura_n, "k": k_val, "p*(h^k)": p_hk})
            
        lista_aux_vi = []
        for item in reversed(temp_calculos):
            alpha = item["p*(h^k)"] / suma_p_hk if suma_p_hk > 0 else 0
            fi = alpha * v_basal_val
            lista_aux_vi.append({"item": item, "alpha": alpha, "fi": fi})
            
        vi_acum, resultado_final = 0, []
        for entry in lista_aux_vi:
            vi_acum += entry["fi"]
            entry["vi"] = vi_acum
            
        for entry in reversed(lista_aux_vi):
            it = entry["item"]
            incidencia = (entry["vi"] / v_basal_val) * 100 if v_basal_val > 0 else 0
            resultado_final.append({"Nivel": it["nivel"], "Peso Sismico": it["Peso"], "Altura H_i": round(it["altura"], 2), "p*(h^k)": round(it["p*(h^k)"], 2), "Factor Alfa": round(entry["alpha"], 3), "Fuerza F_i": round(entry["fi"], 2), "Cortante V_i": round(entry["vi"], 2), "Incidencia": f"{int(round(incidencia))}%"})
        return pd.DataFrame(resultado_final)

    st.write(f"**SISMO SEVERO (R=3)** | Cortante Basal Final: **{vx_sev_final:,.2f} ton**")
    st.table(calcular_distribucion_print(vx_sev_final, df_pesos))
    
    st.write(f"**SISMO MODERADO (R=6)** | Cortante Basal Final: **{vx_mod_final:,.2f} ton**")
    st.table(calcular_distribucion_print(vx_mod_final, df_pesos))
