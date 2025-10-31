import streamlit as st
from core_logic import generate_report_text, create_google_doc_report
import os

st.set_page_config(page_title="Generador de Informes IA", layout="wide")
st.title("🤖 Generador de Informes Técnicos con IA")

# --- CONFIGURACIÓN ---
st.subheader("1. Configuración")
template_id = st.text_input("ID de la plantilla de Google Docs", help="El ID largo en la URL de tu plantilla.")
parent_folder_id = st.text_input("ID de la carpeta de destino en Google Drive", help="El ID largo en la URL de la carpeta de destino.")

# --- CARGADOR DE IMÁGENES ---
st.subheader("2. Adjunta las Imágenes (Opcional)")
uploaded_files = st.file_uploader(
    "Selecciona una o varias imágenes",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

st.markdown("---")

# --- FORMULARIO PRINCIPAL ---
st.subheader("3. Completa los Datos del Informe")
report_type = st.radio(
    "Selecciona el tipo de informe:",
    ("Servicio Técnico", "Instalación"),
    horizontal=True
)

with st.form("report_form"):
    client_name = st.text_input("Nombre del Cliente")
    equipment = st.text_input("Equipo(s) Involucrado(s)")
    
    problem_description = None
    if report_type == "Servicio Técnico":
        st.write("#### Datos del Servicio Técnico")
        problem_description = st.text_area("Descripción del Problema Reportado", height=100)
        acciones_realizadas = st.text_area("Diagnóstico y Acciones Realizadas", height=150)
    
    elif report_type == "Instalación":
        st.write("#### Datos de la Instalación")
        acciones_realizadas = st.text_area("Tareas de Instalación Realizadas", height=150)
    
    image_details = []
    if uploaded_files:
        st.write("#### Detalles de las Imágenes Adjuntas:")
        for i, uploaded_file in enumerate(uploaded_files):
            st.image(uploaded_file, width=150)
            image_name = st.text_input(f"Título para la imagen \"{uploaded_file.name}\"", key=f"img_name_{i}")
            image_desc = st.text_area(f"Descripción para la imagen \"{uploaded_file.name}\"", key=f"img_desc_{i}")
            image_details.append({
                "file": uploaded_file,
                "name": image_name,
                "description": image_desc
            })

    submitted = st.form_submit_button("Generar Informe en Google Docs")

# --- LÓGICA DE GENERACIÓN ---
if submitted:
    required_fields = [template_id, parent_folder_id, client_name, equipment, acciones_realizadas]
    if report_type == "Servicio Técnico":
        required_fields.append(problem_description)
        
    if not all(required_fields):
        st.warning("Por favor, completa todos los campos, incluidos los IDs de plantilla y carpeta.")
    else:
        with st.spinner("🧠 Redactando, subiendo imágenes y creando el documento..."):
            report_text = generate_report_text(
                report_type=report_type,
                client_name=client_name,
                equipment=equipment,
                problem_description=problem_description,
                acciones_realizadas=acciones_realizadas
            )
            
            if "Ocurrió un error" in report_text:
                st.error(report_text)
            else:
                doc_url, error = create_google_doc_report(
                    template_id=template_id,
                    parent_folder_id=parent_folder_id,
                    client_name=client_name,
                    equipment=equipment,
                    report_text=report_text,
                    image_details=image_details
                )
                
                if error:
                    st.error(error)
                else:
                    st.success("¡Informe generado con éxito en tu carpeta de Google Drive!")
                    st.markdown(f"**[Abrir el informe en Google Docs]({doc_url})**", unsafe_allow_html=True)