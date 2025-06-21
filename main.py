from flask import Flask, request, jsonify 
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
CORS(app)

@app.route("/api/test")
def test():
    return jsonify({"message": "Funciona desde Vercel ✅"})


# Almacenamiento en memoria (en producción usarías una base de datos)
tasks_storage = []
schedule_storage = {}

def calculate_priority_score(task):
    """Calcula un puntaje de prioridad basado en varios factores"""
    priority_weights = {
        'high': 100,
        'medium': 50,
        'low': 20
    }
    
    base_score = priority_weights.get(task.get('priority', 'medium'), 50)
    
    # Ajustar por deadline si existe - MUY IMPORTANTE
    if task.get('deadline'):
        try:
            deadline_date = datetime.strptime(task['deadline'], '%Y-%m-%d')
            days_until_deadline = (deadline_date - datetime.now()).days
            
            print(f"📅 Tarea: {task['description'][:30]}... Deadline en {days_until_deadline} días")
            
            # Más urgente = MUCHO mayor puntaje
            if days_until_deadline < 0:  # Ya pasó el deadline
                base_score += 1000
            elif days_until_deadline == 0:  # Hoy es el deadline
                base_score += 500
            elif days_until_deadline == 1:  # Deadline mañana
                base_score += 200
            elif days_until_deadline <= 3:
                base_score += 100
            elif days_until_deadline <= 7:
                base_score += 50
                
        except ValueError:
            print(f"❌ Error parsing deadline: {task.get('deadline')}")
    
    print(f"🎯 Tarea: {task['description'][:30]}... Score: {base_score} (Prioridad: {task.get('priority', 'medium')})")
    return base_score

def generate_smart_schedule(tasks):
    """Genera un horario optimizado basado en prioridades y disponibilidad"""
    if not tasks:
        return {}
    
    print("\n🤖 GENERANDO HORARIO INTELIGENTE")
    print(f"📋 Total de tareas recibidas: {len(tasks)}")
    
    # Mostrar tareas antes de ordenar
    print("\n📝 TAREAS ANTES DE ORDENAR:")
    for i, task in enumerate(tasks):
        print(f"  {i+1}. {task['description']} - Prioridad: {task.get('priority', 'N/A')} - Deadline: {task.get('deadline', 'N/A')}")
    
    # Ordenar tareas por prioridad calculada
    sorted_tasks = sorted(tasks, key=calculate_priority_score, reverse=True)
    
    print("\n🎯 TAREAS DESPUÉS DE ORDENAR:")
    for i, task in enumerate(sorted_tasks):
        score = calculate_priority_score(task)
        print(f"  {i+1}. {task['description']} - Score: {score}")
    
    schedule = {}
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Horarios disponibles por día (9 AM a 6 PM)
    available_hours = [f"{hour:02d}:00" for hour in range(9, 18)]
    
    print(f"\n⏰ Horarios disponibles por día: {available_hours}")
    
    for task_idx, task in enumerate(sorted_tasks):
        if task.get('done'):
            continue
            
        print(f"\n📌 Programando tarea {task_idx + 1}: {task['description']}")
        
        # Buscar el mejor slot disponible
        slots_needed = task.get('duration', 1)
        scheduled = False
        
        print(f"   ⏱️ Duración necesaria: {slots_needed} horas")
        
        # Intentar programar hasta 7 días en adelante
        for day_offset in range(7):
            schedule_date = current_date + timedelta(days=day_offset)
            date_str = schedule_date.strftime('%Y-%m-%d')
            
            if date_str not in schedule:
                schedule[date_str] = {}
            
            print(f"   📅 Probando fecha: {date_str}")
            
            # Buscar slots consecutivos disponibles
            for start_hour_idx in range(len(available_hours) - slots_needed + 1):
                # Verificar si hay slots consecutivos disponibles
                consecutive_available = True
                for slot_idx in range(slots_needed):
                    hour = available_hours[start_hour_idx + slot_idx]
                    if hour in schedule[date_str]:
                        consecutive_available = False
                        break
                
                if consecutive_available:
                    print(f"   ✅ Slot encontrado: {available_hours[start_hour_idx]} ({slots_needed}h)")
                    
                    # Asignar la tarea a los slots consecutivos
                    start_hour = available_hours[start_hour_idx]
                    
                    # Para tareas de múltiples horas, solo guardar en el primer slot
                    schedule[date_str][start_hour] = {
                        'id': task.get('id'),
                        'description': task['description'],
                        'duration': task['duration'],
                        'priority': task.get('priority', 'medium'),
                        'deadline': task.get('deadline'),
                        'done': task.get('done', False)
                    }
                    
                    # Marcar los slots adicionales como ocupados (si es necesario)
                    for slot_idx in range(1, slots_needed):
                        hour = available_hours[start_hour_idx + slot_idx]
                        schedule[date_str][hour] = {
                            'id': f"{task.get('id')}_cont",
                            'description': f"(Continuación) {task['description']}",
                            'duration': 0,  # Duración 0 para continuaciones
                            'priority': task.get('priority', 'medium'),
                            'deadline': task.get('deadline'),
                            'done': task.get('done', False)
                        }
                    
                    scheduled = True
                    break
            
            if scheduled:
                break
                
        if not scheduled:
            print(f"   ❌ No se pudo programar: {task['description']}")
    
    # Limpiar días vacíos
    schedule = {date: slots for date, slots in schedule.items() if slots}
    
    print(f"\n✅ HORARIO FINAL GENERADO: {len(schedule)} días programados")
    
    return schedule

@app.route('/api/add-task', methods=['POST'])
def add_task():
    """Agregar una nueva tarea"""
    try:
        task_data = request.get_json()
        
        # Validar datos requeridos
        if not task_data.get('description'):
            return jsonify({'error': 'La descripción es requerida'}), 400
        
        # Agregar timestamp si no tiene ID
        if not task_data.get('id'):
            task_data['id'] = int(datetime.now().timestamp() * 1000)
        
        # Agregar a almacenamiento
        tasks_storage.append(task_data)
        
        return jsonify({
            'success': True,
            'message': 'Tarea agregada exitosamente',
            'task': task_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@app.route('/api/generate-schedule', methods=['POST'])
def generate_schedule():
    """Generar horario optimizado"""
    try:
        # Usar las tareas almacenadas en lugar de los datos del request
        if not tasks_storage:
            return jsonify({
                'success': False,
                'message': 'No hay tareas para programar'
            }), 400
        
        # Generar horario optimizado
        optimized_schedule = generate_smart_schedule(tasks_storage)
        
        # Guardar en storage global
        global schedule_storage
        schedule_storage = optimized_schedule
        
        return jsonify({
            'success': True,
            'message': 'Horario generado exitosamente',
            'schedule': optimized_schedule,
            'tasks_count': len(tasks_storage)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generando horario: {str(e)}'}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Obtener todas las tareas"""
    return jsonify({
        'success': True,
        'tasks': tasks_storage,
        'count': len(tasks_storage)
    })

@app.route('/api/schedule', methods=['GET'])
def get_current_schedule():
    """Obtener el horario actual"""
    return jsonify({
        'success': True,
        'schedule': schedule_storage
    })

@app.route('/api/task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Eliminar una tarea"""
    global tasks_storage
    tasks_storage = [task for task in tasks_storage if task.get('id') != task_id]
    
    return jsonify({
        'success': True,
        'message': 'Tarea eliminada exitosamente'
    })

@app.route('/api/task/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    """Marcar tarea como completada"""
    for task in tasks_storage:
        if task.get('id') == task_id:
            task['done'] = True
            break
    
    return jsonify({
        'success': True,
        'message': 'Tarea marcada como completada'
    })

@app.route('/api/clear', methods=['POST'])
def clear_all_data():
    """Limpiar todas las tareas y horarios (útil para testing)"""
    global tasks_storage, schedule_storage
    tasks_storage = []
    schedule_storage = {}
    
    return jsonify({
        'success': True,
        'message': 'Todos los datos han sido limpiados'
    })

@app.route('/api/', methods=['GET'])
def health_check():
    """Verificar que el servidor esté funcionando"""
    return jsonify({
        'status': 'OK',
        'message': 'Servidor funcionando correctamente',
        'tasks_count': len(tasks_storage)
    })

@app.route("/")
def index():
    return "Backend Flask funcionando en Vercel 🚀"