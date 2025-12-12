"""
ResourceService - Servicio CRUD para manejar recursos en el gestor de eventos.
Maneja recursos como salas, equipos, personas, etc.
"""
import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

# ========== CONFIGURAR IMPORTS ==========
# Configurar path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))  # services/
project_root = os.path.dirname(current_dir)  # Proyecto/

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from models.resource import Resource
    from database.db_connection import DatabaseConnection
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    IMPORT_SUCCESS = False

# ========== CLASE PRINCIPAL ==========
if IMPORT_SUCCESS:
    logger = logging.getLogger(__name__)
    
    class ResourceService:
        """Servicio para operaciones CRUD con recursos."""
        
        def __init__(self, db_connection: Optional[DatabaseConnection] = None):
            """
            Inicializa el servicio de recursos.
            
            Args:
                db_connection: Conexión a la base de datos (opcional)
            """
            self.db = db_connection or DatabaseConnection()
            logger.info("✅ ResourceService inicializado")
        
        def create_resource(self, resource: Resource) -> Optional[Resource]:
            """
            Crea un nuevo recurso en la base de datos.
            
            Args:
                resource: Objeto Resource a crear
            
            Returns:
                Resource creado con ID asignado, o None si hay error
            """
            try:
                logger.info(f"Creando nuevo recurso: {resource.name}")
                
                query = """
                    INSERT INTO resources (
                        name, description, resource_type, 
                        quantity, is_active, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    resource.name,
                    resource.description,
                    resource.resource_type,
                    resource.quantity,
                    resource.is_active,
                    resource.created_at or datetime.now()
                )
                
                # Ejecutar inserción
                resource_id = self.db.execute_query(query, params)
                
                if resource_id:
                    resource.id = resource_id
                    logger.info(f"✅ Recurso creado con ID: {resource_id}")
                    return resource
                
                logger.error("❌ No se pudo crear el recurso")
                return None
                
            except Exception as e:
                logger.error(f"❌ Error al crear recurso: {e}")
                return None
        
        def get_resource(self, resource_id: int) -> Optional[Resource]:
            """
            Obtiene un recurso por su ID.
            
            Args:
                resource_id: ID del recurso a buscar
            
            Returns:
                Resource encontrado o None si no existe
            """
            try:
                logger.debug(f"Buscando recurso ID: {resource_id}")
                
                query = "SELECT * FROM resources WHERE id = %s"
                result = self.db.execute_query(query, (resource_id,), fetch=True)
                
                if result:
                    resource_data = result[0]
                    resource = Resource.from_db_row(resource_data)
                    logger.debug(f"✅ Recurso encontrado: {resource.name}")
                    return resource
                
                logger.warning(f"⚠️ Recurso ID {resource_id} no encontrado")
                return None
                
            except Exception as e:
                logger.error(f"❌ Error al obtener recurso: {e}")
                return None
        
        def get_all_resources(
            self, 
            active_only: bool = False,
            resource_type: Optional[str] = None,
            limit: int = 100
        ) -> List[Resource]:
            """
            Obtiene todos los recursos con filtros opcionales.
            
            Args:
                active_only: Si True, solo recursos activos
                resource_type: Filtrar por tipo específico
                limit: Máximo número de recursos
            
            Returns:
                Lista de objetos Resource
            """
            try:
                logger.debug(f"Obteniendo recursos (activos: {active_only}, tipo: {resource_type})")
                
                # Construir query dinámica
                where_clauses = []
                params = []
                
                if active_only:
                    where_clauses.append("is_active = TRUE")
                
                if resource_type:
                    where_clauses.append("resource_type = %s")
                    params.append(resource_type)
                
                # Construir query final
                where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                query = f"SELECT * FROM resources {where_str} ORDER BY name LIMIT %s"
                params.append(limit)
                
                results = self.db.execute_query(query, tuple(params), fetch=True)
                resources = [Resource.from_db_row(row) for row in results]
                
                logger.info(f"✅ Encontrados {len(resources)} recursos")
                return resources
                
            except Exception as e:
                logger.error(f"❌ Error al obtener recursos: {e}")
                return []
        
        def update_resource(self, resource_id: int, updates: Dict[str, Any]) -> bool:
            """
            Actualiza un recurso existente.
            
            Args:
                resource_id: ID del recurso a actualizar
                updates: Diccionario con campos a actualizar
            
            Returns:
                True si se actualizó correctamente
            """
            try:
                logger.info(f"Actualizando recurso ID: {resource_id}")
                
                # Verificar que el recurso existe
                current_resource = self.get_resource(resource_id)
                if not current_resource:
                    logger.error(f"❌ Recurso ID {resource_id} no encontrado")
                    return False
                
                # Construir query dinámica
                set_clauses = []
                params = []
                
                # Campos permitidos para actualizar
                allowed_fields = ['name', 'description', 'resource_type', 'quantity', 'is_active']
                
                for field, value in updates.items():
                    if field in allowed_fields and value is not None:
                        set_clauses.append(f"{field} = %s")
                        params.append(value)
                
                if not set_clauses:
                    logger.warning("⚠️ No hay campos válidos para actualizar")
                    return False
                
                # Añadir resource_id al final para WHERE
                params.append(resource_id)
                
                query = f"UPDATE resources SET {', '.join(set_clauses)} WHERE id = %s"
                
                # Ejecutar actualización
                rows_affected = self.db.execute_query(query, tuple(params))
                
                if rows_affected > 0:
                    logger.info(f"✅ Recurso ID {resource_id} actualizado correctamente")
                    return True
                
                logger.warning(f"⚠️ No se pudo actualizar recurso ID {resource_id}")
                return False
                
            except Exception as e:
                logger.error(f"❌ Error al actualizar recurso: {e}")
                return False
        
        def delete_resource(self, resource_id: int) -> bool:
            """
            Elimina un recurso por su ID.
            Nota: Solo elimina si no está siendo usado en eventos.
            
            Args:
                resource_id: ID del recurso a eliminar
            
            Returns:
                True si se eliminó correctamente
            """
            try:
                logger.info(f"Eliminando recurso ID: {resource_id}")
                
                # Verificar si el recurso está siendo usado
                check_query = """
                    SELECT COUNT(*) as usage_count 
                    FROM event_resources 
                    WHERE resource_id = %s
                """
                usage_result = self.db.execute_query(check_query, (resource_id,), fetch=True)
                
                if usage_result and usage_result[0]['usage_count'] > 0:
                    logger.error(f"❌ Recurso ID {resource_id} está siendo usado en eventos")
                    return False
                
                # Eliminar el recurso
                query = "DELETE FROM resources WHERE id = %s"
                rows_affected = self.db.execute_query(query, (resource_id,))
                
                if rows_affected > 0:
                    logger.info(f"✅ Recurso ID {resource_id} eliminado correctamente")
                    return True
                
                logger.warning(f"⚠️ No se pudo eliminar recurso ID {resource_id}")
                return False
                
            except Exception as e:
                logger.error(f"❌ Error al eliminar recurso: {e}")
                return False
        
        def search_resources(self, search_term: str, limit: int = 20) -> List[Resource]:
            """
            Busca recursos por nombre o descripción.
            
            Args:
                search_term: Término de búsqueda
                limit: Máximo número de resultados
            
            Returns:
                Lista de recursos que coinciden
            """
            try:
                logger.debug(f"Buscando recursos con término: '{search_term}'")
                
                query = """
                    SELECT * FROM resources 
                    WHERE name LIKE %s OR description LIKE %s
                    ORDER BY name
                    LIMIT %s
                """
                
                search_pattern = f"%{search_term}%"
                params = (search_pattern, search_pattern, limit)
                
                results = self.db.execute_query(query, params, fetch=True)
                resources = [Resource.from_db_row(row) for row in results]
                
                logger.info(f"✅ Encontrados {len(resources)} recursos para '{search_term}'")
                return resources
                
            except Exception as e:
                logger.error(f"❌ Error al buscar recursos: {e}")
                return []
        
        def check_availability(
            self, 
            resource_id: int, 
            required_quantity: int = 1
        ) -> Dict[str, Any]:
            """
            Verifica la disponibilidad de un recurso.
            
            Args:
                resource_id: ID del recurso
                required_quantity: Cantidad necesaria
            
            Returns:
                Diccionario con información de disponibilidad
            """
            try:
                logger.debug(f"Verificando disponibilidad de recurso {resource_id}")
                
                resource = self.get_resource(resource_id)
                if not resource:
                    return {
                        'available': False,
                        'message': 'Recurso no encontrado',
                        'resource_id': resource_id
                    }
                
                # Calcular uso actual desde la base de datos
                usage_query = """
                    SELECT COALESCE(SUM(quantity_used), 0) as total_used
                    FROM event_resources er
                    JOIN events e ON er.event_id = e.id
                    WHERE er.resource_id = %s 
                    AND e.status = 'scheduled'
                    AND e.end_time > NOW()
                """
                
                usage_result = self.db.execute_query(usage_query, (resource_id,), fetch=True)
                current_usage = usage_result[0]['total_used'] if usage_result else 0
                
                available_quantity = max(0, resource.quantity - current_usage)
                is_available = available_quantity >= required_quantity
                
                result = {
                    'available': is_available,
                    'resource_id': resource_id,
                    'resource_name': resource.name,
                    'total_quantity': resource.quantity,
                    'current_usage': current_usage,
                    'available_quantity': available_quantity,
                    'required_quantity': required_quantity,
                    'is_active': resource.is_active
                }
                
                if not resource.is_active:
                    result['message'] = 'Recurso inactivo'
                elif not is_available:
                    result['message'] = f'Solo hay {available_quantity} disponible(s) de {required_quantity} requerido(s)'
                else:
                    result['message'] = 'Disponible'
                
                logger.debug(f"✅ Disponibilidad verificada: {result['message']}")
                return result
                
            except Exception as e:
                logger.error(f"❌ Error al verificar disponibilidad: {e}")
                return {
                    'available': False,
                    'message': f'Error: {str(e)}',
                    'resource_id': resource_id
                }
        
        def get_resource_types(self) -> List[str]:
            """
            Obtiene todos los tipos de recursos únicos en el sistema.
            
            Returns:
                Lista de tipos de recursos
            """
            try:
                logger.debug("Obteniendo tipos de recursos")
                
                query = "SELECT DISTINCT resource_type FROM resources WHERE resource_type IS NOT NULL ORDER BY resource_type"
                results = self.db.execute_query(query, fetch=True)
                
                types = [row['resource_type'] for row in results]
                logger.info(f"✅ Encontrados {len(types)} tipos de recursos")
                return types
                
            except Exception as e:
                logger.error(f"❌ Error al obtener tipos de recursos: {e}")
                return []
        
        def get_resource_usage_stats(self, resource_id: Optional[int] = None) -> Dict[str, Any]:
            """
            Obtiene estadísticas de uso de recursos.
            
            Args:
                resource_id: ID específico del recurso (opcional)
            
            Returns:
                Diccionario con estadísticas
            """
            try:
                logger.debug(f"Obteniendo estadísticas de uso para recurso: {resource_id}")
                
                stats = {}
                
                # Estadísticas generales
                general_query = """
                    SELECT 
                        COUNT(*) as total_resources,
                        SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_resources,
                        SUM(quantity) as total_capacity,
                        AVG(quantity) as avg_quantity
                    FROM resources
                """
                
                general_result = self.db.execute_query(general_query, fetch=True)
                if general_result:
                    stats.update(general_result[0])
                
                # Uso actual
                usage_query = """
                    SELECT 
                        r.id,
                        r.name,
                        r.quantity,
                        COALESCE(SUM(er.quantity_used), 0) as current_usage,
                        (r.quantity - COALESCE(SUM(er.quantity_used), 0)) as available
                    FROM resources r
                    LEFT JOIN event_resources er ON r.id = er.resource_id
                    LEFT JOIN events e ON er.event_id = e.id AND e.status = 'scheduled' AND e.end_time > NOW()
                    GROUP BY r.id, r.name, r.quantity
                """
                
                if resource_id:
                    usage_query += " WHERE r.id = %s"
                    usage_result = self.db.execute_query(usage_query, (resource_id,), fetch=True)
                else:
                    usage_result = self.db.execute_query(usage_query, fetch=True)
                
                stats['resources'] = usage_result if usage_result else []
                
                logger.info(f"✅ Estadísticas obtenidas")
                return stats
                
            except Exception as e:
                logger.error(f"❌ Error al obtener estadísticas: {e}")
                return {'error': str(e)}

    # ===== PRUEBAS DEL SERVICIO =====
    if __name__ == "__main__":
        print("\n" + "="*60)
        print("🧪 PROBANDO RESOURCE SERVICE")
        print("="*60)
        
        try:
            from models.resource import Resource
            
            # Crear servicio
            service = ResourceService()
            print("✅ ResourceService creado")
            
            # Crear recurso de prueba
            test_resource = Resource(
                name="Proyector HD",
                description="Proyector de alta definición 1080p",
                resource_type="equipment",
                quantity=3,
                is_active=True
            )
            
            # 1. Crear recurso
            created_resource = service.create_resource(test_resource)
            if created_resource:
                print(f"✅ Recurso creado con ID: {created_resource.id}")
                
                # 2. Obtener recurso por ID
                retrieved_resource = service.get_resource(created_resource.id)
                if retrieved_resource:
                    print(f"✅ Recurso recuperado: {retrieved_resource.name}")
                
                # 3. Obtener todos los recursos
                all_resources = service.get_all_resources(active_only=True)
                print(f"✅ Total recursos activos: {len(all_resources)}")
                
                # 4. Buscar recursos
                search_results = service.search_resources("proyector")
                print(f"✅ Recursos encontrados en búsqueda: {len(search_results)}")
                
                # 5. Verificar disponibilidad
                availability = service.check_availability(created_resource.id, 2)
                print(f"✅ Disponibilidad: {availability['message']}")
                
                # 6. Obtener tipos de recursos
                types = service.get_resource_types()
                print(f"✅ Tipos de recursos: {types}")
                
                # 7. Estadísticas
                stats = service.get_resource_usage_stats()
                print(f"✅ Estadísticas obtenidas: {stats.get('total_resources', 0)} recursos totales")
                
                # 8. Actualizar recurso
                updates = {'name': 'Proyector HD Actualizado', 'quantity': 4}
                if service.update_resource(created_resource.id, updates):
                    print("✏️ Recurso actualizado")
                
                # 9. Eliminar recurso (comentado para no borrar)
                # if service.delete_resource(created_resource.id):
                #     print("🗑️ Recurso eliminado")
            
            print("\n" + "="*60)
            print("🎉 ¡PRUEBAS DE RESOURCE SERVICE COMPLETADAS!")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error en pruebas: {e}")
            import traceback
            traceback.print_exc()
else:
    print("❌ No se pudo inicializar ResourceService debido a errores de importación")