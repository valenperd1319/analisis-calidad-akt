import streamlit as st
import pandas as pd
import numpy as np
import json
import sqlite3
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Análisis de Calidad — AKT Motos",
    page_icon="🏍",
    layout="wide",
    initial_sidebar_state="expanded"
)

KB = {'Tallado': {'tipo': 'Pintura', 'desc': 'Marcas superficiales en la pintura por contacto físico', 'causas': ['Manipulación sin guantes post-horno', 'Apilamiento sin separadores', 'Superficies de trabajo con bordes filosos', 'Embalaje inadecuado'], 'soluciones': ['Usar guantes de algodón en toda la cadena post-horno', 'Implementar separadores de espuma entre piezas', 'Revisar puntos de contacto en línea de producción', 'Establecer zonas de almacenamiento con soportes acolchados'], 'std': 'T', 'urgencia': 2}, 'Grumo': {'tipo': 'Pintura', 'desc': 'Partículas o protuberancias en la superficie mayores a 0.3mm', 'causas': ['Filtros de cabina saturados', 'Pintura sin colar antes de aplicar', 'Boquilla desgastada', 'Presión de atomización incorrecta', 'Temperatura de cabina muy alta'], 'soluciones': ['Cambiar filtros cada 100 horas o 3-4 semanas', 'Colar pintura con malla 100-150 micras', 'Verificar presión 1.5-2 bar en HVLP', 'Reemplazar boquillas mensualmente', 'Mantener cabina 20-25°C'], 'std': 'C', 'urgencia': 4}, 'Rayado': {'tipo': 'Pintura', 'desc': 'Arañazos que pueden llegar al sustrato', 'causas': ['Manipulación sin guantes o con materiales abrasivos', 'Empaque sin protección', 'Roce durante ensamble'], 'soluciones': ['Protocolo obligatorio de guantes de algodón', 'Bolsas o fundas de tela por pieza', 'Revisar puntos de contacto en línea de ensamble'], 'std': 'D', 'urgencia': 5}, 'Adherencia': {'tipo': 'Pintura', 'desc': 'Falta de anclaje de la pintura al sustrato', 'causas': ['Superficie contaminada con grasa o aceite', 'Omisión del promotor de adhesión en ABS/PP', 'Humedad en la superficie', 'Alta humedad ambiental en Colombia'], 'soluciones': ['Lavar con desengrasante antes de cada pieza', 'Aplicar promotor en piezas de ABS y PP (5-10 min oreo)', 'Verificar sustrato completamente seco', 'Controlar humedad relativa 40-60% en cabina'], 'std': 'D', 'urgencia': 5, 'colombia_note': 'En Colombia la alta humedad especialmente en temporadas de lluvia es un factor crítico. Usar catalizadores adaptados al clima tropical.'}, 'Ojo de pez': {'tipo': 'Pintura', 'desc': 'Cráteres circulares por contaminación con silicona o aceite', 'causas': ['Aire comprimido contaminado con aceite', 'Trapos con residuos de silicona', 'Productos con silicona cerca de la cabina'], 'soluciones': ['Instalar separador de agua y aceite en la línea de aire', 'Prohibir productos con silicona en el área', 'Limpiar cabina con desengrasante semanalmente'], 'std': 'C', 'urgencia': 3}, 'Diferente tono': {'tipo': 'Pintura', 'desc': 'Variación de color respecto a la probeta aprobada', 'causas': ['Mezcla incorrecta o diferente lote de pigmento', 'Variaciones de temperatura en el horno', 'Tiempo de mezcla insuficiente'], 'soluciones': ['Verificar número de lote antes de producción', 'Calibrar temperatura del horno periódicamente', 'Agitar la pintura mínimo 5 minutos antes de aplicar'], 'std': 'D', 'urgencia': 4}, 'Micro hervido': {'tipo': 'Pintura', 'desc': 'Pequeñas burbujas por disolventes atrapados', 'causas': ['Temperatura muy alta que seca la superficie antes del interior', 'Diluyente demasiado lento', 'Capas muy gruesas', 'Alta temperatura + humedad en Colombia'], 'soluciones': ['Usar diluyentes apropiados a la temperatura del día', 'Respetar tiempos de flash-off entre capas', 'Aplicar capas más delgadas', 'Controlar temperatura de cabina 20-25°C'], 'std': 'C', 'urgencia': 3, 'colombia_note': 'En ciudades de clima cálido ajustar el catalizador según recomendación del fabricante.'}, 'Pintura chorreada': {'tipo': 'Pintura', 'desc': 'Escurrimientos en superficies inclinadas', 'causas': ['Exceso de pintura en una pasada', 'Diluyente demasiado lento', 'Distancia de pistola muy corta'], 'soluciones': ['Aplicar capas más delgadas', 'Calibrar presión caudal y abanico', 'Mantener distancia constante 20-30 cm'], 'std': 'D', 'urgencia': 4}, 'Faltante de pintura': {'tipo': 'Pintura', 'desc': 'Zonas sin cobertura de pintura', 'causas': ['Boquilla tapada', 'Velocidad de aplicación alta', 'Presión insuficiente'], 'soluciones': ['Verificar boquilla antes de producción', 'Establecer revisión de todas las caras al salir del horno', 'Calibrar presión al inicio de cada turno'], 'std': 'D', 'urgencia': 5}, 'Hundido': {'tipo': 'Pintura', 'desc': 'Deformación o abolladura en la pieza', 'causas': ['Golpes durante manejo pre-pintado', 'Presión excesiva en herramentales', 'Impacto en transporte'], 'soluciones': ['Revisar piezas en recepción antes de ingresar al proceso', 'Usar soportes acolchados', 'Registrar piezas con defecto previo para trazabilidad'], 'std': 'D', 'urgencia': 5}, 'Piel naranja': {'tipo': 'Pintura', 'desc': 'Textura rugosa similar a piel de naranja', 'causas': ['Presión de atomización muy alta', 'Distancia de pistola muy grande', 'Diluyente muy rápido'], 'soluciones': ['Ajustar presión dentro del rango recomendado', 'Mantener distancia adecuada 20-30 cm', 'Usar diluyente apropiado a temperatura de trabajo'], 'std': 'C', 'urgencia': 2}, 'Oxidado': {'tipo': 'Pintura', 'desc': 'Corrosión del sustrato metálico', 'causas': ['Exposición a humedad sin protección', 'Falla en primer anticorrosivo', 'Almacenamiento inadecuado'], 'soluciones': ['Revisar proceso de imprimación y primer', 'Almacenar piezas metálicas en ambiente seco', 'Controlar tiempo entre preparación y pintado'], 'std': 'D', 'urgencia': 5}, 'Desprendimiento de pintura': {'tipo': 'Pintura', 'desc': 'La pintura se desprende en placas', 'causas': ['Falla grave de adherencia', 'Superficie contaminada con desmoldante', 'Curado incompleto'], 'soluciones': ['Verificar promotor en 100% de piezas plásticas', 'Revisar proceso de preparación de superficie', 'Confirmar temperatura y tiempo de curado'], 'std': 'D', 'urgencia': 5}, 'Defecto de pintura': {'tipo': 'Pintura', 'desc': 'Defecto genérico no clasificado', 'causas': ['Condiciones de cabina fuera de rango', 'Insumos con problemas de calidad'], 'soluciones': ['Clasificar el defecto para tomar acción correctiva', 'Revisar condiciones de cabina', 'Verificar calidad del lote en uso'], 'std': 'C', 'urgencia': 2}, 'Pintura contaminada': {'tipo': 'Pintura', 'desc': 'Pintura con partículas extrañas visibles', 'causas': ['Almacenamiento inadecuado', 'Recipientes sucios', 'Pintura vencida'], 'soluciones': ['Colar siempre la pintura antes de aplicar', 'Revisar condiciones de almacenamiento', 'Verificar fecha de vencimiento del lote'], 'std': 'C', 'urgencia': 3}, 'Pintura Levantada': {'tipo': 'Pintura', 'desc': 'La pintura se levanta en burbujas sin desprenderse', 'causas': ['Humedad atrapada debajo de la pintura', 'Temperatura de horno genera vapor', 'Capas muy gruesas'], 'soluciones': ['Sustrato completamente seco antes de pintar', 'Revisar temperatura de curado', 'Respetar tiempos de flash-off'], 'std': 'D', 'urgencia': 4}, 'Contaminado': {'tipo': 'Pintura', 'desc': 'Partículas externas incrustadas en la pintura', 'causas': ['Corrientes de aire con polvo en cabina', 'Personal sin indumentaria adecuada', 'Filtros saturados'], 'soluciones': ['Limpiar cabina al inicio de cada turno', 'Usar indumentaria antiestática', 'Verificar filtros semanalmente'], 'std': 'C', 'urgencia': 3}, 'Golpeado': {'tipo': 'Pintura', 'desc': 'Golpe visible en la pieza pintada', 'causas': ['Impacto durante manipulación post-pintura', 'Transporte sin protección', 'Caída durante proceso'], 'soluciones': ['Mejorar embalaje y protección en transporte', 'Revisar procedimientos de manipulación', 'Establecer almacenamiento temporal acolchado'], 'std': 'D', 'urgencia': 4}, 'Roto': {'tipo': 'Sillas', 'desc': 'Ruptura en estructura, tapizado o espuma del asiento', 'causas': ['Espuma de densidad insuficiente', 'Material de tapizado con baja resistencia', 'Grapas mal colocadas', 'Impacto durante manipulación'], 'soluciones': ['Verificar densidad de espuma mínimo 35 kg/m³', 'Revisar proceso de grapeado y tensado', 'Prueba de carga estática por lote', 'Mejorar embalaje para transporte'], 'std': 'D', 'urgencia': 5}, 'Falta buje': {'tipo': 'Sillas', 'desc': 'Ausencia del buje de sujeción del sillín', 'causas': ['Omisión en proceso de ensamble', 'Error en kit de piezas del proveedor'], 'soluciones': ['Verificación final de componentes antes del empaque', 'Implementar checklist visual por referencia'], 'std': 'D', 'urgencia': 5}, 'Base sillín no conforme': {'tipo': 'Sillas', 'desc': 'Base del sillín fuera de especificaciones', 'causas': ['Molde desgastado o fuera de calibración', 'Material de inyección diferente a especificación'], 'soluciones': ['Verificar dimensiones contra plano aprobado en recepción', 'Solicitar certificado de material por lote'], 'std': 'D', 'urgencia': 4}, 'Desgrapado de Silla': {'tipo': 'Sillas', 'desc': 'Tapizado se desprende por fallas en el grapeado', 'causas': ['Grapas de calibre insuficiente', 'Tensado incorrecto del tapizado', 'Proceso de grapeado sin control'], 'soluciones': ['Estandarizar calibre y tipo de grapa', 'Capacitar en técnica correcta de tensado', 'Prueba de jalado como control en proceso'], 'std': 'D', 'urgencia': 4}, 'Incompleto': {'tipo': 'Sillas', 'desc': 'Sillín con piezas faltantes', 'causas': ['Error en ensamble por omisión', 'Falta de control de piezas al final de línea'], 'soluciones': ['Checklist de componentes por referencia', 'Punto de control visual al final del proceso'], 'std': 'D', 'urgencia': 4}, 'Deforme': {'tipo': 'Sillas', 'desc': 'Forma del sillín diferente a especificación', 'causas': ['Espuma con densidad incorrecta', 'Almacenamiento incorrecto que genera deformación'], 'soluciones': ['Verificar forma contra muestra aprobada por lote', 'Revisar condiciones de almacenamiento'], 'std': 'C', 'urgencia': 3}, 'Ruido interno': {'tipo': 'Sillas', 'desc': 'Ruido o crujido al ejercer presión', 'causas': ['Componentes internos sueltos', 'Espuma que no cubre estructura interna'], 'soluciones': ['Prueba de presión manual en control de recepción', 'Verificar fijación de componentes internos'], 'std': 'C', 'urgencia': 3}, 'Falta platina': {'tipo': 'Sillas', 'desc': 'Ausencia de la platina metálica de sujeción', 'causas': ['Omisión en ensamble', 'Error en kit de componentes'], 'soluciones': ['Verificar componentes metálicos antes del empaque', 'Verificación por peso del conjunto'], 'std': 'D', 'urgencia': 5}, '_process_context': {'batch': {'nombre': 'Por lotes (horno cerrado)', 'riesgos': ['Variación de temperatura entre inicio y final del lote', 'Mayor manejo manual en carga y descarga']}, 'continuo': {'nombre': 'Línea continua (horno abierto)', 'riesgos': ['La puerta siempre abierta puede introducir partículas', 'Cambios de temperatura ambiental afectan el proceso']}}, '_process_recs': {'Grumo': {'batch': 'En proceso por lotes verificar que la temperatura esté estabilizada antes de cargar piezas y colar la pintura antes de cada lote.', 'continuo': 'En línea continua revisar si hay fuentes de polvo cerca de la entrada del túnel y aumentar frecuencia de revisión de filtros.'}, 'Micro hervido': {'batch': 'Revisar la uniformidad de temperatura dentro del horno y la rampa de calentamiento entre ciclos.', 'continuo': 'Verificar el tiempo de tránsito de las piezas por cada zona y que la velocidad de línea permita el aireado correcto.'}, 'Diferente tono': {'batch': 'Los primeros lotes del día pueden tener variación porque el horno no ha estabilizado temperatura. Esperar estabilización antes de producción de primera calidad.', 'continuo': 'Las variaciones aparecen al inicio y final de jornada. Establecer tiempo de estabilización de línea antes de producir.'}, 'Adherencia': {'batch': 'Asegurar que las piezas estén completamente secas antes de cargar el lote. El horno cerrado puede concentrar humedad residual.', 'continuo': 'En días lluviosos en Colombia la humedad que entra por la apertura del túnel puede afectar el curado. Ajustar catalizador en temporada de lluvias.'}, 'Ojo de pez': {'batch': 'Generalmente viene de contaminación en pistola o pintura. Revisar sistema de aire comprimido y limpieza de pistola antes de cada lote.', 'continuo': 'Puede venir de contaminación que entra por la apertura del túnel. Considerar cortina de aire en la entrada.'}, 'Tallado': {'batch': 'El mayor riesgo es en la carga y descarga manual del horno. Implementar protocolo específico con guantes y superficies acolchadas en esos momentos.', 'continuo': 'Revisar todos los puntos de contacto del transportador y protegerlos con materiales blandos.'}}, '_provider_process': {'SERVIPINTARTE': 'batch', 'INTERAUTOS': 'continuo'}}

WEIGHTS = {
    "Tallado":1,"Rayado":2,"Piel naranja":2,"Pintura tallada":2,
    "Diferente tono":2,"Diferente color":3,"Grumo":3,"Micro hervido":3,"Hundido":3,
    "Defecto de pintura":3,"Contaminado":3,"Pintura contaminada":3,"Textura defectuosa":3,
    "Ojo de pez":3,"Pintura chorreada":3,"Pintura Levantada":4,
    "Sin pintar":4,"Faltante de pintura":4,"Faltante":4,
    "Adherencia":5,"Desprendimiento de pintura":5,"Desprendimiento":5,
    "Oxidado":5,"Roto":5,"Reventado":5,"Golpeado":3,"Deforme":4,
    "Base sillín no conforme":4,"Desgrapado de Silla":4,"Incompleto":4,
    "Falta buje":5,"Falta platina":5,"Ruido interno":3,
}
STD = {
    "Adherencia":"D","Desprendimiento de pintura":"D","Desprendimiento":"D",
    "Pintura chorreada":"D","Rayado":"D","Faltante de pintura":"D","Sin pintar":"D",
    "Faltante":"D","Hundido":"D","Roto":"D","Reventado":"D","Diferente tono":"D",
    "Diferente color":"D","Pintura Levantada":"D","Oxidado":"D",
    "Falta buje":"D","Falta platina":"D","Incompleto":"D","Base sillín no conforme":"D",
    "Desgrapado de Silla":"D","Desprendimiento de pintura":"D",
    "Grumo":"C","Micro hervido":"C","Ojo de pez":"C","Piel naranja":"C",
    "Contaminado":"C","Pintura contaminada":"C","Textura defectuosa":"C",
    "Pintura tallada":"C","Defecto de pintura":"C","Deforme":"C","Ruido interno":"C",
    "Tallado":"T","Marca de lija":"T","Mal masillado":"T","Golpeado":"T",
}
PROV_PROCESS = {"SERVIPINTARTE":"batch","INTERAUTOS":"continuo"}
STD_COLORS = {"D":"#c0392b","C":"#c9840a","T":"#2d6b3f"}

MES_ORDER = ["enero","febrero","marzo","abril","mayo","junio",
    "julio","agosto","septiembre","octubre","noviembre","diciembre"]

def sort_mes(m):
    m_lower = str(m).lower()
    yr = next((s for s in str(m).split("-") if s.isdigit() and len(s)==4), "0000")
    mn = next((str(i).zfill(2) for i,n in enumerate(MES_ORDER) if n in m_lower), "99")
    return yr+mn

DB_PATH = "calidad_akt.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS periodos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, fecha_carga TEXT, registros INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo_id INTEGER, mes TEXT, proveedor TEXT,
        damage TEXT, tipo_averia TEXT, articulo TEXT,
        modelo TEXT, cantidad_pnc REAL, criticidad REAL, std TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS acciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo_id INTEGER, proveedor TEXT, defecto TEXT,
        accion TEXT, responsable TEXT, fecha_compromiso TEXT,
        estado TEXT, fecha_creacion TEXT, notas TEXT)""")
    con.commit(); con.close()

def save_periodo(nombre, df):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO periodos (nombre,fecha_carga,registros) VALUES (?,?,?)",
        (nombre, datetime.now().strftime("%Y-%m-%d %H:%M"), len(df)))
    pid = cur.lastrowid
    rows = []
    for _, r in df.iterrows():
        dmg = str(r.get("damage",""))
        pnc = float(r.get("cantidad_pnc",0) or 0)
        rows.append((pid, str(r.get("mes","")), str(r.get("nombre_proveedor","")),
            dmg, str(r.get("tipo_averia","")), str(r.get("articulo","")),
            str(r.get("Modelo","")), pnc, pnc*WEIGHTS.get(dmg,2), STD.get(dmg,"C")))
    cur.executemany("INSERT INTO registros (periodo_id,mes,proveedor,damage,tipo_averia,articulo,modelo,cantidad_pnc,criticidad,std) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()
    return pid

def get_periodos():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM periodos ORDER BY id DESC", con)
    con.close(); return df

def get_data(periodo_ids):
    if not periodo_ids: return pd.DataFrame()
    con = sqlite3.connect(DB_PATH)
    ids = ",".join(str(i) for i in periodo_ids)
    df = pd.read_sql(f"SELECT r.*, p.nombre as periodo_nombre FROM registros r JOIN periodos p ON r.periodo_id=p.id WHERE r.periodo_id IN ({ids})", con)
    con.close(); return df

def save_accion(pid, prov, defecto, accion, responsable, fecha, estado, notas):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO acciones (periodo_id,proveedor,defecto,accion,responsable,fecha_compromiso,estado,fecha_creacion,notas) VALUES (?,?,?,?,?,?,?,?,?)",
        (pid,prov,defecto,accion,responsable,fecha,estado,datetime.now().strftime("%Y-%m-%d"),notas))
    con.commit(); con.close()

def get_acciones(proveedor=None):
    con = sqlite3.connect(DB_PATH)
    q = "SELECT a.*, p.nombre as periodo_nombre FROM acciones a JOIN periodos p ON a.periodo_id=p.id"
    if proveedor: q += f" WHERE a.proveedor='{proveedor}'"
    df = pd.read_sql(q+" ORDER BY a.id DESC", con); con.close(); return df

def update_accion(accion_id, estado, notas=""):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE acciones SET estado=?,notas=? WHERE id=?",(estado,notas,accion_id))
    con.commit(); con.close()

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.main-title{font-family:'DM Serif Display',serif;font-size:1.9rem;color:#0f2718}
.kpi-card{background:#fff;border-radius:10px;padding:18px 20px;border:1px solid #f0ece2;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.kpi-val{font-family:'DM Serif Display',serif;font-size:1.8rem;color:#0f2718;line-height:1}
.kpi-lbl{font-size:.72rem;color:#8a9e8e;text-transform:uppercase;letter-spacing:.08em;margin-top:4px}
.sec-title{font-family:'DM Serif Display',serif;font-size:1.1rem;color:#0f2718;margin:1.2rem 0 .6rem}
.alert-reinc{background:#fdf0ef;border-left:4px solid #c0392b;padding:12px 16px;border-radius:0 8px 8px 0;margin:6px 0;font-size:.86rem}
.ac-pend{background:#fef9ed;border-left:3px solid #c9840a;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0}
.ac-done{background:#e8f5ec;border-left:3px solid #2d6b3f;padding:10px 14px;border-radius:0 8px 8px 0;margin:4px 0}
.rec-D{background:#fdf0ef;border-left:3px solid #c0392b;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
.rec-C{background:#fef9ed;border-left:3px solid #c9840a;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
.rec-T{background:#e8f5ec;border-left:3px solid #2d6b3f;padding:12px 16px;border-radius:0 8px 8px 0;margin:5px 0}
</style>""", unsafe_allow_html=True)

init_db()

# SIDEBAR
with st.sidebar:
    st.markdown("### 🏍 AKT Motos")
    st.markdown("**Análisis de Calidad**")
    st.divider()
    st.markdown("#### Cargar datos")
    uploaded = st.file_uploader("Master de averías (.xlsx)", type=["xlsx","xls"])
    if uploaded:
        nombre = st.text_input("Nombre del período", placeholder="Ej: Q1 2026")
        if st.button("💾 Guardar período", use_container_width=True):
            if not nombre:
                st.error("Escribe un nombre")
            else:
                with st.spinner("Procesando..."):
                    df_raw = pd.read_excel(uploaded, sheet_name="Datos")
                    # Normalize column names
                    df_raw.columns = [c.strip() for c in df_raw.columns]
                    if 'Modelo' in df_raw.columns: df_raw['modelo'] = df_raw['Modelo']
                    df_raw["cantidad_pnc"] = pd.to_numeric(df_raw.get("cantidad_pnc",0), errors="coerce").fillna(0)
                    save_periodo(nombre, df_raw)
                    st.success(f"✅ {nombre} guardado")
                    st.rerun()
    st.divider()
    periodos_df = get_periodos()
    if len(periodos_df)==0:
        st.info("Sube un master para comenzar")
        st.stop()
    periodo_options = {r["nombre"]:r["id"] for _,r in periodos_df.iterrows()}
    selected = st.multiselect("Períodos a analizar",
        list(periodo_options.keys()),
        default=[list(periodo_options.keys())[0]])
    if not selected:
        st.warning("Selecciona al menos un período")
        st.stop()
    selected_ids = [periodo_options[p] for p in selected]
    st.divider()
    st.caption("Área de Desarrollo de Producto")
    st.caption("Valentina Perdomo Perdomo")

df = get_data(selected_ids)
if df.empty:
    st.warning("Sin datos"); st.stop()
df["cantidad_pnc"] = pd.to_numeric(df["cantidad_pnc"],errors="coerce").fillna(0)
df["criticidad"]   = pd.to_numeric(df["criticidad"],errors="coerce").fillna(0)
periodo_label = " + ".join(selected)

st.markdown(f'<div class="main-title">🏍 Análisis de Calidad — AKT Motos</div>', unsafe_allow_html=True)
st.markdown(f"**Período:** {periodo_label} · {len(df):,} registros · {df['proveedor'].nunique()} proveedores")
st.markdown("")

tabs = st.tabs(["📊 Resumen","🏭 Por proveedor","🔍 Por defecto","🔧 Por pieza","📈 Comparar","✅ Acciones"])
tab_res, tab_prov, tab_def, tab_pie, tab_comp, tab_acc = tabs

# ── TAB RESUMEN ──────────────────────────────────────────────
with tab_res:
    total = df["cantidad_pnc"].sum()
    pnc_D = df[df["std"]=="D"]["cantidad_pnc"].sum()
    pnc_C = df[df["std"]=="C"]["cantidad_pnc"].sum()
    pnc_T = df[df["std"]=="T"]["cantidad_pnc"].sum()
    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl in [
        (c1,f"{total:,.0f}","PNC Totales"),
        (c2,f"{pnc_D:,.0f}","Devolución directa"),
        (c3,f"{pnc_C:,.0f}","Condicional"),
        (c4,str(df["proveedor"].nunique()),"Proveedores")
    ]:
        col.markdown(f'<div class="kpi-card"><div class="kpi-val">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("")
    l, r = st.columns(2)
    with l:
        st.markdown('<div class="sec-title">PNC por proveedor</div>', unsafe_allow_html=True)
        pp = df.groupby("proveedor")["cantidad_pnc"].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(pp,x="cantidad_pnc",y="proveedor",orientation="h",
            color="cantidad_pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
            labels={"cantidad_pnc":"PNC","proveedor":""},height=280)
        fig.update_layout(showlegend=False,margin=dict(l=0,r=0,t=5,b=0),
            plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
        st.plotly_chart(fig,use_container_width=True)
    with r:
        st.markdown('<div class="sec-title">Distribución STD-001</div>', unsafe_allow_html=True)
        sd = pd.DataFrame({"Tipo":["Devolución directa","Condicional","Tolerable"],"PNC":[pnc_D,pnc_C,pnc_T]})
        fig2 = px.pie(sd,values="PNC",names="Tipo",height=280,
            color="Tipo",color_discrete_map={"Devolución directa":"#c0392b","Condicional":"#c9840a","Tolerable":"#2d6b3f"})
        fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),paper_bgcolor="white")
        st.plotly_chart(fig2,use_container_width=True)

    st.markdown('<div class="sec-title">Tendencia mensual por proveedor</div>', unsafe_allow_html=True)
    mt = df.groupby(["mes","proveedor"])["cantidad_pnc"].sum().reset_index()
    if not mt.empty:
        mt["_sort"] = mt["mes"].apply(sort_mes)
        mt = mt.sort_values("_sort").drop(columns=["_sort"])
        fig3 = px.line(mt,x="mes",y="cantidad_pnc",color="proveedor",markers=True,
            labels={"cantidad_pnc":"PNC","mes":"Mes","proveedor":"Proveedor"},height=280,
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig3.update_layout(margin=dict(l=0,r=0,t=5,b=0),
            plot_bgcolor="white",paper_bgcolor="white",xaxis=dict(tickangle=-45))
        st.plotly_chart(fig3,use_container_width=True)

    if len(selected_ids)>1:
        st.markdown('<div class="sec-title">⚠️ Alertas de reincidencia entre períodos</div>', unsafe_allow_html=True)
        per = df.groupby(["periodo_nombre","proveedor","damage"])["cantidad_pnc"].sum().reset_index()
        reinc = per.groupby(["proveedor","damage"]).filter(lambda x: len(x)>=2)
        if not reinc.empty:
            for _, rw in reinc.groupby(["proveedor","damage"])["cantidad_pnc"].sum().sort_values(ascending=False).head(5).reset_index().iterrows():
                s = STD.get(rw["damage"],"C")
                icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
                st.markdown(f'<div class="alert-reinc">{icon} <strong>{rw["proveedor"]}</strong> — <strong>{rw["damage"]}</strong> aparece como crítico en {len(selected)} períodos consecutivos con {rw["cantidad_pnc"]:,.0f} PNC acumulados. Las acciones previas pueden no haber sido suficientes.</div>', unsafe_allow_html=True)
        else:
            st.success("✅ Sin defectos reincidentes entre los períodos seleccionados")

# ── TAB PROVEEDOR ────────────────────────────────────────────
with tab_prov:
    provs = sorted(df["proveedor"].unique())
    col1,col2,col3 = st.columns(3)
    prov_sel = col1.selectbox("Proveedor", provs)
    tipos = ["Todos"] + sorted(df["tipo_averia"].dropna().unique().tolist())
    tipo_sel = col2.selectbox("Tipo avería", tipos)
    std_sel = col3.selectbox("STD-001", ["Todos","D — Devolución","C — Condicional","T — Tolerable"])

    dfp = df[df["proveedor"]==prov_sel].copy()
    if tipo_sel!="Todos": dfp = dfp[dfp["tipo_averia"]==tipo_sel]
    if std_sel!="Todos": dfp = dfp[dfp["std"]==std_sel[0]]

    if dfp.empty:
        st.info("Sin datos para esta combinación")
    else:
        tot = dfp["cantidad_pnc"].sum()
        avg = dfp.groupby("mes")["cantidad_pnc"].sum().mean()
        pctD = dfp[dfp["std"]=="D"]["cantidad_pnc"].sum()/tot*100 if tot else 0
        proc = PROV_PROCESS.get(prov_sel)
        proc_lbl = "Por lotes" if proc=="batch" else "Línea continua" if proc=="continuo" else "—"

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("PNC Totales",f"{tot:,.0f}")
        k2.metric("Promedio mensual",f"{avg:,.0f}")
        k3.metric("% Devolución directa",f"{pctD:.0f}%")
        k4.metric("Tipo de proceso", proc_lbl)

        l2,r2 = st.columns(2)
        with l2:
            st.markdown('<div class="sec-title">Top defectos por criticidad</div>', unsafe_allow_html=True)
            td = dfp.groupby(["damage","std"]).agg(pnc=("cantidad_pnc","sum"),crit=("criticidad","sum")).sort_values("crit",ascending=False).head(8).reset_index()
            fig = px.bar(td,x="pnc",y="damage",orientation="h",color="std",
                color_discrete_map=STD_COLORS,
                labels={"pnc":"PNC","damage":"","std":"STD"},height=300)
            fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)
        with r2:
            st.markdown('<div class="sec-title">Top piezas críticas</div>', unsafe_allow_html=True)
            tp = dfp.groupby("articulo").agg(pnc=("cantidad_pnc","sum")).sort_values("pnc",ascending=False).head(8).reset_index()
            fig2 = px.bar(tp,x="pnc",y="articulo",orientation="h",
                color="pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
                labels={"pnc":"PNC","articulo":""},height=300)
            fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
            st.plotly_chart(fig2,use_container_width=True)

        st.markdown('<div class="sec-title">Tendencia mensual</div>', unsafe_allow_html=True)
        md = dfp.groupby("mes")["cantidad_pnc"].sum().reset_index()
        md["_sort"] = md["mes"].apply(sort_mes)
        md = md.sort_values("_sort").drop(columns=["_sort"])
        avg_v = md["cantidad_pnc"].mean()
        md["Estado"] = md["cantidad_pnc"].apply(lambda v:"Anómalo (+30%)" if v>avg_v*1.3 else "Sobre promedio" if v>avg_v else "Normal")
        fig3 = px.bar(md,x="mes",y="cantidad_pnc",color="Estado",
            color_discrete_map={"Normal":"#52b06b","Sobre promedio":"#c9840a","Anómalo (+30%)":"#c0392b"},
            labels={"cantidad_pnc":"PNC","mes":""},height=260)
        fig3.add_hline(y=avg_v,line_dash="dot",line_color="#888",annotation_text=f"Prom: {avg_v:.0f}")
        fig3.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",xaxis=dict(tickangle=-45))
        st.plotly_chart(fig3,use_container_width=True)

        st.markdown('<div class="sec-title">💡 Recomendaciones según datos y proceso</div>', unsafe_allow_html=True)
        for _, rw in td.head(4).iterrows():
            kbE = KB.get(rw["damage"],{})
            s = rw["std"]
            causas = kbE.get("causas",[])
            sols = kbE.get("soluciones",[])
            proc_recs = KB.get("_process_recs",{}).get(rw["damage"],{})
            proc_rec = proc_recs.get(proc,"") if proc else ""
            col_note = kbE.get("colombia_note","")
            icon = "🔴" if s=="D" else "🟡" if s=="C" else "🟢"
            std_lbl = "Devolución directa" if s=="D" else "Condicional" if s=="C" else "Tolerable"
            txt = f"{rw['pnc']:,.0f} PNC · {std_lbl}. "
            if causas: txt += f"Causa frecuente: {causas[0]}. "
            if sols: txt += f"Se recomienda: {sols[0]}. "
            if proc_rec: txt += f"Para {proc_lbl.lower()}: {proc_rec} "
            if col_note: txt += f"Nota Colombia: {col_note}"
            st.markdown(f'<div class="rec-{s}">{icon} <strong>{rw["damage"]}</strong><br><span style="font-size:.83rem">{txt}</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-title">Tabla de trazabilidad</div>', unsafe_allow_html=True)
        tbl = dfp.groupby(["damage","std","articulo"]).agg(PNC=("cantidad_pnc","sum"),Crit=("criticidad","sum")).sort_values("Crit",ascending=False).reset_index()
        tbl["STD"] = tbl["std"].map({"D":"🔴 Dev.","C":"🟡 Cond.","T":"🟢 Tol."})
        tbl = tbl[["damage","STD","articulo","PNC","Crit"]].rename(columns={"damage":"Defecto","articulo":"Pieza","Crit":"Criticidad"})
        tbl["PNC"] = tbl["PNC"].apply(lambda x:f"{x:,.0f}")
        tbl["Criticidad"] = tbl["Criticidad"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(tbl,use_container_width=True,hide_index=True)

# ── TAB DEFECTO ──────────────────────────────────────────────
with tab_def:
    c1,c2 = st.columns(2)
    dmg_sel = c1.selectbox("Defecto",["Todos"]+sorted(df["damage"].dropna().unique().tolist()))
    std_f   = c2.selectbox("STD-001",["Todos","D — Devolución","C — Condicional","T — Tolerable"],key="std_d")

    dfd = df.copy()
    if dmg_sel!="Todos": dfd = dfd[dfd["damage"]==dmg_sel]
    if std_f!="Todos": dfd = dfd[dfd["std"]==std_f[0]]

    if not dfd.empty:
        if dmg_sel!="Todos":
            kbE = KB.get(dmg_sel,{})
            if kbE:
                s = STD.get(dmg_sel,"C")
                border = "#c0392b" if s=="D" else "#c9840a" if s=="C" else "#2d6b3f"
                bg = "#fdf0ef" if s=="D" else "#fef9ed" if s=="C" else "#e8f5ec"
                causas_txt = "; ".join(kbE.get("causas",[])[:3])
                st.markdown(f'<div style="background:{bg};border-left:4px solid {border};padding:12px 16px;border-radius:0 10px 10px 0;margin-bottom:12px"><strong>{dmg_sel}</strong> — {kbE.get("desc","")}<br><span style="font-size:.82rem;color:#555">Causas: {causas_txt}</span></div>', unsafe_allow_html=True)

        l3,r3 = st.columns(2)
        with l3:
            st.markdown('<div class="sec-title">Por proveedor</div>', unsafe_allow_html=True)
            bp = dfd.groupby("proveedor")["cantidad_pnc"].sum().sort_values(ascending=False).reset_index()
            fig = px.bar(bp,x="proveedor",y="cantidad_pnc",
                color="cantidad_pnc",color_continuous_scale=["#e8f5ec","#0f2718"],
                labels={"cantidad_pnc":"PNC","proveedor":""},height=260)
            fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white",coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
        with r3:
            st.markdown('<div class="sec-title">Por modelo</div>', unsafe_allow_html=True)
            bm = dfd.groupby("modelo")["cantidad_pnc"].sum().sort_values(ascending=False).head(8).reset_index()
            fig2 = px.bar(bm,x="cantidad_pnc",y="modelo",orientation="h",
                color_discrete_sequence=["#3a8a51"],labels={"cantidad_pnc":"PNC","modelo":""},height=260)
            fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig2,use_container_width=True)

        st.markdown('<div class="sec-title">Trazabilidad por pieza y proveedor</div>', unsafe_allow_html=True)
        tbl2 = dfd.groupby(["proveedor","damage","articulo","std"]).agg(PNC=("cantidad_pnc","sum"),Crit=("criticidad","sum")).sort_values("Crit",ascending=False).reset_index()
        tbl2["STD"] = tbl2["std"].map({"D":"🔴 Dev.","C":"🟡 Cond.","T":"🟢 Tol."})
        tbl2 = tbl2[["proveedor","damage","articulo","STD","PNC","Crit"]].rename(columns={"proveedor":"Proveedor","damage":"Defecto","articulo":"Pieza","Crit":"Criticidad"})
        tbl2["PNC"] = tbl2["PNC"].apply(lambda x:f"{x:,.0f}")
        tbl2["Criticidad"] = tbl2["Criticidad"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(tbl2,use_container_width=True,hide_index=True)

# ── TAB PIEZA ────────────────────────────────────────────────
with tab_pie:
    c1,c2 = st.columns(2)
    prov_p = c1.selectbox("Proveedor",["Todos"]+sorted(df["proveedor"].unique().tolist()),key="prov_p")
    sort_p = c2.selectbox("Ordenar por",["Criticidad","PNC total","Devoluciones directas"])

    dfpi = df.copy()
    if prov_p!="Todos": dfpi = dfpi[dfpi["proveedor"]==prov_p]

    if not dfpi.empty:
        agg = dfpi.groupby(["articulo","proveedor"]).apply(lambda x: pd.Series({
            "PNC":x["cantidad_pnc"].sum(),
            "Criticidad":x["criticidad"].sum(),
            "Dev_D":x[x["std"]=="D"]["cantidad_pnc"].sum(),
            "Top_defecto": x.groupby("damage")["cantidad_pnc"].sum().idxmax() if len(x)>0 else ""
        })).reset_index()

        if sort_p=="Criticidad": agg = agg.sort_values("Criticidad",ascending=False)
        elif sort_p=="PNC total": agg = agg.sort_values("PNC",ascending=False)
        else: agg = agg.sort_values("Dev_D",ascending=False)
        agg = agg.head(15)

        fig = px.bar(agg,x="Criticidad",y="articulo",orientation="h",color="proveedor",
            labels={"Criticidad":"Índice Criticidad","articulo":""},height=480,
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

        show = agg.copy()
        show["PNC"] = show["PNC"].apply(lambda x:f"{x:,.0f}")
        show["Criticidad"] = show["Criticidad"].apply(lambda x:f"{x:,.0f}")
        show["Dev. Directas"] = show["Dev_D"].apply(lambda x:f"{x:,.0f}")
        st.dataframe(show[["articulo","proveedor","PNC","Dev. Directas","Criticidad","Top_defecto"]].rename(columns={"articulo":"Pieza","proveedor":"Proveedor","Top_defecto":"Defecto principal"}),use_container_width=True,hide_index=True)

# ── TAB COMPARAR ─────────────────────────────────────────────
with tab_comp:
    if len(selected_ids)<2:
        st.info("Selecciona al menos 2 períodos en el panel izquierdo para comparar")
    else:
        st.markdown('<div class="sec-title">PNC por proveedor — comparativo entre períodos</div>', unsafe_allow_html=True)
        comp = df.groupby(["periodo_nombre","proveedor"])["cantidad_pnc"].sum().reset_index()
        fig = px.bar(comp,x="proveedor",y="cantidad_pnc",color="periodo_nombre",barmode="group",
            labels={"cantidad_pnc":"PNC","proveedor":"Proveedor","periodo_nombre":"Período"},height=320,
            color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

        st.markdown('<div class="sec-title">Evolución de defectos de devolución directa</div>', unsafe_allow_html=True)
        top5D = df[df["std"]=="D"].groupby("damage")["cantidad_pnc"].sum().nlargest(5).index.tolist()
        cd = df[df["damage"].isin(top5D)].groupby(["periodo_nombre","damage"])["cantidad_pnc"].sum().reset_index()
        fig2 = px.line(cd,x="periodo_nombre",y="cantidad_pnc",color="damage",markers=True,
            labels={"cantidad_pnc":"PNC","periodo_nombre":"Período","damage":"Defecto"},height=280,
            color_discrete_sequence=px.colors.qualitative.Set1)
        fig2.update_layout(margin=dict(l=0,r=0,t=5,b=0),plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig2,use_container_width=True)

        st.markdown('<div class="sec-title">Tabla comparativa</div>', unsafe_allow_html=True)
        pivot = comp.pivot(index="proveedor",columns="periodo_nombre",values="cantidad_pnc").reset_index()
        pivot.columns.name = None
        st.dataframe(pivot,use_container_width=True,hide_index=True)

# ── TAB ACCIONES ─────────────────────────────────────────────
with tab_acc:
    st.markdown('<div class="sec-title">Registrar nueva acción</div>', unsafe_allow_html=True)
    with st.form("form_acc"):
        fa1,fa2 = st.columns(2)
        with fa1:
            ac_per  = fa1.selectbox("Período", list(periodo_options.keys()))
            ac_prov = fa1.selectbox("Proveedor", sorted(df["proveedor"].unique()))
            ac_dmg  = fa1.selectbox("Defecto", ["—"]+sorted(df["damage"].dropna().unique().tolist()))
        with fa2:
            ac_resp  = fa2.text_input("Responsable")
            ac_fecha = fa2.date_input("Fecha de compromiso")
            ac_est   = fa2.selectbox("Estado",["Pendiente","En proceso","Completada","Cancelada"])
        ac_acc  = st.text_area("Acción", height=70)
        ac_nota = st.text_area("Notas", height=50)
        if st.form_submit_button("💾 Guardar",use_container_width=True) and ac_acc:
            save_accion(periodo_options[ac_per],ac_prov,
                ac_dmg if ac_dmg!="—" else "",
                ac_acc,ac_resp,str(ac_fecha),ac_est,ac_nota)
            st.success("✅ Acción guardada"); st.rerun()

    st.markdown('<div class="sec-title">Seguimiento de acciones</div>', unsafe_allow_html=True)
    ff1,ff2 = st.columns(2)
    fil_prov = ff1.selectbox("Proveedor",["Todos"]+sorted(df["proveedor"].unique().tolist()),key="fil_p")
    fil_est  = ff2.selectbox("Estado",["Todos","Pendiente","En proceso","Completada","Cancelada"])

    acc_df = get_acciones(fil_prov if fil_prov!="Todos" else None)
    if fil_est!="Todos": acc_df = acc_df[acc_df["estado"]==fil_est]

    if acc_df.empty:
        st.info("Sin acciones registradas")
    else:
        for _,ac in acc_df.iterrows():
            est = ac["estado"]
            css = "ac-done" if est=="Completada" else "ac-pend"
            icon = {"Pendiente":"⏳","En proceso":"🔄","Completada":"✅","Cancelada":"❌"}.get(est,"⏳")
            st.markdown(f'<div class="{css}"><strong>{icon} {ac["proveedor"]}</strong> — {ac["defecto"] or "General"} <span style="float:right;font-size:.75rem;color:#888">{ac["fecha_creacion"]} · {ac["periodo_nombre"]}</span><br><span style="font-size:.85rem">{ac["accion"]}</span><br><span style="font-size:.75rem;color:#666">Resp: {ac["responsable"] or "—"} · Compromiso: {ac["fecha_compromiso"] or "—"} · {est}</span></div>', unsafe_allow_html=True)
            if est not in ["Completada","Cancelada"]:
                b1,b2,_ = st.columns([1,1,4])
                if b1.button("✅ Completar",key=f"c{ac['id']}"):
                    update_accion(ac["id"],"Completada"); st.rerun()
                if b2.button("🔄 En proceso",key=f"p{ac['id']}"):
                    update_accion(ac["id"],"En proceso"); st.rerun()
