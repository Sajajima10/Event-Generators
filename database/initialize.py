import mariadb
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_database():
    """Crea la base de datos si no existe."""
    print("📦 Creando base de datos...")
    
    try:
        # Conectar sin especificar base de datos
        conn = mariadb.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '0000')
        )
        
        cursor = conn.cursor()
        
        # Nombre de la base de datos
        db_name = os.getenv('DB_NAME', 'event_manager')
        
        # Crear base de datos
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✅ Base de datos '{db_name}' creada/verificada")
        
        cursor.close()
        conn.close()
        return True
        
    except mariadb.Error as e:
        print(f"❌ Error creando base de datos: {e}")
        return False

def execute_sql_file():
    """Ejecuta el archivo setup.sql para crear tablas."""
    print("📄 Ejecutando script SQL...")
    
    try:
        # Conectar a la base de datos específica
        conn = mariadb.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '0000'),
            database=os.getenv('DB_NAME', 'event_manager')
        )
        
        cursor = conn.cursor()
        
        # RUTA CORRECTA: setup.sql está en el mismo directorio que initialize.py
        current_dir = os.path.dirname(__file__)
        sql_file = os.path.join(current_dir, 'setup.sql')
        
        print(f"🔍 Buscando: {sql_file}")
        
        # Verificar que setup.sql existe
        if not os.path.exists(sql_file):
            print(f"❌ Error: No se encuentra el archivo {sql_file}")
            print("   Asegúrate de que database/setup.sql existe")
            return False
        
        # Leer el archivo SQL
        with open(sql_file, 'r') as file:
            sql_content = file.read()
        
        print(f"📖 Leyendo {len(sql_content)} caracteres...")
        
        # Separar y ejecutar cada comando SQL
        commands = sql_content.split(';')
        
        for command in commands:
            if command.strip():  # Ignorar líneas vacías
                try:
                    cursor.execute(command)
                except mariadb.Error as e:
                    # Ignorar errores de DROP TABLE si las tablas no existen
                    if "DROP TABLE" in command and "doesn't exist" in str(e):
                        pass  # Es normal
                    else:
                        print(f"⚠️  Advertencia en comando SQL: {e}")
                        print(f"   Comando: {command[:50]}...")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Script SQL ejecutado exitosamente")
        return True
        
    except mariadb.Error as e:
        print(f"❌ Error ejecutando SQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_tables():
    """Verifica que las tablas se crearon correctamente."""
    print("🔍 Verificando tablas creadas...")
    
    try:
        conn = mariadb.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '0000'),
            database=os.getenv('DB_NAME', 'event_manager')
        )
        
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Se encontraron {len(tables)} tablas:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No se encontraron tablas")
        
        cursor.close()
        conn.close()
        return True
        
    except mariadb.Error as e:
        print(f"❌ Error verificando tablas: {e}")
        return False

def main():
    """Función principal de inicialización."""
    print("=" * 50)
    print("🚀 INICIALIZACIÓN DE BASE DE DATOS")
    print("=" * 50)
    
    # Paso 1: Crear base de datos
    if not create_database():
        return False
    
    # Paso 2: Ejecutar script SQL
    if not execute_sql_file():
        return False
    
    # Paso 3: Verificar tablas
    if not verify_tables():
        return False
    
    print("=" * 50)
    print("🎉 ¡INICIALIZACIÓN COMPLETADA EXITOSAMENTE!")
    print("=" * 50)
    print("\n📋 Resumen:")
    print(f"   Base de datos: {os.getenv('DB_NAME', 'event_manager')}")
    print(f"   Usuario: {os.getenv('DB_USER', 'root')}")
    print(f"   Host: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 3306)}")
    print("\n➡️  Siguiente paso: Ejecutar 'python database/db_connection.py'")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Todo listo para comenzar el proyecto!")
        else:
            print("\n❌ La inicialización falló. Revisa los errores.")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Inicialización cancelada por el usuario")
        sys.exit(1)
