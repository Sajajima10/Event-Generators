import mariadb
import sys
import os
from dotenv import load_dotenv
import logging
from typing import Optional, List, Dict, Any

# Configurar variables de entorno
load_dotenv()

# Configuremos loggin
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConnection():

    # Clase singleton para manejar la conexión a la base de datos.
    # Garantiza una única conexión por aplicación.

    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):

        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_NAME', 'event_manager'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'autocommit': True,
            'connect_timeout': int(os.getenv('DB_CONNECTION_TIMEOUT', 30))
        }
        logger.debug("Configuración de DB inicializada")


    def connect(self) -> mariadb.Connection:
        # Establece conexión con MariaDB.
        try:
            if self._connection is None or not self._connection.open:
                logger.info(f"Conectando a MariaDB en {self.config['host']}:{self.config['port']}")
                self._connection = mariadb.connect(**self.config)
                logger.info("✅ Conexión a MariaDB establecida")
            return self._connection
        
        except mariadb.Error as e:
            logger.error(f"❌ Error al conectar a MariaDB: {e}")
            raise

    def disconnect(self):
        # Basicamente cierra la conecion con la base de datos
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None
            logger.info("Conexión a MariaDB cerrada")

    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None, 
        fetch: bool = False
    ) -> Any:
        
        """
        Ejecuta una consulta SQL.
        """
        connection = self.connect()
        cursor = None
    
        try:
            cursor = connection.cursor(dictionary=True)
            logger.debug(f"Ejecutando query: {query[:50]}...")
            
            cursor.execute(query, params or ())
            
            if fetch:
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    logger.debug(f"Query retornó {len(result)} filas")
                else:
                    result = cursor.lastrowid
            else:
                result = cursor.rowcount
            
            return result
        
        except mariadb.Error as e:
            logger.error(f"Error en consulta SQL: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Parámetros: {params}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        # Ejecuta la misma consulta con múltiples conjuntos de parámetros.
        connection = self.connect()
        cursor = None
        
        try:
            cursor = connection.cursor()
            cursor.executemany(query, params_list)
            total_rows = cursor.rowcount
            logger.debug(f"execute_many afectó {total_rows} filas")
            return total_rows
        
        except mariadb.Error as e:
            logger.error(f"Error en executemany: {e}")
            raise

        finally:
            if cursor:
                cursor.close()
    
    def test_connection(self) -> bool:
        # Prueba la conecion a la Base de Datos
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            return result[0] == 1
        
        except mariadb.Error as e:
            logger.error(f"Prueba de conexión fallida: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        # Obtiene la Información de la Base de datos
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            
            # Obtener versión de MariaDB
            cursor.execute("SELECT VERSION() as version")
            version = cursor.fetchone()
            
            # Obtener nombre de la base de datos actual
            cursor.execute("SELECT DATABASE() as db_name")
            db_info = cursor.fetchone()
            
            # Obtener lista de tablas
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            cursor.close()
            
            return {
                'version': version['version'] if version else 'Desconocida',
                'database': db_info['db_name'] if db_info else 'Desconocida',
                'tables': [list(table.values())[0] for table in tables],
                'table_count': len(tables)
            }
            
        except mariadb.Error as e:
            logger.error(f"Error obteniendo info de DB: {e}")
            return {}