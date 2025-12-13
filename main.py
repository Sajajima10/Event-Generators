import sys
import os
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import init, Fore, Style

# Importar servicios
from database.initialize import main as init_db
from services.event_service import EventService
from services.resource_service import ResourceService
from validators.conflict_checker import ConflictChecker
from services.constraint_service import ConstraintService  # <--- NUEVO IMPORT
from models.event import Event
from models.resource import Resource
from models.constraint import Constraint # <--- NUEVO IMPORT

# Inicializar colores
init(autoreset=True)

class EventManagerApp:
    def __init__(self):
        self.event_service = EventService()
        self.resource_service = ResourceService()
        self.conflict_checker = ConflictChecker()
        self.constraint_service = ConstraintService() # <--- INICIALIZAR SERVICIO

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        print(Fore.CYAN + "=" * 50)
        print(Fore.CYAN + "📅  SISTEMA DE GESTIÓN DE EVENTOS")
        print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)

    # ==========================
    # GESTIÓN DE RECURSOS
    # ==========================
    def view_resources(self):
        print(Fore.YELLOW + "\n📋 LISTA DE RECURSOS DISPONIBLES")
        resources = self.resource_service.get_all_resources()
        
        if not resources:
            print(Fore.RED + "No hay recursos registrados.")
            return

        data = []
        for r in resources:
            status = "✅" if r.is_active else "⛔"
            available = r.available_quantity()
            data.append([r.id, r.name, r.resource_type, f"{available}/{r.quantity}", status])
        
        print(tabulate(data, headers=["ID", "Nombre", "Tipo", "Disp/Total", "Estado"], tablefmt="fancy_grid"))

    def create_resource(self):
        print(Fore.YELLOW + "\n➕ NUEVO RECURSO")
        try:
            name = input("Nombre del recurso: ")
            type_r = input("Tipo (room, equipment, person): ")
            qty = int(input("Cantidad total: "))
            desc = input("Descripción: ")

            res = Resource(name=name, resource_type=type_r, quantity=qty, description=desc)
            if self.resource_service.create_resource(res):
                print(Fore.GREEN + f"\n✅ Recurso '{name}' creado exitosamente!")
            else:
                print(Fore.RED + "\n❌ Error al crear recurso.")
        except ValueError:
            print(Fore.RED + "❌ Error: La cantidad debe ser un número.")

    # ==========================
    # GESTIÓN DE RESTRICCIONES (NUEVO)
    # ==========================
    def manage_constraints(self):
        """Menú para crear reglas entre recursos."""
        print(Fore.MAGENTA + "\n⛓️  GESTIÓN DE RESTRICCIONES Y REGLAS")
        print("Define reglas como: 'El Recurso A requiere al Recurso B'")
        
        self.view_resources()
        print("-" * 30)
        
        try:
            # 1. Crear la definición de la restricción
            print("\n1. Definir Nueva Regla:")
            name = input("Nombre de la regla (ej: Pack Audio): ")
            desc = input("Descripción: ")
            
            # Crear objeto restricción
            new_constraint = Constraint(
                name=name,
                constraint_type="co_requirement", # Por defecto co-requisito
                description=desc
            )
            
            # Guardar encabezado
            saved_constraint = self.constraint_service.create_constraint(new_constraint)
            
            if not saved_constraint:
                print(Fore.RED + "❌ Error al iniciar la restricción.")
                return

            # 2. Agregar reglas específicas
            print(Fore.CYAN + "\nAhora definamos la lógica:")
            print("Ejemplo: Si selecciono 'Proyector' (ID Principal) ENTONCES 'REQUIRES' (Tipo) -> 'Pantalla' (ID Relacionado)")
            
            res_id = int(input("\nID del Recurso Principal: "))
            
            print("\nTipos de regla disponibles:")
            print(" - requires (Si uso A, necesito B)")
            print(" - excludes (Si uso A, NO puedo usar B)")
            rule_type = input("Tipo de regla (requires/excludes): ").lower()
            
            related_id = int(input("ID del Recurso Relacionado: "))
            
            # Crear el diccionario de la regla
            rule = {
                'resource_id': res_id,
                'rule_type': rule_type,
                'related_resource_id': related_id,
                'value': None
            }
            
            # Guardar regla en BD
            if self.constraint_service.add_rule_to_constraint(saved_constraint.id, rule):
                print(Fore.GREEN + f"\n✅ Regla guardada: El recurso {res_id} ahora {rule_type} al recurso {related_id}")
            else:
                print(Fore.RED + "❌ Error al guardar la regla.")

        except ValueError:
            print(Fore.RED + "❌ Error: Debes ingresar números para los IDs.")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")

    # ==========================
    # GESTIÓN DE EVENTOS
    # ==========================
    def view_events(self):
        print(Fore.YELLOW + "\n📅 CALENDARIO DE EVENTOS")
        events = self.event_service.get_all_events()
        
        if not events:
            print("No hay eventos programados.")
            return

        data = []
        for e in events:
            start = e.start_time.strftime("%d/%m %H:%M")
            end = e.end_time.strftime("%H:%M")
            # Obtener nombres de recursos
            res_names = []
            for rid in e.resource_ids:
                r = self.resource_service.get_resource(rid)
                if r: res_names.append(r.name)
            
            data.append([e.id, e.title, f"{start} - {end}", e.status, ", ".join(res_names)])
        
        print(tabulate(data, headers=["ID", "Título", "Horario", "Estado", "Recursos"], tablefmt="simple"))

    def create_event(self):
        print(Fore.YELLOW + "\n➕ NUEVO EVENTO")
        try:
            title = input("Título del evento: ")
            desc = input("Descripción: ")
            
            print(Fore.CYAN + "Formato de fecha: YYYY-MM-DD HH:MM (Ej: 2024-12-25 14:00)")
            start_str = input("Inicio: ")
            duration = int(input("Duración en minutos: "))
            
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end_time = start_time + timedelta(minutes=duration)

            # Selección de recursos
            self.view_resources()
            res_input = input("\nIDs de recursos a usar (separados por coma, o enter para ninguno): ")
            resource_ids = [int(x.strip()) for x in res_input.split(',')] if res_input.strip() else []

            # ==========================================
            # 1. VERIFICAR CONFLICTOS DE HORARIO/CANTIDAD
            # ==========================================
            if resource_ids:
                print(Fore.YELLOW + "🔍 Verificando disponibilidad de horarios...")
                conflict = self.conflict_checker.check_multiple_resources_conflict(
                    resource_ids, start_time, end_time
                )
                
                if conflict['has_conflict']:
                    print(Fore.RED + "\n⛔ ERROR DE DISPONIBILIDAD:")
                    print("Uno o más recursos ya están ocupados en ese horario.")
                    print("Detalles del conflicto:", conflict.get('conflicts'))
                    return # Detener creación

            # ==========================================
            # 2. VERIFICAR RESTRICCIONES (NUEVO)
            # ==========================================
            if resource_ids:
                print(Fore.YELLOW + "🔍 Verificando reglas de negocio (dependencias)...")
                violations = self.constraint_service.validate_resources(resource_ids)
                
                if violations:
                    print(Fore.RED + "\n⛔ ERROR DE REGLAS DE NEGOCIO:")
                    for v in violations:
                        # v['message'] contiene mensajes como "El recurso X requiere el recurso Y"
                        print(f" - {v['message']}")
                    
                    print(Fore.RED + "\nNo se puede crear el evento porque faltan recursos obligatorios o hay incompatibilidades.")
                    return # Detener creación

            # Creación del evento si todo pasa
            new_event = Event(
                title=title,
                description=desc,
                start_time=start_time,
                end_time=end_time,
                resource_ids=resource_ids,
                created_by="admin"
            )
            
            created = self.event_service.create_event(new_event)
            if created:
                print(Fore.GREEN + f"\n✅ Evento '{title}' creado exitosamente (ID: {created.id})")
            else:
                print(Fore.RED + "\n❌ Error al guardar el evento en base de datos.")

        except ValueError as e:
            print(Fore.RED + f"❌ Error de formato: {e}")
        except Exception as e:
            print(Fore.RED + f"❌ Error inesperado: {e}")

    def run(self):
        while True:
            # self.clear_screen()
            self.print_header()
            print("1. 📅 Ver Eventos")
            print("2. ➕ Crear Evento (Con validaciones)")
            print("3. 📦 Ver Recursos")
            print("4. ➕ Crear Recurso")
            print(Fore.MAGENTA + "5. ⛓️  Gestionar Restricciones/Reglas") # Nueva opción
            print(Style.RESET_ALL + "6. 🔧 Inicializar/Resetear Base de Datos")
            print("0. 🚪 Salir")
            
            choice = input("\n👉 Selecciona una opción: ")

            if choice == '1':
                self.view_events()
            elif choice == '2':
                self.create_event()
            elif choice == '3':
                self.view_resources()
            elif choice == '4':
                self.create_resource()
            elif choice == '5':
                self.manage_constraints()
            elif choice == '6':
                confirm = input("¿Seguro? Esto borrará datos existentes si recrea tablas (s/n): ")
                if confirm.lower() == 's':
                    init_db()
            elif choice == '0':
                print("¡Hasta luego!")
                break
            else:
                print(Fore.RED + "Opción inválida.")
            
            input(Fore.BLUE + "\nPresiona ENTER para continuar...")

if __name__ == "__main__":
    try:
        app = EventManagerApp()
        app.run()
    except Exception as e:
        print(f"Error crítico al iniciar: {e}")
        print("Asegúrate de haber configurado el archivo .env y ejecutado initialize.py")