// Configuración de la API - usa rutas relativas para Vercel
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : ''; // En Vercel, las rutas /api/ funcionan directamente

let currentTasks = [];
let currentSchedule = null;

const taskForm = document.getElementById('taskForm');
const generateBtn = document.getElementById('generateBtn');
const scheduleContent = document.getElementById('scheduleContent');
const alertsContainer = document.getElementById('alerts');
const taskListContainer = document.getElementById('taskList');

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadExistingTasks();
});

function setupEventListeners() {
    taskForm.addEventListener('submit', handleTaskSubmit);
    generateBtn.addEventListener('click', handleGenerateSchedule);
}

function showAlert(message, type = 'success') {
    alertsContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => alertsContainer.innerHTML = '', 5000);
}

async function handleTaskSubmit(e) {
    e.preventDefault();
    const description = document.getElementById('taskDescription').value.trim();
    const duration = parseInt(document.getElementById('taskDuration').value);
    const deadline = document.getElementById('taskDeadline').value;
    const priority = document.getElementById('taskPriority').value;

    if (!description) {
        showAlert('Por favor, describe la tarea', 'error');
        return;
    }

    const task = {
        description,
        duration,
        priority,
        done: false,
        deadline: deadline || null,
        id: Date.now()
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/add-task`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(task)
        });

        if (response.ok) {
            currentTasks.push(task);
            taskForm.reset();
            showAlert('¡Tarea agregada exitosamente!');
            updateTasksDisplay();
        } else throw new Error();
    } catch {
        showAlert('Error al agregar la tarea', 'error');
    }
}

async function handleGenerateSchedule() {
    if (currentTasks.length === 0) {
        showAlert('Agrega al menos una tarea', 'error');
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = 'Generando...';
    scheduleContent.innerHTML = `<div class="loading"><div class="spinner"></div><p>Generando horario...</p></div>`;

    try {
        const response = await fetch(`${API_BASE_URL}/api/generate-schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        if (response.ok) {
            const result = await response.json();
            currentSchedule = result.schedule;
            displaySchedule(currentSchedule);
            showAlert('¡Horario generado exitosamente!');
        } else throw new Error();
    } catch {
        showAlert('Error generando horario', 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generar Horario Inteligente';
    }
}

function displaySchedule(schedule) {
    if (!schedule || Object.keys(schedule).length === 0) {
        scheduleContent.innerHTML = `<div class="loading"><p>No hay tareas programadas</p></div>`;
        return;
    }

    const sortedDates = Object.keys(schedule).sort();
    let html = '<div class="schedule-grid">';

    sortedDates.forEach(date => {
        const day = new Date(date).toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: '2-digit' });
        html += `<div class="day-schedule"><div class="day-header">${day}</div>`;
        const sortedTimes = Object.keys(schedule[date]).sort();
        sortedTimes.forEach(time => {
            const task = schedule[date][time];
            const deadline = task.deadline ? `<span class="task-deadline">⏰ ${task.deadline}</span>` : '';
            html += `
                <div class="task-item">
                    <div class="task-info">
                        <div class="task-time">${time}</div>
                        <div class="task-description">${task.description}</div>
                        <div class="task-duration">${task.duration}h</div>
                    </div>
                    ${deadline}
                </div>`;
        });
        html += '</div>';
    });

    html += '</div>';
    scheduleContent.innerHTML = html;
}

async function loadExistingTasks() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/tasks`);
        if (response.ok) {
            const data = await response.json();
            currentTasks = data.tasks;
            updateTasksDisplay();
        }
    } catch {
        showAlert('No se pudo cargar las tareas', 'error');
    }
}

async function deleteTask(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/task/${id}`, { method: 'DELETE' });
        if (response.ok) {
            currentTasks = currentTasks.filter(t => t.id !== id);
            updateTasksDisplay();
            await handleGenerateSchedule();
            showAlert('Tarea eliminada');
        }
    } catch {
        showAlert('Error al eliminar tarea', 'error');
    }
}

async function markTaskComplete(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/task/${id}/complete`, { method: 'PUT' });
        if (response.ok) {
            const task = currentTasks.find(t => t.id === id);
            if (task) task.done = true;
            updateTasksDisplay();
            await handleGenerateSchedule();
            showAlert('Tarea completada');
        }
    } catch {
        showAlert('Error al completar tarea', 'error');
    }
}

function updateTasksDisplay() {
    const pendingContainer = document.getElementById('pendingTasks');
    const completedContainer = document.getElementById('completedTasks');

    pendingContainer.innerHTML = '';
    completedContainer.innerHTML = '';

    const createTaskElement = (task) => {
        const div = document.createElement('div');
        div.classList.add('task-item');
        div.innerHTML = `
            <div class="task-info">
                <div class="task-time">${task.deadline ? '⏰ ' + task.deadline : ''}</div>
                <div class="task-description">${task.description}</div>
                <div class="task-duration">${task.duration}h · Prioridad: ${task.priority}</div>
            </div>
            <div>
                ${!task.done ? `<button onclick="markTaskComplete(${task.id})">✔️</button>` : ''}
                <button onclick="deleteTask(${task.id})">🗑️</button>
            </div>
        `;
        return div;
    };

    const pendingTasks = currentTasks.filter(t => !t.done);
    const completedTasks = currentTasks.filter(t => t.done);

    if (pendingTasks.length === 0) {
        pendingContainer.innerHTML = '<p style="color:#999;">Sin tareas pendientes</p>';
    } else {
        pendingTasks.forEach(task => pendingContainer.appendChild(createTaskElement(task)));
    }

    if (completedTasks.length === 0) {
        completedContainer.innerHTML = '<p style="color:#999;">Aún no completaste tareas</p>';
    } else {
        completedTasks.forEach(task => completedContainer.appendChild(createTaskElement(task)));
    }
}