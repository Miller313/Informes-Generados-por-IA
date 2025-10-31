import streamlit as st
from core_logic import generate_report_text, create_google_doc_report
import os

st.set_page_config(page_title="Generador de Informes IA", layout="wide")
st.title("🤖 Generador de Informes Técnicos con IA")

# --- CONFIGURACIÓN ---
st.subheader("1. Configuración")
template_id = st.text_input("ID de la plantilla de Google Docs")
parent_folder_id = st.text_input("ID de la carpeta de destino en Google Drive")

# --- ¡CAMPO NUEVO Y OBLIGATORIO! ---
user_email = st.text_input("Tu Correo de Google", help="Tu email personal. El informe se transferirá a tu propiedad.")

# (Resto del código de app.py: cargador de imágenes, formulario, etc... sin cambios)
# ...

# --- LÓGICA DE GENERACIÓN ---
if submitted:
    # Añadimos 'user_email' a la lista de campos obligatorios
    required_fields = [template_id, parent_folder_id, user_email, client_name, equipment, acciones_realizadas]
    if report_type == "Servicio Técnico":
        required_fields.append(problem_description)
        
    if not all(required_fields):
        st.warning("Por favor, completa TODOS los campos, incluido tu correo.")
    else:
        with st.spinner("🧠 Redactando y creando el documento..."):
            report_text = generate_report_text(
                report_type=report_type,
                # ... (otros campos) ...
            )
            
            if "Ocurrió un error" in report_text:
                st.error(report_text)
            else:
                doc_url, error = create_google_doc_report(
                    # ... (otros campos) ...
                    report_text=report_text,
                    user_email=user_email, # Pasamos el correo a la lógica
                    image_details=image_details
                )
                
                if error:
                    st.error(error)
                else:
                    st.success("¡Informe generado y transferido a tu propiedad!")
                    st.markdown(f"**[Abrir el informe en Google Docs]({doc_url})**", unsafe_allow_html=True)
