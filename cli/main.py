import sys
import os
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import init, Fore, Style

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, parent_dir)

from database.initialize import main as init_db
from services.event_service import EventService
from services.resource_service import ResourceService
from validators.conflict_checker import ConflictChecker
from services.constraint_service import ConstraintService
from models.event import Event
from models.resource import Resource
from models.constraint import Constraint

init(autoreset=True)

class EventManagerApp:
    def __init__(self):
        self.event_service = EventService()
        self.resource_service = ResourceService()
        self.conflict_checker = ConflictChecker()
        self.constraint_service = ConstraintService()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        print(Fore.CYAN + "=" * 50)
        print(Fore.CYAN + "📅  SISTEMA DE GESTIÓN DE EVENTOS")
        print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)

    def _calculate_recurring_dates(self, start_dt, end_dt, frequency, occurrences):
        """Genera pares (start, end) para eventos recurrentes."""
        dates = []
        current_start = start_dt
        current_end = end_dt
        
        for i in range(occurrences):
            dates.append((current_start, current_end))
            
            if frequency == 'd': # Diario
                current_start += timedelta(days=1)
                current_end += timedelta(days=1)
            elif frequency == 'w': # Semanal
                current_start += timedelta(weeks=1)
                current_end += timedelta(weeks=1)
                
        return dates

    def view_resources(self):
        print(Fore.YELLOW + "\n📋 LISTA DE RECURSOS")
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
            name = input("Nombre: ")
            type_r = input("Tipo (room, equipment, person): ")
            qty = int(input("Cantidad total: "))
            desc = input("Descripción: ")

            res = Resource(name=name, resource_type=type_r, quantity=qty, description=desc)
            if self.resource_service.create_resource(res):
                print(Fore.GREEN + f"\n✅ Recurso '{name}' creado.")
            else:
                print(Fore.RED + "\n❌ Error al crear recurso.")
        except ValueError:
            print(Fore.RED + "❌ Cantidad debe ser un número.")

    def manage_constraints(self):
        print(Fore.MAGENTA + "\n⛓️  GESTIÓN DE RESTRICCIONES")
        self.view_resources()
        print("-" * 30)
        
        try:
            print("\n1. Definir Nueva Regla:")
            name = input("Nombre de la regla: ")
            desc = input("Descripción: ")
            
            new_constraint = Constraint(name=name, constraint_type="co_requirement", description=desc)
            saved = self.constraint_service.create_constraint(new_constraint)
            
            if not saved:
                print(Fore.RED + "❌ Error al iniciar restricción.")
                return

            print(Fore.CYAN + "\nDefinir lógica:")
            res_id = int(input("ID Recurso Principal: "))
            rule_type = input("Tipo (requires/excludes): ").lower()
            related_id = int(input("ID Recurso Relacionado: "))
            
            rule = {
                'resource_id': res_id,
                'rule_type': rule_type,
                'related_resource_id': related_id
            }
            
            if self.constraint_service.add_rule_to_constraint(saved.id, rule):
                print(Fore.GREEN + f"\n✅ Regla guardada.")
            else:
                print(Fore.RED + "❌ Error al guardar regla.")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")

    def view_events(self):
        print(Fore.YELLOW + "\n📅 CALENDARIO")
        events = self.event_service.get_all_events()
        
        if not events:
            print("No hay eventos.")
            return

        data = []
        for e in events:
            start = e.start_time.strftime("%d/%m %H:%M")
            end = e.end_time.strftime("%H:%M")
            res_names = []
            for rid in e.resource_ids:
                r = self.resource_service.get_resource(rid)
                if r: res_names.append(r.name)
            
            data.append([e.id, e.title, f"{start} - {end}", e.status, ", ".join(res_names)])
        
        print(tabulate(data, headers=["ID", "Título", "Horario", "Estado", "Recursos"], tablefmt="simple"))

    def create_event(self):
        print(Fore.YELLOW + "\n➕ NUEVO EVENTO")
        try:
            title = input("Título: ")
            desc = input("Descripción: ")
            
            print(Fore.CYAN + "Formato: YYYY-MM-DD HH:MM")
            start_str = input("Inicio Primer Evento: ")
            duration = int(input("Duración (minutos): "))
            
            base_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            base_end = base_start + timedelta(minutes=duration)

            # Lógica Recurrencia
            is_recurring = input("¿Es recurrente? (s/n): ").lower() == 's'
            frequency = None
            occurrences = 1
            
            if is_recurring:
                print("Frecuencia: (d)iaria, (w)semanal")
                frequency = input("Opción: ").lower()
                occurrences = int(input("Cantidad de repeticiones: "))
                if frequency not in ['d', 'w']:
                    print(Fore.RED + "❌ Frecuencia no soportada.")
                    return

            date_list = self._calculate_recurring_dates(base_start, base_end, frequency, occurrences)
            
            if is_recurring:
                print(Fore.CYAN + f"\nSe crearán {len(date_list)} eventos.")
                print(f"Del {date_list[0][0].date()} al {date_list[-1][0].date()}")

            self.view_resources()
            res_input = input("\nIDs de recursos (coma): ")
            resource_ids = [int(x.strip()) for x in res_input.split(',')] if res_input.strip() else []

            # Validación Masiva (Atomicidad Lógica)
            if resource_ids:
                print(Fore.YELLOW + "🔍 Verificando disponibilidad para TODAS las fechas...")
                
                # 1. Reglas (se validan una sola vez)
                violations = self.constraint_service.validate_resources(resource_ids)
                if violations:
                    print(Fore.RED + "\n⛔ ERROR: Reglas de negocio.")
                    for v in violations: print(f" - {v['message']}")
                    return

                # 2. Conflictos por Fecha
                for i, (s_time, e_time) in enumerate(date_list):
                    conflict = self.conflict_checker.check_multiple_resources_conflict(
                        resource_ids, s_time, e_time
                    )
                    if conflict['has_conflict']:
                        print(Fore.RED + f"\n⛔ CONFLICTO EN REPETICIÓN #{i+1} ({s_time}):")
                        print(f"Detalles: {conflict.get('conflicts')}")
                        print(Fore.RED + "❌ Operación cancelada. No se creó ningún evento.")
                        return

            # Creación Objetos
            events_to_create = []
            for i, (s_time, e_time) in enumerate(date_list):
                final_title = title if not is_recurring else f"{title} ({i+1}/{occurrences})"
                
                new_event = Event(
                    title=final_title,
                    description=desc,
                    start_time=s_time,
                    end_time=e_time,
                    resource_ids=resource_ids,
                    created_by="admin"
                )
                events_to_create.append(new_event)

            # Persistencia en Lote
            print(Fore.YELLOW + "💾 Guardando eventos...")
            count = self.event_service.create_batch_events(events_to_create)
            
            if count == len(events_to_create):
                print(Fore.GREEN + f"\n✅ ÉXITO: {count} eventos creados.")
            else:
                print(Fore.RED + f"\n⚠️ ADVERTENCIA: Solo se crearon {count} de {len(events_to_create)}.")

        except ValueError as e:
            print(Fore.RED + f"❌ Error de formato: {e}")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")

    def edit_event_ui(self):
        print(Fore.YELLOW + "\n✏️  EDITAR EVENTO")
        self.view_events()
        try:
            id_input = input("\nID evento (ENTER volver): ")
            if not id_input.strip(): return
            
            event = self.event_service.get_event(int(id_input))
            if not event:
                print(Fore.RED + "❌ No encontrado.")
                return
            if event.status == 'cancelled':
                print(Fore.RED + "⛔ Evento cancelado.")
                return

            print(Fore.CYAN + "ENTER para mantener valor")
            
            new_title = input(f"Título [{event.title}]: ").strip()
            new_desc = input(f"Descripción [{event.description}]: ").strip()
            
            current_start = event.start_time.strftime("%Y-%m-%d %H:%M")
            new_start_str = input(f"Inicio [{current_start}]: ").strip()
            
            curr_duration = int((event.end_time - event.start_time).total_seconds() / 60)
            new_duration_str = input(f"Duración min [{curr_duration}]: ").strip()
            
            new_start_time = event.start_time
            new_end_time = event.end_time
            times_changed = False
            
            if new_start_str:
                try:
                    new_start_time = datetime.strptime(new_start_str, "%Y-%m-%d %H:%M")
                    times_changed = True
                except ValueError:
                    print(Fore.RED + "❌ Fecha inválida.")
            
            if new_duration_str or times_changed:
                try:
                    dur = int(new_duration_str) if new_duration_str else curr_duration
                    new_end_time = new_start_time + timedelta(minutes=dur)
                    times_changed = True
                except ValueError:
                    print(Fore.RED + "❌ Duración inválida.")

            print(f"Recursos actuales: {event.resource_ids}")
            self.view_resources()
            new_res_input = input("Nuevos IDs (coma, '0' limpiar, ENTER mantener): ").strip()
            
            new_resource_ids = event.resource_ids
            resources_changed = False
            
            if new_res_input:
                try:
                    if new_res_input in ['0', 'none']:
                        new_resource_ids = []
                    else:
                        new_resource_ids = [int(x.strip()) for x in new_res_input.split(',')]
                    resources_changed = True
                except ValueError:
                    print(Fore.RED + "❌ IDs inválidos.")

            if times_changed or resources_changed:
                print(Fore.YELLOW + "🔍 Validando cambios...")
                conflict = self.conflict_checker.check_multiple_resources_conflict(
                    new_resource_ids, new_start_time, new_end_time,
                    exclude_event_id=event.id
                )
                
                if conflict['has_conflict']:
                    print(Fore.RED + "\n⛔ CAMBIO RECHAZADO: Conflicto.")
                    print(f"Detalles: {conflict.get('conflicts')}")
                    return
                
                violations = self.constraint_service.validate_resources(new_resource_ids)
                if violations:
                    print(Fore.RED + "\n⛔ RECHAZADO: Reglas de negocio.")
                    return

            updates = {}
            if new_title: updates['title'] = new_title
            if new_desc: updates['description'] = new_desc
            if times_changed:
                updates['start_time'] = new_start_time
                updates['end_time'] = new_end_time
            if resources_changed:
                updates['resource_ids'] = new_resource_ids
            
            if not updates:
                print("⚠️ Sin cambios.")
                return

            if self.event_service.update_event(event.id, updates):
                print(Fore.GREEN + "✅ Actualizado.")
            else:
                print(Fore.RED + "❌ Error al actualizar.")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")

    def clone_event_ui(self):
        print(Fore.YELLOW + "\n🐑 CLONAR EVENTO")
        self.view_events()
        try:
            id_input = input("\nID evento (ENTER volver): ")
            if not id_input.strip(): return
            
            orig = self.event_service.get_event(int(id_input))
            if not orig:
                print(Fore.RED + "❌ No encontrado.")
                return

            print(Fore.CYAN + f"Clonando: '{orig.title}'")
            start_str = input("Nuevo Inicio (YYYY-MM-DD HH:MM): ")
            
            new_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            duration = orig.end_time - orig.start_time
            new_end = new_start + duration
            
            print(Fore.YELLOW + "🔍 Verificando disponibilidad...")
            conflict = self.conflict_checker.check_multiple_resources_conflict(
                orig.resource_ids, new_start, new_end
            )
            
            if conflict['has_conflict']:
                print(Fore.RED + "\n⛔ IMPOSIBLE CLONAR: Conflicto.")
                print(f"Detalles: {conflict.get('conflicts')}")
                return

            violations = self.constraint_service.validate_resources(orig.resource_ids)
            if violations:
                print(Fore.RED + "\n⛔ REGLAS VIOLADAS.")
                return

            cloned = Event(
                title=f"{orig.title} (Copia)",
                description=orig.description,
                start_time=new_start,
                end_time=new_end,
                resource_ids=orig.resource_ids,
                created_by="admin_clone"
            )

            created = self.event_service.create_event(cloned)
            if created:
                print(Fore.GREEN + f"\n✅ Clonado exitosamente (ID: {created.id})")
            else:
                print(Fore.RED + "❌ Error al clonar.")

        except ValueError:
            print(Fore.RED + "❌ Fecha inválida.")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")

    def cancel_event_ui(self):
        print(Fore.YELLOW + "\n🚫 CANCELAR EVENTO")
        self.view_events()
        try:
            id_input = input("\nID evento (ENTER volver): ")
            if not id_input.strip(): return
            
            event_id = int(id_input)
            if self.event_service.cancel_event(event_id):
                print(Fore.GREEN + "✅ Cancelado.")
            else:
                print(Fore.RED + "❌ Error (ID inválido o ya cancelado).")
        except ValueError:
            print(Fore.RED + "❌ ID inválido.")

    def view_reports_ui(self):
        print(Fore.MAGENTA + "\n📊 REPORTE DE UTILIZACIÓN")
        stats = self.resource_service.get_utilization_stats()
        
        if not stats:
            print("No hay datos.")
            return

        data = []
        for s in stats:
            mins = int(s['total_minutes'])
            time_str = f"{mins // 60}h {mins % 60}m"
            bar = "█" * int(mins / 60)
            if len(bar) > 20: bar = bar[:20] + "+"
            
            data.append([
                s['name'], 
                s['resource_type'], 
                s['total_events'], 
                time_str,
                Fore.BLUE + bar + Style.RESET_ALL
            ])
            
        print(tabulate(data, headers=["Recurso", "Tipo", "Eventos", "Tiempo Total", "Uso"], tablefmt="simple"))

    def run(self):
        while True:
            self.print_header()
            print("1. 📅 Ver Eventos")
            print("2. ➕ Crear Evento")
            print("3. ✏️  Editar Evento")
            print("4. 🐑 Clonar Evento")
            print("5. 🚫 Cancelar Evento")
            print("-" * 25)
            print("6. 📦 Ver Recursos")
            print("7. ➕ Crear Recurso")
            print("8. ⛓️  Gestionar Restricciones")
            print("9. 📊 Ver Reportes")
            print("-" * 25)
            print("10. 🔧 Resetear DB")
            print("0. 🚪 Salir")
            
            choice = input("\n👉 Opción: ")

            if choice == '1': self.view_events()
            elif choice == '2': self.create_event()
            elif choice == '3': self.edit_event_ui()
            elif choice == '4': self.clone_event_ui()
            elif choice == '5': self.cancel_event_ui()
            elif choice == '6': self.view_resources()
            elif choice == '7': self.create_resource()
            elif choice == '8': self.manage_constraints()
            elif choice == '9': self.view_reports_ui()
            elif choice == '10':
                if input("¿Seguro? (s/n): ").lower() == 's': init_db()
            elif choice == '0': break
            else: print(Fore.RED + "Opción inválida.")
            
            input(Fore.BLUE + "\nPresiona ENTER...")

if __name__ == "__main__":
    try:
        app = EventManagerApp()
        app.run()
    except Exception as e:
        print(f"Error crítico: {e}")