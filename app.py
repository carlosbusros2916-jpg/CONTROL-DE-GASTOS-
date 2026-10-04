import streamlit as st
import sqlite3
from datetime import date
import pandas as pd
import io
import hashlib
import plotly.express as px

DB = "finbot.db"

def conectar():
    return sqlite3.connect(DB)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def iniciar_db():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT,
            valor REAL NOT NULL,
            etiqueta TEXT DEFAULT 'Necesario'
        )
    """)
    try:
        cursor.execute("ALTER TABLE movimientos ADD COLUMN usuario_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            usuario_id INTEGER PRIMARY KEY,
            presupuesto_mensual REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            monto_objetivo REAL NOT NULL,
            monto_actual REAL DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ahorros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            capital_actual REAL NOT NULL,
            tasa_ea REAL NOT NULL,
            aporte_mensual REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

iniciar_db()

# Configuración de página optimizada
st.set_page_config(page_title="FinBot Pro", page_icon="💳", layout="centered")

# ==========================================
# ESTILOS CSS PERSONALIZADOS (Look App Móvil)
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    div.stMetric, .card {
        background-color: #1e293b;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    h1, h2, h3 {
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        border-color: transparent;
    }
    
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #1e293b;
        color: white;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GESTIÓN DE AUTENTICACIÓN MULTI-USUARIO
# ==========================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

if st.session_state.user_id is None:
    st.title("💳 FinBot Pro - Acceso Inteligente")
    st.markdown("<p style='color: #94a3b8; margin-top: -15px;'>Tu plataforma financiera personal en la nube</p>", unsafe_allow_html=True)
    
    tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab_login:
        with st.form("form_login"):
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Ingresar a mi Cuenta")
            
            if btn_login:
                conn = conectar()
                user_db = conn.execute("SELECT id, usuario, password FROM usuarios WHERE usuario = ?", (user_input.strip(),)).fetchone()
                conn.close()
                
                if user_db and user_db[2] == hash_password(pass_input):
                    st.session_state.user_id = user_db[0]
                    st.session_state.user_name = user_db[1]
                    st.success("¡Bienvenido de nuevo!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
                    
    with tab_registro:
        with st.form("form_registro"):
            nuevo_user = st.text_input("Elige tu usuario único")
            nuevo_pass = st.text_input("Elige tu contraseña", type="password")
            btn_reg = st.form_submit_button("Crear Cuenta Gratis")
            
            if btn_reg:
                if nuevo_user and nuevo_pass:
                    try:
                        conn = conectar()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)", (nuevo_user.strip(), hash_password(nuevo_pass)))
                        conn.commit()
                        nuevo_id = cursor.lastrowid
                        conn.close()
                        
                        st.session_state.user_id = nuevo_id
                        st.session_state.user_name = nuevo_user.strip()
                        st.success("¡Cuenta creada con éxito!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya está en uso. Elige otro.")
                else:
                    st.error("Por favor completa todos los campos.")
    st.stop()

# ==========================================
# APLICACIÓN PRINCIPAL (POST-LOGIN)
# ==========================================
st.title(f"💳 FinBot Pro")
st.markdown(f"<p style='color: #94a3b8; margin-top: -15px;'>Hola, <b>{st.session_state.user_name}</b>. Control financiero profesional.</p>", unsafe_allow_html=True)

menu = st.sidebar.selectbox(
    "Navegación",
    [
        "🏠 Dashboard",
        "📤 Nuevo Registro",
        "🎯 Metas & Presupuesto",
        "📂 Reportes & Excel",
        "💡 Consejos IA"
    ]
)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.rerun()

def dinero(valor):
    return f"${int(valor):,}".replace(",", ".")

def clasificar_automatico(desc):
    desc = desc.lower()
    if any(p in desc for p in ["uber", "taxi", "bus", "gasolina", "transporte", "peaje", "metro"]):
        return "Transporte / Gasolina", "Necesario (Bueno)"
    elif any(p in desc for p in ["exito", "d1", "carulla", "ara", "supermercado", "mercado", "comida", "almuerzo", "restaurante", "rappi"]):
        return "Comida / Mercado", "Necesario (Bueno)"
    elif any(p in desc for p in ["netflix", "spotify", "cine", "salida", "cerveza", "fiesta", "juego"]):
        return "Ocio / Salidas", "Innecesario / Hormiga (Evitable)"
    return "Otros", "Necesario (Bueno)"

UID = st.session_state.user_id

# ==========================================
# 1. DASHBOARD
# ==========================================
if menu == "🏠 Dashboard":
    st.markdown("### 📊 Resumen Financiero")
    
    conn = conectar()
    ingresos = conn.execute("SELECT COALESCE(SUM(valor),0) FROM movimientos WHERE usuario_id = ? AND tipo = 'INGRESO'", (UID,)).fetchone()[0]
    gastos = conn.execute("SELECT COALESCE(SUM(valor),0) FROM movimientos WHERE usuario_id = ? AND tipo = 'GASTO'", (UID,)).fetchone()[0]
    presupuesto_row = conn.execute("SELECT presupuesto_mensual FROM configuracion WHERE usuario_id = ?", (UID,)).fetchone()
    presupuesto = presupuesto_row[0] if presupuesto_row else 0
    conn.close()
    
    saldo = ingresos - gastos
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos", dinero(ingresos))
    col2.metric("Gastos", dinero(gastos))
    col3.metric("Disponible", dinero(saldo))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if presupuesto > 0:
        st.markdown("### 🎯 Progreso de Presupuesto")
        porcentaje_gasto = min(gastos / presupuesto, 1.0)
        st.progress(porcentaje_gasto)
        if gastos > presupuesto:
            st.error(f"⚠️ Alerta: Te pasaste del presupuesto por {dinero(gastos - presupuesto)}")
        else:
            st.success(f"✅ Vas muy bien. Te quedan {dinero(presupuesto - gastos)} disponibles.")
    
    st.markdown("---")
    st.markdown("### 🍩 Distribución de Gastos (Gráfico Profesional)")
    conn = conectar()
    df_gastos = pd.read_sql("SELECT categoria, SUM(valor) as total FROM movimientos WHERE usuario_id = ? AND tipo='GASTO' GROUP BY categoria", conn, params=(UID,))
    conn.close()
    
    if not df_gastos.empty:
        # Gráfico de torta/dona interactivo y moderno con Plotly
        fig = px.pie(
            df_gastos, 
            names='categoria', 
            values='total', 
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig.update_layout(
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            font_color="#f8fafc",
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("💡 Registra algunos gastos para ver tu gráfico de torta profesional.")

# ==========================================
# 2. NUEVO REGISTRO
# ==========================================
elif menu == "📤 Nuevo Registro":
    st.markdown("### 📝 Registrar Movimiento")
    
    tipo = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("form_movimiento"):
        valor_texto = st.text_input("Valor en COP ($)", placeholder="Ej: 2.300.000 o 50000")
        descripcion = st.text_input("Descripción (Ej: Uber al trabajo, Mercado en D1)")
        
        if tipo == "GASTO":
            categoria = st.selectbox("Categoría", ["Comida / Mercado", "Transporte / Gasolina", "Arriendo / Servicios", "Ocio / Salidas", "Gastos Hormiga", "Otros"])
            etiqueta = st.selectbox("Clasificación", ["Necesario (Bueno)", "Innecesario / Hormiga (Evitable)"])
        else:
            categoria = "Ingreso"
            etiqueta = "Necesario (Bueno)"
            
        fecha = st.date_input("Fecha", value=date.today())
        
        submitted = st.form_submit_button("Guardar Movimiento")
        
        valor = 0.0
        if valor_texto:
            try:
                limpio = valor_texto.replace(".", "").replace(",", "").replace("$", "").strip()
                valor = float(limpio)
            except ValueError:
                valor = 0.0

        if submitted:
            if valor > 0:
                cat_final, etiqueta_final = categoria, etiqueta
                if descripcion and tipo == "GASTO" and categoria == "Otros":
                    cat_final, etiqueta_final = clasificar_automatico(descripcion)

                conn = conectar()
                conn.execute("INSERT INTO movimientos (usuario_id, fecha, tipo, categoria, descripcion, valor, etiqueta) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (UID, str(fecha), tipo, cat_final, descripcion, valor, etiqueta_final))
                conn.commit()
                conn.close()
                st.success(f"¡Guardado correctamente! ({cat_final} - {dinero(valor)})")
            else:
                st.error("Por favor ingresa un valor válido.")

# ==========================================
# 3. METAS, PRESUPUESTO Y AHORROS CON PROYECCIÓN
# ==========================================
elif menu == "🎯 Metas & Presupuesto":
    st.markdown("### 💰 Mis Ahorros e Intereses (Proyección a Diciembre)")
    
    with st.form("form_ahorro"):
        nombre_ahorro = st.text_input("Nombre de la cuenta o fondo (Ej: Cuenta Nu, CDT)")
        capital_texto = st.text_input("Dinero que tienes ahorrado actualmente ($)", placeholder="Ej: 3.500.000")
        tasa_texto = st.text_input("Tasa Efectiva Anual (E.A.) %", placeholder="Ej: 13.0")
        aporte_mes_texto = st.text_input("Aporte mensual planeado ($)", placeholder="Ej: 300.000")
        
        guardar_ahorro = st.form_submit_button("Guardar y Calcular Proyección")
        
        cap, tasa, aporte = 0.0, 0.0, 0.0
        if capital_texto:
            try: cap = float(capital_texto.replace(".", "").replace(",", "").replace("$", "").strip())
            except ValueError: cap = 0.0
        if tasa_texto:
            try: tasa = float(tasa_texto.replace(",", ".").replace("%", "").strip())
            except ValueError: tasa = 0.0
        if aporte_mes_texto:
            try: aporte = float(aporte_mes_texto.replace(".", "").replace(",", "").replace("$", "").strip())
            except ValueError: aporte = 0.0

        if guardar_ahorro and nombre_ahorro and cap >= 0:
            conn = conectar()
            conn.execute("INSERT INTO ahorros (usuario_id, nombre, capital_actual, tasa_ea, aporte_mensual) VALUES (?, ?, ?, ?, ?)", 
                         (UID, nombre_ahorro, cap, tasa, aporte))
            conn.commit()
            conn.close()
            st.success("¡Ahorro registrado con éxito!")

    st.markdown("---")
    st.markdown("### 📈 Proyecciones Actuales al 31 de Diciembre")
    
    conn = conectar()
    ahorros_list = conn.execute("SELECT id, nombre, capital_actual, tasa_ea, aporte_mensual FROM ahorros WHERE usuario_id = ?", (UID,)).fetchall()
    conn.close()
    
    if ahorros_list:
        hoy = date.today()
        meses_hasta_dic = max(0, 12 - hoy.month)
        if meses_hasta_dic == 0:
            meses_hasta_dic = 1
            
        for a_id, a_nom, a_cap, a_tasa, a_aporte in ahorros_list:
            tasa_mensual = ((1 + (a_tasa / 100.0)) ** (1/12)) - 1
            
            proyectado = a_cap
            for _ in range(meses_hasta_dic):
                proyectado = (proyectado + a_aporte) * (1 + tasa_mensual)
                
            interes_ganado = proyectado - a_cap - (a_aporte * meses_hasta_dic)
            
            st.markdown(f"#### 🔹 {a_nom}")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Actual", dinero(a_cap))
            col_b.metric("Proyectado 31 Dic", dinero(proyectado))
            col_c.metric("Intereses Estimados", dinero(interes_ganado))
            
            if st.button(f"🗑️ Eliminar '{a_nom}'", key=f"del_ah_{a_id}"):
                conn = conectar()
                conn.execute("DELETE FROM ahorros WHERE id = ? AND usuario_id = ?", (a_id, UID))
                conn.commit()
                conn.close()
                st.success("¡Eliminado!")
                st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No tienes cuentas de ahorro registradas.")

    st.markdown("---")
    st.markdown("### 🎯 Metas de Ahorro")
    with st.form("form_meta"):
        nombre_meta = st.text_input("Nombre de Meta (Ej: Fondo de Emergencia, Moto)")
        monto_obj_texto = st.text_input("Meta Objetivo ($)", placeholder="Ej: 1.500.000")
        crear_meta = st.form_submit_button("Crear Meta")
        
        monto_obj = 0.0
        if monto_obj_texto:
            try:
                monto_obj = float(monto_obj_texto.replace(".", "").replace(",", "").replace("$", "").strip())
            except ValueError:
                monto_obj = 0.0

        if crear_meta and nombre_meta and monto_obj > 0:
            conn = conectar()
            conn.execute("INSERT INTO metas (usuario_id, nombre, monto_objetivo, monto_actual) VALUES (?, ?, ?, 0)", (UID, nombre_meta, monto_obj))
            conn.commit()
            conn.close()
            st.success("¡Meta creada con éxito!")

    st.markdown("### 📌 Tus Metas Activas")
    conn = conectar()
    metas = conn.execute("SELECT id, nombre, monto_objetivo, monto_actual FROM metas WHERE usuario_id = ?", (UID,)).fetchall()
    conn.close()
    
    if metas:
        for m_id, m_nombre, m_obj, m_act in metas:
            st.write(f"**{m_nombre}**: {dinero(m_act)} / {dinero(m_obj)}")
            st.progress(min(m_act / m_obj, 1.0) if m_obj > 0 else 0)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                abono_texto = st.text_input(f"Abonar a {m_nombre}", placeholder="Ej: 50.000", key=f"ab_{m_id}")
            with c2:
                if st.button("Abonar", key=f"btn_{m_id}"):
                    abono = 0.0
                    if abono_texto:
                        try:
                            abono = float(abono_texto.replace(".", "").replace(",", "").replace("$", "").strip())
                        except ValueError:
                            abono = 0.0
                    if abono > 0:
                        conn = conectar()
                        conn.execute("UPDATE metas SET monto_actual = monto_actual + ? WHERE id = ? AND usuario_id = ?", (abono, m_id, UID))
                        conn.commit()
                        conn.close()
                        st.success("¡Abono registrado!")
                        st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No tienes metas creadas.")

    st.markdown("### ⚙️ Límite Mensual")
    with st.form("form_presupuesto"):
        presupuesto_texto = st.text_input("Presupuesto máximo mensual ($)", placeholder="Ej: 2.000.000")
        guardar = st.form_submit_button("Actualizar Límite")
        
        nuevo_presupuesto = 0.0
        if presupuesto_texto:
            try:
                nuevo_presupuesto = float(presupuesto_texto.replace(".", "").replace(",", "").replace("$", "").strip())
            except ValueError:
                nuevo_presupuesto = 0.0

        if guardar and nuevo_presupuesto > 0:
            conn = conectar()
            conn.execute("INSERT OR REPLACE INTO configuracion (usuario_id, presupuesto_mensual) VALUES (?, ?)", (UID, nuevo_presupuesto))
            conn.commit()
            conn.close()
            st.success("¡Presupuesto actualizado!")

# ==========================================
# 4. REPORTES & GESTIÓN
# ==========================================
elif menu == "📂 Reportes & Excel":
    st.markdown("### 📂 Historial y Exportación")
    
    conn = conectar()
    movimientos = conn.execute("SELECT id, fecha, tipo, categoria, descripcion, valor, etiqueta FROM movimientos WHERE usuario_id = ? ORDER BY fecha DESC", (UID,)).fetchall()
    conn.close()
    
    if movimientos:
        df_historial = pd.DataFrame(movimientos, columns=["ID", "Fecha", "Tipo", "Categoría", "Descripción", "Valor", "Etiqueta"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_historial.drop(columns=["ID"]).to_excel(writer, index=False, sheet_name='Movimientos')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Descargar Reporte en Excel (.xlsx)",
            data=excel_data,
            file_name="finbot_reporte.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🗑️ Administrar Movimientos (Eliminar duplicados)")
        
        for m_id, fecha, tipo, categoria, descripcion, valor, etiqueta in movimientos:
            desc_txt = f" - {descripcion}" if descripcion else ""
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"**[{fecha}] {tipo}** | {categoria}{desc_txt} : **{dinero(valor)}**")
            with col_btn:
                if st.button("🗑️ Borrar", key=f"del_{m_id}"):
                    conn = conectar()
                    conn.execute("DELETE FROM movimientos WHERE id = ? AND usuario_id = ?", (m_id, UID))
                    conn.commit()
                    conn.close()
                    st.success("¡Movimiento eliminado!")
                    st.rerun()
            st.markdown("<hr style='margin: 5px 0px; border-color: #334155;'>", unsafe_allow_html=True)
    else:
        st.info("No hay movimientos registrados.")

# ==========================================
# 5. CONSEJOS IA
# ==========================================
elif menu == "💡 Consejos IA":
    st.markdown("### 💡 Asesor Financiero Inteligente")
    mes = date.today().strftime("%Y-%m")
    conn = conectar()
    datos = conn.execute("SELECT categoria, SUM(valor) FROM movimientos WHERE usuario_id = ? AND tipo='GASTO' AND substr(fecha,1,7)=? GROUP BY categoria ORDER BY SUM(valor) DESC", (UID, mes)).fetchall()
    conn.close()
    
    if datos:
        cat_mayor, val_mayor = datos[0]
        st.info(f"🔍 **Análisis del mes:** Tu mayor fuente de gastos actual es **{cat_mayor}** con un total de **{dinero(val_mayor)}**.")
        
        if "Ocio" in cat_mayor or "Hormiga" in cat_mayor:
            st.warning("⚠️ Cuidado con los gastos discrecionales. Reducir un poco tus salidas te ayudará a cumplir tus metas mucho más rápido.")
        else:
            st.success("✅ Tus gastos principales están enfocados en necesidades fundamentales. ¡Vas por excelente camino!")
            
        ahorro = val_mayor * 0.15
        st.success(f"💡 **Tip Pro:** Si reduces un 15% los gastos en esta categoría, liberarías **{dinero(ahorro)}** para tu fondo de ahorro este mes.")
    else:
        st.info("Registra algunos movimientos para activar los consejos automáticos.")