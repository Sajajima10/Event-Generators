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
        conn = mariadb.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '0000')
        )
        
        cursor = conn.cursor()
        db_name = os.getenv('DB_NAME', 'event_manager')
        
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
        conn = mariadb.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '0000'),
            database=os.getenv('DB_NAME', 'event_manager')
        )
        
        cursor = conn.cursor()
        current_dir = os.path.dirname(__file__)
        sql_file = os.path.join(current_dir, 'setup.sql')
        
        print(f"🔍 Buscando: {sql_file}")
        
        if not os.path.exists(sql_file):
            print(f"❌ Error: No se encuentra el archivo {sql_file}")
            return False
        
        with open(sql_file, 'r') as file:
            sql_content = file.read()
        
        commands = sql_content.split(';')
        
        for command in commands:
            if command.strip():
                try:
                    cursor.execute(command)
                except mariadb.Error as e:
                    if "DROP TABLE" in command and "doesn't exist" in str(e):
                        pass
                    else:
                        print(f"⚠️  Advertencia en comando SQL: {e}")
        
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
    
    if not create_database():
        return False
    
    if not execute_sql_file():
        return False
    
    if not verify_tables():
        return False
    
    print("=" * 50)
    print("🎉 ¡INICIALIZACIÓN COMPLETADA EXITOSAMENTE!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Inicialización cancelada por el usuario")
        sys.exit(1)