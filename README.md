# 📅 Sistema de Gestión de Eventos (Event Manager)

¡Bienvenido al **Sistema de Gestión de Eventos**! Esta aplicación permite organizar eventos, gestionar recursos (salas, equipos, personal) y detectar conflictos de horario automáticamente.

Sigue esta guía para poner en marcha el programa en unos pocos minutos.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado lo siguiente:

1.  **Python 3.10 o superior**: [Descargar aquí](https://www.python.org/downloads/) (Durante la instalación, marca la casilla **"Add Python to PATH"**).
2.  **MariaDB Server**: [Descargar aquí](https://mariadb.org/download/). Asegúrate de tener activo el servicio de base de datos.
    **Asegurate de al instalar MariaDB usar la contraseña 0000, o cambiar la contraseña del archivo .env por la que usaste en la instalacion.
3.  **MariaDB Connector/C**: **(Obligatorio para Windows)**. Instala este driver para que Python pueda comunicarse con MariaDB: [Descargar Conector MSI](https://mariadb.com/downloads/connectors/connector-c/).

---

## 🚀 Guía de Inicio Rápido

### 1. Preparar el entorno
Abre una terminal o consola (CMD o PowerShell) y navega hasta la carpeta del proyecto:
```bash
cd ruta/a/tu/proyecto
```

### 2. Instalar dependencias
Instala todas las librerías necesarias ejecutando el siguiente comando:
```bash
pip install -r requirements.txt
```

### 3. Inicializar la Base de Datos
El proyecto ya incluye un archivo `.env` con la configuración predeterminada. Ahora debes crear la estructura de tablas necesaria ejecutando el script de inicialización:

```bash
python database/initialize.py
```
*Si todo está bien, verás mensajes con ✅ indicando que la base de datos `event_manager` y sus tablas están listas.*

### 4. Ejecutar el programa
¡Todo listo! Para iniciar la aplicación de gestión (Interfaz de Comandos), ejecuta:

```bash
python cli/main.py
```

---

## 📂 Estructura del Proyecto

*   **`cli/`**: Contiene la interfaz de usuario principal (`main.py`).
*   **`database/`**: Scripts de conexión, inicializacin.
*   **`models/`**: Definiciones de los objetos del sistema (Eventos, Recursos, etc.).
*   **`services/`**: Lógica de negocio (gestión de datos y procesos).
*   **`validators/`**: Herramientas para detectar choques de horarios y validar reglas.

---

## ❓ Solución de Problemas

*   **Error de conexión (Access Denied)**: Si tu contraseña de MariaDB es distinta a la que viene en el archivo `.env`, abre el archivo `.env` en la carpeta raíz o en `database/` y edita la línea `DB_PASSWORD`.
*   **Error: "MariaDB Connector/C not found"**: Este error ocurre si no instalaste el driver MSI mencionado en los requisitos previos.
*   **Comando 'python' no reconocido**: Intenta usar `python3` en lugar de `python`.

---

El proceso de creacion de este proyecto paso varias etapas en las cuales aunque la dificultad no tuvo muchos picos, si es cierto que varias veces me estanque en la creacion de este proyecto.
Al inicio pense en seguir ciegamente las instrucciones del proyecto, simplemente me limite a cumplir los requisitos. Como trabajar en python y en proyectos un poco mas grandes no era algo desconocido para mi, primeramente cree una estructura que me permitiera una facilidad y una organizacion suficiente para que el proyecto se mejorara con el tiempo. A pesar de que el primer resultado final no fue nada complicado, era un poco simple, por esta razon decidi comenzar un nuevo proyecto un poco mas ambicioso. Era una decision un poco radical, ya que era incluso mucho mas sencillo, escalar el resultado que ya tenia en mano, pero verdaderamente, tenia confianza en lo que habia hecho, y crei poder hacerlo mucho mejor la vez proxima.

El segundo intento fue un poco mas sencillo de terminar, es cierto que al tener ya una vision de lo que se iba a hacer, un nuevo proyecto iba a ser mucho mas sencillo, en este caso igual que en el anterior, no hubo mucha dificultad, sabia trabajar con python, habia usado anteriormente json, a nivel estructural ya habia conformado como iba a ser todo, y la programacion orientada a objetos, era lo normal para mi, aunque mi dominio con ella aun sigue siendo deficiente, pero verdaderamente fue sencillo terminar. A pesar de tener otro resultado en mano, seguia siendo insuficiente para mi, asi que decidi empezar algo un poco diferente.

EN esta tercera version del proyecto, me puse la meta personal de superarme, asi que comence a aprender un poco de sql, era completamente nuevo para mi, asi que el pico de dificultad fue un poco mayor, aqui tenia que crear las bases de datos, configurar las conexiones, verificar que todo estuviera en orden, y luego de que la base de datos estuviera montada, entonces ahi, comenzaba la creacion del proyecto. Ciertamente en este proceso, me estanque varias veces, en especial en la configuracion y las conexiones de la base de datos, pero con un poco de tiempo se raalizo. A pesar de que esta tercera entrega de Event-Generators era una aplicacion de terminal, para mi era una mejor version con mejor manejo de errores, y conflictos que las versiones anteriores, y aqui esta la version actual de este programa. 
