import streamlit as st # Importante: añadimos streamlit para manejar los secretos
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io
from PIL import Image

# --- CONFIGURACIÓN Y AUTENTICACIÓN (NUEVA VERSIÓN PARA LA NUBE) ---
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/cloud-platform']
PROJECT_ID = "app-informes-nube" # O el ID de tu nuevo proyecto en la nube
LOCATION = "us-east1"

def get_credentials():
    """Obtiene las credenciales desde los Secretos de Streamlit."""
    # Carga las credenciales desde el secreto "google_creds" que crearemos en Streamlit
    creds_dict = st.secrets["google_creds"]
    CREDENTIALS = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return CREDENTIALS

CREDENTIALS = get_credentials()
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=CREDENTIALS)

# --- FUNCIÓN DE GENERACIÓN DE TEXTO (Sin cambios) ---
def generate_report_text(report_type, client_name, equipment, problem_description, acciones_realizadas):
    model = GenerativeModel("gemini-2.5-pro")
    prompt = ""
    if report_type == "Servicio Técnico":
        prompt = f"""
        Actúa como un técnico de soporte senior especializado...
        ... (tu prompt de servicio técnico completo va aquí) ...
        """
    elif report_type == "Instalación":
        prompt = f"""
        Actúa como un técnico instalador senior...
        ... (tu prompt de instalación completo va aquí) ...
        """
    try:
        response = model.generate_content(prompt)
        full_text = "".join(part.text for part in response.candidates[0].content.parts)
        return full_text.replace("**", "")
    except Exception as e:
        return f"Ocurrió un error al contactar la API de Vertex AI: {e}"

# --- FUNCIÓN DE GOOGLE DOCS (Lógica de imágenes corregida) ---
def create_google_doc_report(template_id, parent_folder_id, client_name, equipment, report_text, image_details=None):
    try:
        drive_service = build('drive', 'v3', credentials=CREDENTIALS)
        docs_service = build('docs', 'v1', credentials=CREDENTIALS)
        
        # 1. Copia la plantilla y reemplaza el texto principal
        copied_file_name = f"Informe - {client_name} - {datetime.now().strftime('%Y-%m-%d')}"
        body = {'name': copied_file_name, 'parents': [parent_folder_id]}
        copied_file = drive_service.files().copy(fileId=template_id, body=body).execute()
        document_id = copied_file.get('id')
        
        requests = [
            {'replaceAllText': {'replaceText': client_name, 'containsText': {'text': '{{cliente}}'}}},
            {'replaceAllText': {'replaceText': equipment, 'containsText': {'text': '{{equipo}}'}}},
            {'replaceAllText': {'replaceText': datetime.now().strftime('%d/%m/%Y'), 'containsText': {'text': '{{fecha_actual}}'}}},
            {'replaceAllText': {'replaceText': report_text, 'containsText': {'text': '{{cuerpo_informe}}'}}},
        ]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

        # 2. Inserta las imágenes
        if image_details:
            doc = docs_service.documents().get(documentId=document_id).execute()
            doc_content = doc.get('body').get('content')
            anexo_location = None
            for element in doc_content:
                if 'paragraph' in element:
                    for run in element.get('paragraph').get('elements'):
                        if 'textRun' in run and '{{anexo_imagenes}}' in run.get('textRun').get('content'):
                            anexo_location = run.get('startIndex')
                            break
                if anexo_location: break

            if anexo_location:
                all_image_requests = []
                for detail in reversed(image_details):
                    image_file = detail["file"]
                    image_bytes = image_file.read()
                    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=image_file.type, resumable=True)
                    image_metadata = {'name': image_file.name, 'parents': [parent_folder_id]}
                    uploaded_image = drive_service.files().create(body=image_metadata, media_body=media, fields='id, webContentLink').execute()
                    image_url = uploaded_image.get('webContentLink')
                    drive_service.permissions().create(fileId=uploaded_image.get('id'), body={'role': 'reader', 'type': 'anyone'}).execute()
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    width_px, height_px = pil_image.size
                    aspect_ratio = height_px / width_px if width_px > 0 else 1
                    max_width_pt = 450.0
                    final_height_pt = max_width_pt * aspect_ratio

                    if detail["description"]:
                        all_image_requests.append({'insertText': {'location': {'index': anexo_location}, 'text': f'\n{detail["description"]}\n\n'}})
                    all_image_requests.append({'insertInlineImage': {'location': {'index': anexo_location}, 'uri': image_url, 'objectSize': {'width': {'magnitude': max_width_pt, 'unit': 'PT'}, 'height': {'magnitude': final_height_pt, 'unit': 'PT'}}}})
                    if detail["name"]:
                        all_image_requests.append({'insertText': {'location': {'index': anexo_location}, 'text': f'\n{detail["name"]}\n'}})
                
                if all_image_requests:
                    docs_service.documents().batchUpdate(documentId=document_id, body={'requests': all_image_requests}).execute()

                delete_request = {'requests': [{'deleteContentRange': {'range': {'startIndex': anexo_location, 'endIndex': anexo_location + len('{{anexo_imagenes}}')}}}]}
                docs_service.documents().batchUpdate(documentId=document_id, body=delete_request).execute()

        doc_url = f"https.google.com/document/d/{document_id}/edit"
        return doc_url, None
    except Exception as e:

        return None, f"Ocurrió un error con Google Docs/Drive: {e}"
