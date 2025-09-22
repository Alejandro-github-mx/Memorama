# 🧠 Memorama – Juego de pares en Streamlit

Este proyecto permite al profesor ingresar 10, 20, 30 o 50 términos (con o sin imágenes) para que los estudiantes encuentren los pares en un memorama grupal.

## 🚀 Cómo ejecutar
1. Clonar este repositorio:
   ```bash
   git clone https://github.com/TU-USUARIO/Memorama.git
   cd Memorama


# Crear entorno virtual (opcional):

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows


# Instalar dependencias:
pip install -r requirements.txt

# Ejecutar:

streamlit run memorama_streamlit_app.py

# Características

Profesor puede cargar 10, 20, 30 o 50 términos.

Soporte opcional para imágenes.

Cartas numeradas en orden ascendente.

Animación inicial de mezcla.

Animación y conteo al completar el tablero.


**`memorama_streamlit_app.py`**  
👉 Aquí pegarás el código que ya te preparé en el canvas.

---

# Subir a GitHub
1. Crear repo en GitHub:  
   - Nombre: `Memorama`
   - Sin README (ya lo tienes local).
   - Público o privado, como prefieras.

2. Conectar y subir:
```bash
git remote add origin https://github.com/TU-USUARIO/Memorama.git
git add .
git commit -m "Primer commit - estructura base del memorama"
git branch -M main
git push -u origin main
