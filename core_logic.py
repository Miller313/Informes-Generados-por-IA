import streamlit as st # Importante para leer los Secretos
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io
from PIL import Image

# --- CONFIGURACIÓN Y AUTENTICACIÓN (Versión Nube) ---
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/cloud-platform']
PROJECT_ID = "app-informes-nube"
LOCATION = "us-east1"

def get_credentials():
    """Obtiene las credenciales de la Cuenta de Servicio desde los Secretos de Streamlit."""
    # Carga las credenciales desde el secreto "google_creds"
    creds_dict = st.secrets["google_creds"]
    CREDENTIALS = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return CREDENTIALS

CREDENTIALS = get_credentials()
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=CREDENTIALS)

def generate_report_text(report_type, client_name, equipment, problem_description, acciones_realizadas):
    # --- Mantenemos tu prompt y modelo tal cual ---
    model = GenerativeModel("gemini-2.5-pro")
    prompt = ""
    
    if report_type == "Servicio Técnico":
        prompt = f"""
        Actúa como un técnico de soporte senior especializado. Tu tarea es redactar un informe de servicio técnico para el cliente: {client_name}.
        ... (Tu prompt completo de Servicio Técnico aquí) ...
        """
    elif report_type == "Instalación":
        prompt = f"""
        Actúa como un técnico instalador senior...
        ... (Tu prompt completo de Instalación aquí) ...
        """
        
    try:
        response = model.generate_content(prompt)
        full_text = "".join(part.text for part in response.candidates[0].content.parts)
        return full_text.replace("**", "")
    except Exception as e:
        return f"Ocurrió un error al contactar la API de Vertex AI: {e}"

# --- FUNCIÓN DE GOOGLE DOCS CON TRANSFERENCIA DE PROPIEDAD ---
def create_google_doc_report(template_id, parent_folder_id, client_name, equipment, report_text, user_email, image_details=None):
    try:
        drive_service = build('drive', 'v3', credentials=CREDENTIALS)
        docs_service = build('docs', 'v1', credentials=CREDENTIALS)
        
        # 1. Copia la plantilla
        copied_file_name = f"Informe - {client_name} - {datetime.now().strftime('%Y-%m-%d')}"
        body = {'name': copied_file_name, 'parents': [parent_folder_id]}
        copied_file = drive_service.files().copy(fileId=template_id, body=body).execute()
        document_id = copied_file.get('id')

        # --- !! LA SOLUCIÓN AL ERROR DE CUOTA !! ---
        # 2. Transfiere la propiedad del nuevo archivo del "robot" a "ti" (el usuario).
        drive_service.permissions().create(
            fileId=document_id,
            body={'role': 'owner', 'type': 'user', 'emailAddress': user_email},
            transferOwnership=True
        ).execute()
        # --- FIN DE LA SOLUCIÓN ---
        
        # 3. Reemplaza el texto (ahora como propietario)
        requests = [
            {'replaceAllText': {'replaceText': client_name, 'containsText': {'text': '{{cliente}}'}}},
            {'replaceAllText': {'replaceText': equipment, 'containsText': {'text': '{{equipo}}'}}},
            {'replaceAllText': {'replaceText': datetime.now().strftime('%d/%m/%Y'), 'containsText': {'text': '{{fecha_actual}}'}}},
            {'replaceAllText': {'replaceText': report_text, 'containsText': {'text': '{{cuerpo_informe}}'}}},
        ]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

        # 4. Inserta las imágenes (con la lógica que ya funciona)
        if image_details:
            doc = docs_service.documents().get(documentId=document_id).execute()
            # ... (Lógica para encontrar 'anexo_location') ...
            # ... (Lógica para borrar la etiqueta) ...
            # ... (Lógica para insertar cada imagen en 'reversed(image_details)') ...
            # (Esta parte de tu código anterior ya estaba bien)
            # ...

        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        return doc_url, None
    except Exception as e:
        return None, f"Ocurrió un error con Google Docs/Drive: {e}"
