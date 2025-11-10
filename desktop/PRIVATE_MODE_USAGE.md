# Modo Privado y Subida de Archivos

## Activar modo privado
Backend: export PRIVATE_MODE=true (o en .env).  
Frontend: REACT_APP_PRIVATE_MODE=true.

## Flujo de subida de archivos
En modo privado, si no hay tarea activa en un thread, al subir un archivo se crea una tarea dummy '(private-mode dummy task for uploads)' y se marca el thread como WORKING para poder adjuntar memoria.

Endpoint: POST /apps/threads/{tid}/upload_file  (multipart/form-data campo 'upload')
Respuesta incluye memory_entry_id y flag private_mode_dummy.

## Notas
- Archivos de texto indexan hasta 5000 caracteres.
- Binarios se almacenan indicando nombre y tipo.
- Pendiente: extracción avanzada (PDF/DOCX/Imágenes OCR) y vector embeddings.

