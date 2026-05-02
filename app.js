const STORAGE_KEY = "homework-hq-state-v2";
const NOTIFICATION_KEY = "homework-hq-notifications-v2";
const STATUS_ORDER = [
  "not_started",
  "in_progress",
  "waiting",
  "completed",
  "submitted",
];
const PRIORITY_SCORE = {
  low: 1,
  medium: 2,
  high: 3,
  urgent: 4,
};
const STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  waiting: "Waiting / blocked",
  completed: "Completed",
  submitted: "Submitted",
};
const SUBMISSION_LABELS = {
  not_submitted: "Not submitted",
  finished: "Finished",
  submitted_online: "Submitted online",
  turned_in_physically: "Turned in physically",
  confirmed: "Confirmed by teacher / LMS",
};
const RECURRENCE_LABELS = {
  none: "One-time",
  daily: "Daily",
  weekly: "Weekly",
  biweekly: "Every 2 weeks",
  weekdays: "Weekdays",
};

const els = {
  classList: document.getElementById("class-list"),
  classCount: document.getElementById("class-count"),
  classForm: document.getElementById("class-form"),
  className: document.getElementById("class-name"),
  classTeacher: document.getElementById("class-teacher"),
  classSchedule: document.getElementById("class-schedule"),
  classColor: document.getElementById("class-color"),
  reminderList: document.getElementById("reminder-list"),
  enableNotifications: document.getElementById("enable-notifications"),
  exportData: document.getElementById("export-data"),
  importData: document.getElementById("import-data"),
  startFresh: document.getElementById("start-fresh"),
  clearCompleted: document.getElementById("clear-completed"),
  dueTodayList: document.getElementById("due-today-list"),
  dueSoonList: document.getElementById("due-soon-list"),
  nextUpList: document.getElementById("next-up-list"),
  dashboardClassCount: document.getElementById("dashboard-class-count"),
  classDashboardList: document.getElementById("class-dashboard-list"),
  taskCount: document.getElementById("task-count"),
  taskList: document.getElementById("task-list"),
  projectCount: document.getElementById("project-count"),
  projectList: document.getElementById("project-list"),
  metricDueToday: document.getElementById("metric-due-today"),
  metricDueTodayNote: document.getElementById("metric-due-today-note"),
  metricDueWeek: document.getElementById("metric-due-week"),
  metricDueWeekNote: document.getElementById("metric-due-week-note"),
  metricOverdue: document.getElementById("metric-overdue"),
  metricOverdueNote: document.getElementById("metric-overdue-note"),
  metricCompleted: document.getElementById("metric-completed"),
  metricCompletedNote: document.getElementById("metric-completed-note"),
  assignmentForm: document.getElementById("assignment-form"),
  formStatus: document.getElementById("form-status"),
  titleInput: document.getElementById("title-input"),
  classInput: document.getElementById("class-input"),
  dueInput: document.getElementById("due-input"),
  priorityInput: document.getElementById("priority-input"),
  statusInput: document.getElementById("status-input"),
  effortInput: document.getElementById("effort-input"),
  weightInput: document.getElementById("weight-input"),
  recurringInput: document.getElementById("recurring-input"),
  naturalInput: document.getElementById("natural-input"),
  searchInput: document.getElementById("search-input"),
  filterClass: document.getElementById("filter-class"),
  filterStatus: document.getElementById("filter-status"),
  filterPriority: document.getElementById("filter-priority"),
  filterAttachments: document.getElementById("filter-attachments"),
  filterOverdue: document.getElementById("filter-overdue"),
  resetFilters: document.getElementById("reset-filters"),
  pageNav: document.getElementById("page-nav"),
  viewTabs: document.getElementById("view-tabs"),
  prevMonth: document.getElementById("prev-month"),
  nextMonth: document.getElementById("next-month"),
  calendarLabel: document.getElementById("calendar-label"),
  calendarGrid: document.getElementById("calendar-grid"),
  assignmentList: document.getElementById("assignment-list"),
  assignmentCount: document.getElementById("assignment-count"),
  detailTitle: document.getElementById("detail-title"),
  detailEmpty: document.getElementById("detail-empty"),
  detailForm: document.getElementById("detail-form"),
  detailAssignmentTitle: document.getElementById("detail-assignment-title"),
  detailClass: document.getElementById("detail-class"),
  detailDue: document.getElementById("detail-due"),
  detailStatus: document.getElementById("detail-status"),
  detailSubmission: document.getElementById("detail-submission"),
  detailPriority: document.getElementById("detail-priority"),
  detailEffort: document.getElementById("detail-effort"),
  detailWeight: document.getElementById("detail-weight"),
  detailAvailability: document.getElementById("detail-availability"),
  detailRecurring: document.getElementById("detail-recurring"),
  detailReminder: document.getElementById("detail-reminder"),
  detailBlocked: document.getElementById("detail-blocked"),
  detailProgress: document.getElementById("detail-progress"),
  detailChecklist: document.getElementById("detail-checklist"),
  detailScore: document.getElementById("detail-score"),
  detailNotes: document.getElementById("detail-notes"),
  detailComments: document.getElementById("detail-comments"),
  detailRubric: document.getElementById("detail-rubric"),
  detailGroup: document.getElementById("detail-group"),
  detailLinks: document.getElementById("detail-links"),
  subtaskList: document.getElementById("subtask-list"),
  addSubtask: document.getElementById("add-subtask"),
  createNextRecurring: document.getElementById("create-next-recurring"),
  deleteAssignment: document.getElementById("delete-assignment"),
  subjectProgress: document.getElementById("subject-progress"),
  weeklySummary: document.getElementById("weekly-summary"),
};

const assignmentTemplate = document.getElementById("assignment-card-template");

let state = loadState();

if (isLikelySeededDemo(state)) {
  state = createEmptyState();
  persistState();
}

function createId(prefix) {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

function todayAt(hour = 17, minute = 0) {
  const date = new Date();
  date.setHours(hour, minute, 0, 0);
  return date.toISOString();
}

function addDays(dateLike, days) {
  const date = new Date(dateLike);
  date.setDate(date.getDate() + days);
  return date;
}

function toLocalInputValue(dateLike) {
  if (!dateLike) return "";
  const date = new Date(dateLike);
  const pad = (value) => `${value}`.padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

function formatDue(dateLike) {
  const date = new Date(dateLike);
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatMonth(dateLike) {
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
  }).format(new Date(dateLike));
}

function isSameDay(a, b) {
  const first = new Date(a);
  const second = new Date(b);
  return (
    first.getFullYear() === second.getFullYear() &&
    first.getMonth() === second.getMonth() &&
    first.getDate() === second.getDate()
  );
}

function startOfDay(dateLike) {
  const date = new Date(dateLike);
  date.setHours(0, 0, 0, 0);
  return date;
}

function endOfDay(dateLike) {
  const date = new Date(dateLike);
  date.setHours(23, 59, 59, 999);
  return date;
}

function startOfWeek(dateLike) {
  const date = startOfDay(dateLike);
  date.setDate(date.getDate() - date.getDay());
  return date;
}

function endOfWeek(dateLike) {
  const date = startOfWeek(dateLike);
  date.setDate(date.getDate() + 6);
  date.setHours(23, 59, 59, 999);
  return date;
}

function differenceInHours(from, to) {
  return (new Date(to).getTime() - new Date(from).getTime()) / 3_600_000;
}

function differenceInDays(from, to) {
  return differenceInHours(from, to) / 24;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hexToRgb(hex) {
  const normalized = (hex || "#ff8a5b").replace("#", "");
  const safe = normalized.length === 3
    ? normalized
        .split("")
        .map((char) => char + char)
        .join("")
    : normalized;

  return {
    r: Number.parseInt(safe.slice(0, 2), 16) || 255,
    g: Number.parseInt(safe.slice(2, 4), 16) || 138,
    b: Number.parseInt(safe.slice(4, 6), 16) || 91,
  };
}

function rgbaFromHex(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function applyClassAccent(element, classItem) {
  const color = classItem?.color || "#ff8a5b";
  element.style.borderLeft = `6px solid ${color}`;
  element.style.background = `linear-gradient(135deg, ${rgbaFromHex(color, 0.2)}, rgba(255, 255, 255, 0.82) 34%)`;
}

function parseLines(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function getClassById(classId) {
  return state.classes.find((item) => item.id === classId) || state.classes[0];
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.classes?.length && parsed?.assignments?.length >= 0) {
        return normalizeState(parsed);
      }
    }
  } catch (error) {
    console.warn("Could not load saved homework data.", error);
  }

  return createEmptyState();
}

function normalizeState(raw) {
  const currentPage =
    raw.ui?.currentPage === "deadlines" ? "assignments" : raw.ui?.currentPage || "home";

  return {
    classes: (raw.classes || []).map((item) => ({
      id: item.id || createId("class"),
      name: item.name || "Class",
      teacher: item.teacher || "",
      schedule: item.schedule || "",
      color: item.color || "#ff8a5b",
      gradingWeight: item.gradingWeight || "",
    })),
    assignments: (raw.assignments || []).map(normalizeAssignment),
    ui: {
      selectedAssignmentId: raw.ui?.selectedAssignmentId || null,
      currentView: raw.ui?.currentView || "today",
      currentMonth: raw.ui?.currentMonth || new Date().toISOString(),
      currentPage,
      search: raw.ui?.search || "",
      filterClass: raw.ui?.filterClass || "all",
      filterStatus: raw.ui?.filterStatus || "all",
      filterPriority: raw.ui?.filterPriority || "all",
      filterAttachments: Boolean(raw.ui?.filterAttachments),
      filterOverdue: Boolean(raw.ui?.filterOverdue),
    },
  };
}

function normalizeAssignment(item) {
  return {
    id: item.id || createId("hw"),
    title: item.title || "Untitled assignment",
    classId: item.classId || "",
    dueAt: item.dueAt || todayAt(),
    status: item.status || "not_started",
    submissionStatus: item.submissionStatus || "not_submitted",
    priority: item.priority || "medium",
    estimatedHours: Number(item.estimatedHours) || 1,
    gradeWeight: Number(item.gradeWeight) || 0,
    availability: item.availability || "normal",
    recurring: item.recurring || "none",
    customReminderAt: item.customReminderAt || "",
    blockedReason: item.blockedReason || "",
    notes: item.notes || "",
    teacherComments: item.teacherComments || "",
    rubric: item.rubric || "",
    groupInfo: item.groupInfo || "",
    resources: Array.isArray(item.resources) ? item.resources : [],
    subtasks: Array.isArray(item.subtasks)
      ? item.subtasks.map((subtask) => ({
          id: subtask.id || createId("subtask"),
          title: subtask.title || "",
          done: Boolean(subtask.done),
        }))
      : [],
    createdAt: item.createdAt || new Date().toISOString(),
    completedAt: item.completedAt || "",
    submittedAt: item.submittedAt || "",
    lastRecurringCloneAt: item.lastRecurringCloneAt || "",
  };
}

function createEmptyState() {
  return normalizeState({
    classes: [],
    assignments: [],
    ui: {
      selectedAssignmentId: null,
      currentView: "today",
      currentMonth: new Date().toISOString(),
      currentPage: "home",
      search: "",
      filterClass: "all",
      filterStatus: "all",
      filterPriority: "all",
      filterAttachments: false,
      filterOverdue: false,
    },
  });
}

function isLikelySeededDemo(currentState) {
  const demoTitles = [
    "History essay",
    "Math worksheet 6.4",
    "Biology lab report",
    "English reading response",
  ];

  return (
    currentState.classes.length === 4 &&
    demoTitles.every((title) =>
      currentState.assignments.some((assignment) => assignment.title === title)
    )
  );
}

function persistState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function getSelectedAssignment() {
  return state.assignments.find((item) => item.id === state.ui.selectedAssignmentId) || null;
}

function saveAndRender() {
  persistState();
  render();
  maybeSendNotifications();
}

function progressForAssignment(assignment) {
  if (assignment.status === "submitted") return 100;
  if (assignment.status === "completed") return 90;
  const total = assignment.subtasks.length;
  if (total === 0) {
    if (assignment.status === "in_progress") return 40;
    if (assignment.status === "waiting") return 25;
    return 0;
  }
  const done = assignment.subtasks.filter((item) => item.done).length;
  const percent = Math.round((done / total) * 100);
  if (assignment.status === "completed") return Math.max(percent, 90);
  return percent;
}

function recommendationScore(assignment) {
  const now = new Date();
  const hoursLeft = differenceInHours(now, assignment.dueAt);
  const dueUrgency = hoursLeft < 0 ? 55 : clamp(48 - hoursLeft, 0, 48);
  const priorityBoost = PRIORITY_SCORE[assignment.priority] * 12;
  const weightBoost = clamp(Number(assignment.gradeWeight) || 0, 0, 25);
  const effortBoost = clamp((Number(assignment.estimatedHours) || 0) * 2.5, 0, 20);
  const waitingPenalty = assignment.status === "waiting" ? -16 : 0;
  const progressPenalty = (progressForAssignment(assignment) / 100) * -18;
  const availabilityBoost =
    assignment.availability === "light"
      ? 8
      : assignment.availability === "busy"
        ? -4
        : 2;
  const submissionPenalty =
    assignment.submissionStatus === "submitted_online" ||
    assignment.submissionStatus === "turned_in_physically" ||
    assignment.submissionStatus === "confirmed"
      ? -25
      : 0;

  return Math.round(
    10 +
      dueUrgency +
      priorityBoost +
      weightBoost +
      effortBoost +
      waitingPenalty +
      progressPenalty +
      availabilityBoost +
      submissionPenalty
  );
}

function isOverdue(assignment) {
  return new Date(assignment.dueAt) < new Date() && assignment.status !== "submitted";
}

function isDueToday(assignment) {
  return isSameDay(assignment.dueAt, new Date());
}

function shouldShowInCurrentView(assignment) {
  const now = new Date();
  const due = new Date(assignment.dueAt);
  const view = state.ui.currentView;

  if (view === "all") return true;
  if (view === "today") return isDueToday(assignment);
  if (view === "week") return due >= startOfWeek(now) && due <= endOfWeek(now);
  if (view === "month") {
    const base = new Date(state.ui.currentMonth);
    return (
      due.getFullYear() === base.getFullYear() && due.getMonth() === base.getMonth()
    );
  }
  if (view === "overdue") return isOverdue(assignment);
  if (view === "upcoming") {
    const hours = differenceInHours(now, assignment.dueAt);
    return hours >= 0 && hours <= 168;
  }

  return true;
}

function filteredAssignments() {
  return [...state.assignments]
    .filter((assignment) => {
      const search = state.ui.search.trim().toLowerCase();
      if (search) {
        const haystack = [
          assignment.title,
          assignment.notes,
          assignment.teacherComments,
          assignment.rubric,
          assignment.groupInfo,
          ...assignment.resources,
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(search)) return false;
      }

      if (state.ui.filterClass !== "all" && assignment.classId !== state.ui.filterClass) {
        return false;
      }

      if (state.ui.filterStatus !== "all" && assignment.status !== state.ui.filterStatus) {
        return false;
      }

      if (state.ui.filterPriority !== "all" && assignment.priority !== state.ui.filterPriority) {
        return false;
      }

      if (state.ui.filterAttachments && assignment.resources.length === 0) return false;
      if (state.ui.filterOverdue && !isOverdue(assignment)) return false;
      if (!shouldShowInCurrentView(assignment)) return false;

      return true;
    })
    .sort((a, b) => {
      const scoreDiff = recommendationScore(b) - recommendationScore(a);
      if (scoreDiff !== 0) return scoreDiff;
      return new Date(a.dueAt) - new Date(b.dueAt);
    });
}

function dashboardAssignments() {
  const active = state.assignments.filter((item) => item.status !== "submitted");
  const dueToday = active
    .filter(isDueToday)
    .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt));
  const dueSoon = active
    .filter((item) => {
      const hours = differenceInHours(new Date(), item.dueAt);
      return hours >= 0 && hours <= 72;
    })
    .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt));
  const nextUp = active
    .filter((item) => item.status !== "completed")
    .sort((a, b) => recommendationScore(b) - recommendationScore(a))
    .slice(0, 3);
  return { dueToday, dueSoon, nextUp };
}

function activeAssignments() {
  return state.assignments
    .filter((item) => item.status !== "submitted")
    .sort((a, b) => recommendationScore(b) - recommendationScore(a));
}

function soonestAssignmentForClass(classId) {
  return activeAssignments()
    .filter((item) => item.classId === classId)
    .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt))[0] || null;
}

function projectAssignments() {
  return activeAssignments().filter(
    (assignment) =>
      assignment.subtasks.length >= 2 || Number(assignment.estimatedHours || 0) >= 2.5
  );
}

function getReminderItems() {
  const reminders = [];
  const now = new Date();

  for (const assignment of state.assignments) {
    const hours = differenceInHours(now, assignment.dueAt);
    const classItem = getClassById(assignment.classId);

    if (assignment.status !== "submitted" && hours >= 0 && hours <= 24) {
      reminders.push({
        id: `${assignment.id}-due-soon`,
        type: "Due soon",
        assignment,
        classItem,
        body: `${assignment.title} is due ${formatDue(assignment.dueAt)}.`,
        severity: 5,
      });
    }

    if (assignment.status === "not_started" && hours > 24 && hours <= 72) {
      reminders.push({
        id: `${assignment.id}-start`,
        type: "Start working",
        assignment,
        classItem,
        body: `Start ${assignment.title} before it becomes a crunch.`,
        severity: 4,
      });
    }

    if (isOverdue(assignment)) {
      reminders.push({
        id: `${assignment.id}-overdue`,
        type: "Overdue",
        assignment,
        classItem,
        body: `${assignment.title} is overdue. Finish and submit it soon.`,
        severity: 6,
      });
    }

    if (assignment.customReminderAt && new Date(assignment.customReminderAt) <= now) {
      reminders.push({
        id: `${assignment.id}-custom`,
        type: "Custom reminder",
        assignment,
        classItem,
        body: `Custom reminder for ${assignment.title}.`,
        severity: 3,
      });
    }

    if (assignment.recurring !== "none" && hours >= 0 && hours <= 48) {
      reminders.push({
        id: `${assignment.id}-recurring`,
        type: "Recurring homework",
        assignment,
        classItem,
        body: `${assignment.title} is part of your ${RECURRENCE_LABELS[assignment.recurring].toLowerCase()} routine.`,
        severity: 2,
      });
    }
  }

  return reminders.sort((a, b) => b.severity - a.severity).slice(0, 6);
}

function notificationCache() {
  try {
    return JSON.parse(localStorage.getItem(NOTIFICATION_KEY) || "{}");
  } catch {
    return {};
  }
}

function storeNotificationCache(cache) {
  localStorage.setItem(NOTIFICATION_KEY, JSON.stringify(cache));
}

function maybeSendNotifications() {
  if (!("Notification" in window) || Notification.permission !== "granted") return;

  const reminders = getReminderItems().slice(0, 3);
  const cache = notificationCache();
  const todayKey = startOfDay(new Date()).toISOString();

  reminders.forEach((reminder) => {
    if (cache[reminder.id] === todayKey) return;

    new Notification(`${reminder.type}: ${reminder.assignment.title}`, {
      body: reminder.body,
    });
    cache[reminder.id] = todayKey;
  });

  storeNotificationCache(cache);
}

function renderClassOptions() {
  const options = state.classes
    .map((item) => `<option value="${item.id}">${item.name}</option>`)
    .join("");
  const emptyOption = '<option value="">Create a class first</option>';

  els.classInput.innerHTML = state.classes.length ? options : emptyOption;
  els.detailClass.innerHTML = state.classes.length ? options : emptyOption;
  els.filterClass.innerHTML = `<option value="all">All classes</option>${options}`;
  els.classInput.disabled = state.classes.length === 0;
  els.detailClass.disabled = state.classes.length === 0;

  if (!state.classes.some((item) => item.id === els.classInput.value)) {
    els.classInput.value = state.classes[0]?.id || "";
  }
  if (!state.classes.some((item) => item.id === els.detailClass.value)) {
    els.detailClass.value = state.classes[0]?.id || "";
  }
  els.filterClass.value = state.ui.filterClass;
}

function renderClasses() {
  els.classCount.textContent = `${state.classes.length} total`;
  els.classList.innerHTML = "";

  if (state.classes.length === 0) {
    els.classList.innerHTML =
      '<div class="empty-state">No classes yet. Create your first class, then start adding assignments.</div>';
    return;
  }

  state.classes.forEach((item) => {
    const activeCount = state.assignments.filter(
      (assignment) => assignment.classId === item.id && assignment.status !== "submitted"
    ).length;
    const card = document.createElement("article");
    card.className = "class-card";
    applyClassAccent(card, item);
    card.innerHTML = `
      <div class="class-card-head">
        <span class="class-color" style="background:${item.color}"></span>
        <strong>${item.name}</strong>
      </div>
      <div class="class-meta">
        <small>${item.teacher || "Teacher not set"}</small>
        <small>${item.schedule || "Schedule not set"}</small>
      </div>
      <small>${activeCount} active assignment${activeCount === 1 ? "" : "s"}</small>
    `;
    els.classList.appendChild(card);
  });
}

function renderDashboard() {
  const { dueToday, dueSoon, nextUp } = dashboardAssignments();
  const dueWeek = state.assignments.filter((item) => {
    const due = new Date(item.dueAt);
    return due >= startOfWeek(new Date()) && due <= endOfWeek(new Date());
  });
  const overdue = state.assignments.filter(isOverdue);
  const completedThisWeek = state.assignments.filter((item) => {
    if (!item.completedAt && !item.submittedAt) return false;
    const stamp = item.submittedAt || item.completedAt;
    return new Date(stamp) >= startOfWeek(new Date());
  });

  els.metricDueToday.textContent = dueToday.length;
  els.metricDueTodayNote.textContent =
    dueToday.length > 0 ? `${dueToday[0].title} is the next deadline.` : "Nothing urgent.";
  els.metricDueWeek.textContent = dueWeek.length;
  els.metricDueWeekNote.textContent =
    dueWeek.length > 0 ? `${dueWeek.length} item${dueWeek.length === 1 ? "" : "s"} on deck.` : "Weekly load is clear.";
  els.metricOverdue.textContent = overdue.length;
  els.metricOverdueNote.textContent =
    overdue.length > 0 ? `${overdue[0].title} needs attention.` : "You are caught up.";
  els.metricCompleted.textContent = completedThisWeek.length;
  els.metricCompletedNote.textContent =
    completedThisWeek.length > 0
      ? "Momentum is building."
      : "Check off your first win this week.";

  renderDashboardList(els.dueTodayList, dueToday, "No homework due today.");
  renderDashboardList(els.dueSoonList, dueSoon.slice(0, 4), "Nothing due in the next 72 hours.");
  renderDashboardList(els.nextUpList, nextUp, "Your queue is clear right now.");
}

function renderDashboardList(container, items, emptyCopy) {
  container.innerHTML = "";
  if (items.length === 0) {
    container.innerHTML = `<div class="empty-state">${emptyCopy}</div>`;
    return;
  }

  items.forEach((assignment) => {
    const classItem = getClassById(assignment.classId);
    const card = document.createElement("article");
    card.className = "dashboard-item";
    applyClassAccent(card, classItem);
    card.innerHTML = `
      <div class="section-head">
        <strong>${assignment.title}</strong>
        <span class="status-pill ${isOverdue(assignment) ? "overdue" : assignment.status === "waiting" ? "waiting" : ""}">${STATUS_LABELS[assignment.status]}</span>
      </div>
      <small>${classItem.name} • ${formatDue(assignment.dueAt)}</small>
      <div class="dashboard-tags">
        <span class="chip">Priority: ${assignment.priority}</span>
        <span class="chip subtle">Score: ${recommendationScore(assignment)}</span>
      </div>
    `;
    card.addEventListener("click", () => {
      state.ui.selectedAssignmentId = assignment.id;
      state.ui.currentPage = "assignments";
      saveAndRender();
    });
    container.appendChild(card);
  });
}

function renderClassDashboard() {
  els.classDashboardList.innerHTML = "";
  els.dashboardClassCount.textContent = `${state.classes.length} classes`;

  if (state.classes.length === 0) {
    els.classDashboardList.innerHTML =
      '<div class="empty-state">Create a class to start building your class dashboard.</div>';
    return;
  }

  state.classes.forEach((classItem) => {
    const assignment = soonestAssignmentForClass(classItem.id);
    const row = document.createElement("article");
    row.className = "class-dashboard-card";

    if (!assignment) {
      applyClassAccent(row, classItem);
      row.innerHTML = `
        <div class="section-head">
          <div class="class-card-head">
            <span class="class-color" style="background:${classItem.color}"></span>
            <strong>${classItem.name}</strong>
          </div>
          <span class="chip subtle">No due work</span>
        </div>
        <small>${classItem.teacher || "Teacher not set"} • ${classItem.schedule || "Schedule not set"}</small>
        <p class="inline-note">No active assignments are due for this class yet.</p>
      `;
      els.classDashboardList.appendChild(row);
      return;
    }

    row.innerHTML = `
      <div class="section-head">
        <div class="class-card-head">
          <span class="class-color" style="background:${classItem.color}"></span>
          <strong>${classItem.name}</strong>
        </div>
        <span class="chip subtle">Score ${recommendationScore(assignment)}</span>
      </div>
      <small>${classItem.teacher || "Teacher not set"} • ${classItem.schedule || "Schedule not set"}</small>
      <h3 class="assignment-title">${assignment.title}</h3>
      <small>Due ${formatDue(assignment.dueAt)}</small>
      <div class="dashboard-tags">
        <span class="status-pill ${isOverdue(assignment) ? "overdue" : assignment.status === "waiting" ? "waiting" : ""}">${STATUS_LABELS[assignment.status]}</span>
        <span class="chip">Priority: ${assignment.priority}</span>
        <span class="chip subtle">${SUBMISSION_LABELS[assignment.submissionStatus]}</span>
      </div>
    `;
    applyClassAccent(row, classItem);
    row.addEventListener("click", () => {
      state.ui.selectedAssignmentId = assignment.id;
      state.ui.currentPage = "assignments";
      saveAndRender();
    });
    els.classDashboardList.appendChild(row);
  });
}

function renderReminders() {
  const reminders = getReminderItems();
  els.reminderList.innerHTML = "";

  if (reminders.length === 0) {
    els.reminderList.innerHTML =
      '<div class="empty-state">No reminders right now. The system is keeping things quiet on purpose.</div>';
    return;
  }

  reminders.forEach((reminder) => {
    const card = document.createElement("article");
    card.className = "reminder-card";
    card.innerHTML = `
      <div class="section-head">
        <strong>${reminder.type}</strong>
        <span class="chip subtle">${reminder.classItem.name}</span>
      </div>
      <p>${reminder.body}</p>
    `;
    els.reminderList.appendChild(card);
  });
}

function renderCalendar() {
  els.calendarGrid.innerHTML = "";
  const base = new Date(state.ui.currentMonth);
  const currentMonth = new Date(base.getFullYear(), base.getMonth(), 1);
  els.calendarLabel.textContent = formatMonth(currentMonth);

  const start = new Date(currentMonth);
  start.setDate(1 - start.getDay());
  const end = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);

  for (let index = 0; index < 42; index += 1) {
    const day = addDays(start, index);
    const dayAssignments = state.assignments
      .filter((item) => isSameDay(item.dueAt, day))
      .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt))
      .slice(0, 3);
    const dayEl = document.createElement("article");
    dayEl.className = "calendar-day";

    if (day.getMonth() !== currentMonth.getMonth()) dayEl.classList.add("muted");
    if (isSameDay(day, new Date())) dayEl.classList.add("today");

    dayEl.innerHTML = `<div class="calendar-day-number">${day.getDate()}</div>`;
    dayAssignments.forEach((assignment) => {
      const classItem = getClassById(assignment.classId);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "calendar-item";
      chip.style.background = classItem.color;
      chip.textContent = assignment.title;
      chip.title = `${assignment.title} • ${formatDue(assignment.dueAt)}`;
      chip.addEventListener("click", () => {
        state.ui.selectedAssignmentId = assignment.id;
        state.ui.currentPage = "assignments";
        saveAndRender();
      });
      dayEl.appendChild(chip);
    });

    if (dayAssignments.length === 0) {
      const spacer = document.createElement("span");
      spacer.className = "small-label";
      spacer.textContent = " ";
      dayEl.appendChild(spacer);
    }

    els.calendarGrid.appendChild(dayEl);
  }
}

function renderAssignments() {
  const assignments = filteredAssignments();
  els.assignmentCount.textContent = `${assignments.length} showing`;
  els.assignmentList.innerHTML = "";

  if (assignments.length === 0) {
    els.assignmentList.innerHTML =
      '<div class="empty-state">No assignments match this filter set.</div>';
    return;
  }

  assignments.forEach((assignment) => {
    const node = assignmentTemplate.content.firstElementChild.cloneNode(true);
    const classItem = getClassById(assignment.classId);
    const progress = progressForAssignment(assignment);
    const done = assignment.subtasks.filter((item) => item.done).length;
    const total = assignment.subtasks.length;

    applyClassAccent(node, classItem);
    node.querySelector(".assignment-class").textContent = classItem.name;
    node.querySelector(".assignment-class").style.color = classItem.color;
    node.querySelector(".assignment-title").textContent = assignment.title;
    node.querySelector(".assignment-score").textContent = `Score ${recommendationScore(assignment)}`;
    node.querySelector(".assignment-meta").textContent = `${formatDue(assignment.dueAt)} • ${SUBMISSION_LABELS[assignment.submissionStatus]}`;

    const tags = node.querySelector(".assignment-tags");
    tags.innerHTML = "";
    [
      `Priority: ${assignment.priority}`,
      STATUS_LABELS[assignment.status],
      assignment.recurring !== "none" ? RECURRENCE_LABELS[assignment.recurring] : "",
      assignment.resources.length ? `${assignment.resources.length} resource${assignment.resources.length === 1 ? "" : "s"}` : "",
    ]
      .filter(Boolean)
      .forEach((label) => {
        const span = document.createElement("span");
        span.className = `status-pill ${label === STATUS_LABELS.waiting ? "waiting" : ""}`;
        if (label === STATUS_LABELS[assignment.status] && isOverdue(assignment)) {
          span.classList.add("overdue");
        }
        span.textContent = label;
        tags.appendChild(span);
      });

    node.querySelector(".progress-bar span").style.width = `${progress}%`;
    node.querySelector(".progress-copy").textContent = `${progress}% complete${
      total ? ` • ${done} / ${total} steps done` : ""
    }`;

    node.querySelector(".select-button").addEventListener("click", () => {
      state.ui.selectedAssignmentId = assignment.id;
      saveAndRender();
    });

    node.querySelector(".toggle-status").addEventListener("click", () => {
      advanceAssignmentStatus(assignment.id);
    });

    if (assignment.id === state.ui.selectedAssignmentId) {
      node.style.outline = `2px solid ${classItem.color}`;
    }

    els.assignmentList.appendChild(node);
  });
}

function renderTasks() {
  const items = activeAssignments().filter(
    (assignment) =>
      assignment.status === "not_started" ||
      assignment.status === "in_progress" ||
      assignment.status === "waiting"
  );

  els.taskCount.textContent = `${items.length} active`;
  els.taskList.innerHTML = "";

  if (items.length === 0) {
    els.taskList.innerHTML =
      '<div class="empty-state">No active tasks right now. New assignments will show up here.</div>';
    return;
  }

  items.forEach((assignment) => {
    const classItem = getClassById(assignment.classId);
    const unfinishedSubtask =
      assignment.subtasks.find((subtask) => !subtask.done)?.title || "No subtasks yet";
    const card = document.createElement("article");
    card.className = "task-card";
    applyClassAccent(card, classItem);
    card.innerHTML = `
      <div class="section-head">
        <div>
          <p class="assignment-class">${classItem.name}</p>
          <h3 class="assignment-title">${assignment.title}</h3>
        </div>
        <span class="chip subtle">Score ${recommendationScore(assignment)}</span>
      </div>
      <small>Due ${formatDue(assignment.dueAt)}</small>
      <div class="dashboard-tags">
        <span class="status-pill ${isOverdue(assignment) ? "overdue" : assignment.status === "waiting" ? "waiting" : ""}">${STATUS_LABELS[assignment.status]}</span>
        <span class="chip">Priority: ${assignment.priority}</span>
      </div>
      <p class="inline-note">Next task: ${unfinishedSubtask}</p>
      <div class="progress-bar"><span style="width:${progressForAssignment(assignment)}%"></span></div>
    `;
    card.querySelector(".assignment-class").style.color = classItem.color;
    card.addEventListener("click", () => {
      state.ui.selectedAssignmentId = assignment.id;
      state.ui.currentPage = "assignments";
      saveAndRender();
    });
    els.taskList.appendChild(card);
  });
}

function renderProjects() {
  const items = projectAssignments();
  els.projectCount.textContent = `${items.length} projects`;
  els.projectList.innerHTML = "";

  if (items.length === 0) {
    els.projectList.innerHTML =
      '<div class="empty-state">Projects will appear here when an assignment has multiple steps or larger effort.</div>';
    return;
  }

  items.forEach((assignment) => {
    const classItem = getClassById(assignment.classId);
    const total = assignment.subtasks.length;
    const done = assignment.subtasks.filter((subtask) => subtask.done).length;
    const nextStep =
      assignment.subtasks.find((subtask) => !subtask.done)?.title || "Add project steps";
    const card = document.createElement("article");
    card.className = "project-card";
    applyClassAccent(card, classItem);
    card.innerHTML = `
      <div class="section-head">
        <div>
          <p class="assignment-class">${classItem.name}</p>
          <h3 class="assignment-title">${assignment.title}</h3>
        </div>
        <span class="chip subtle">Score ${recommendationScore(assignment)}</span>
      </div>
      <small>Due ${formatDue(assignment.dueAt)}</small>
      <div class="dashboard-tags">
        <span class="status-pill ${isOverdue(assignment) ? "overdue" : assignment.status === "waiting" ? "waiting" : ""}">${STATUS_LABELS[assignment.status]}</span>
        <span class="chip">Priority: ${assignment.priority}</span>
        <span class="chip subtle">${total ? `${done} / ${total} steps` : `${assignment.estimatedHours}h est.`}</span>
      </div>
      <p class="inline-note">Next step: ${nextStep}</p>
      <div class="progress-bar"><span style="width:${progressForAssignment(assignment)}%"></span></div>
    `;
    card.querySelector(".assignment-class").style.color = classItem.color;
    card.addEventListener("click", () => {
      state.ui.selectedAssignmentId = assignment.id;
      state.ui.currentPage = "assignments";
      saveAndRender();
    });
    els.projectList.appendChild(card);
  });
}

function renderDetail() {
  const assignment = getSelectedAssignment();
  if (!assignment) {
    els.detailTitle.textContent = "Select an assignment";
    els.detailTitle.style.background = "";
    els.detailTitle.style.color = "";
    els.detailEmpty.classList.remove("hidden");
    els.detailForm.classList.add("hidden");
    return;
  }

  const classItem = getClassById(assignment.classId);
  els.detailTitle.textContent = assignment.title;
  els.detailTitle.style.background = rgbaFromHex(classItem.color, 0.16);
  els.detailTitle.style.color = classItem.color;
  els.detailEmpty.classList.add("hidden");
  els.detailForm.classList.remove("hidden");

  els.detailAssignmentTitle.value = assignment.title;
  els.detailClass.value = assignment.classId;
  els.detailDue.value = toLocalInputValue(assignment.dueAt);
  els.detailStatus.value = assignment.status;
  els.detailSubmission.value = assignment.submissionStatus;
  els.detailPriority.value = assignment.priority;
  els.detailEffort.value = assignment.estimatedHours;
  els.detailWeight.value = assignment.gradeWeight;
  els.detailAvailability.value = assignment.availability;
  els.detailRecurring.value = assignment.recurring;
  els.detailReminder.value = toLocalInputValue(assignment.customReminderAt);
  els.detailBlocked.value = assignment.blockedReason;
  els.detailNotes.value = assignment.notes;
  els.detailComments.value = assignment.teacherComments;
  els.detailRubric.value = assignment.rubric;
  els.detailGroup.value = assignment.groupInfo;
  els.detailLinks.value = assignment.resources.join("\n");
  els.detailProgress.textContent = `${progressForAssignment(assignment)}%`;
  els.detailChecklist.textContent = `${assignment.subtasks.filter((item) => item.done).length} / ${assignment.subtasks.length}`;
  els.detailScore.textContent = recommendationScore(assignment);

  els.subtaskList.innerHTML = "";
  assignment.subtasks.forEach((subtask) => {
    const row = document.createElement("div");
    row.className = "subtask-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = subtask.done;
    checkbox.addEventListener("change", () => {
      subtask.done = checkbox.checked;
      saveAndRender();
    });

    const input = document.createElement("input");
    input.type = "text";
    input.value = subtask.title;
    input.placeholder = "Step";
    input.addEventListener("input", () => {
      subtask.title = input.value;
      persistState();
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost-button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      assignment.subtasks = assignment.subtasks.filter((item) => item.id !== subtask.id);
      saveAndRender();
    });

    row.append(checkbox, input, remove);
    els.subtaskList.appendChild(row);
  });
}

function renderSubjectProgress() {
  els.subjectProgress.innerHTML = "";

  if (state.classes.length === 0) {
    els.subjectProgress.innerHTML =
      '<div class="empty-state">Subject progress will appear after you create classes and assignments.</div>';
    return;
  }

  state.classes.forEach((classItem) => {
    const items = state.assignments.filter((assignment) => assignment.classId === classItem.id);
    const completed = items.filter((assignment) => assignment.status === "submitted").length;
    const overdue = items.filter(isOverdue).length;
    const averageProgress =
      items.length === 0
        ? 0
        : Math.round(items.reduce((sum, item) => sum + progressForAssignment(item), 0) / items.length);

    const row = document.createElement("article");
    row.className = "subject-row";
    row.innerHTML = `
      <div class="subject-row-top">
        <strong>${classItem.name}</strong>
        <span class="chip subtle">${overdue} overdue</span>
      </div>
      <small>${completed} submitted • ${items.length} total assignments</small>
      <div class="progress-bar"><span style="width:${averageProgress}%; background:${classItem.color}"></span></div>
      <small>${averageProgress}% average completion</small>
    `;
    els.subjectProgress.appendChild(row);
  });
}

function renderWeeklySummary() {
  const active = state.assignments.filter((item) => item.status !== "submitted");
  const totalHours = active.reduce((sum, item) => sum + (Number(item.estimatedHours) || 0), 0);
  const waiting = active.filter((item) => item.status === "waiting").length;
  const highPriority = active.filter(
    (item) => item.priority === "high" || item.priority === "urgent"
  ).length;

  const rows = [
    ["Estimated workload", `${totalHours.toFixed(1)} hours`],
    ["Blocked assignments", `${waiting}`],
    ["High-priority work", `${highPriority}`],
    ["Upcoming due dates", `${dashboardAssignments().dueSoon.length}`],
  ];

  els.weeklySummary.innerHTML = "";
  if (state.assignments.length === 0) {
    els.weeklySummary.innerHTML =
      '<div class="empty-state">Your weekly summary will fill in as you add homework.</div>';
    return;
  }
  rows.forEach(([label, value]) => {
    const row = document.createElement("article");
    row.className = "summary-row";
    row.innerHTML = `<strong>${label}</strong><small>${value}</small>`;
    els.weeklySummary.appendChild(row);
  });
}

function renderFilters() {
  els.searchInput.value = state.ui.search;
  els.filterStatus.value = state.ui.filterStatus;
  els.filterPriority.value = state.ui.filterPriority;
  els.filterAttachments.checked = state.ui.filterAttachments;
  els.filterOverdue.checked = state.ui.filterOverdue;

  [...els.viewTabs.querySelectorAll(".tab")].forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === state.ui.currentView);
  });
}

function renderPageNavigation() {
  document.querySelectorAll(".app-page").forEach((page) => {
    page.classList.toggle("active", page.id === `page-${state.ui.currentPage}`);
  });

  [...els.pageNav.querySelectorAll(".page-link")].forEach((button) => {
    button.classList.toggle("active", button.dataset.page === state.ui.currentPage);
  });
}

function render() {
  renderPageNavigation();
  renderClassOptions();
  renderClasses();
  renderFilters();
  renderDashboard();
  renderClassDashboard();
  renderReminders();
  renderCalendar();
  renderTasks();
  renderProjects();
  renderAssignments();
  renderDetail();
  renderSubjectProgress();
  renderWeeklySummary();
}

function advanceAssignmentStatus(id) {
  const assignment = state.assignments.find((item) => item.id === id);
  if (!assignment) return;

  const currentIndex = STATUS_ORDER.indexOf(assignment.status);
  const nextStatus = STATUS_ORDER[Math.min(currentIndex + 1, STATUS_ORDER.length - 1)];
  assignment.status = nextStatus;

  if (nextStatus === "completed" && !assignment.completedAt) {
    assignment.completedAt = new Date().toISOString();
  }

  if (nextStatus === "submitted") {
    assignment.submittedAt = new Date().toISOString();
    if (assignment.submissionStatus === "not_submitted") {
      assignment.submissionStatus = "submitted_online";
    }
    ensureNextRecurringAssignment(assignment);
  }

  saveAndRender();
}

function ensureNextRecurringAssignment(assignment) {
  if (assignment.recurring === "none") return;
  const nextDue = getNextRecurringDate(assignment.dueAt, assignment.recurring);
  if (!nextDue) return;

  const exists = state.assignments.some(
    (item) =>
      item.id !== assignment.id &&
      item.title === assignment.title &&
      item.classId === assignment.classId &&
      isSameDay(item.dueAt, nextDue)
  );

  if (exists) return;

  state.assignments.push(
    normalizeAssignment({
      ...assignment,
      id: createId("hw"),
      dueAt: nextDue.toISOString(),
      status: "not_started",
      submissionStatus: "not_submitted",
      completedAt: "",
      submittedAt: "",
      customReminderAt: "",
      subtasks: assignment.subtasks.map((item) => ({
        ...item,
        id: createId("subtask"),
        done: false,
      })),
      createdAt: new Date().toISOString(),
      lastRecurringCloneAt: new Date().toISOString(),
    })
  );
}

function getNextRecurringDate(dateLike, recurring) {
  const date = new Date(dateLike);

  if (recurring === "daily") {
    date.setDate(date.getDate() + 1);
    return date;
  }
  if (recurring === "weekly") {
    date.setDate(date.getDate() + 7);
    return date;
  }
  if (recurring === "biweekly") {
    date.setDate(date.getDate() + 14);
    return date;
  }
  if (recurring === "weekdays") {
    date.setDate(date.getDate() + 1);
    while (date.getDay() === 0 || date.getDay() === 6) {
      date.setDate(date.getDate() + 1);
    }
    return date;
  }
  return null;
}

function upsertAssignment(data) {
  state.assignments.unshift(normalizeAssignment(data));
  state.ui.selectedAssignmentId = state.assignments[0].id;
  saveAndRender();
}

function readNaturalLanguageInput(value) {
  if (!value.trim()) return {};
  const raw = value.trim();
  const lower = raw.toLowerCase();
  const patterns = [
    { token: "today", date: new Date() },
    { token: "tomorrow", date: addDays(new Date(), 1) },
    { token: "friday", date: nextWeekday(5) },
    { token: "monday", date: nextWeekday(1) },
    { token: "tuesday", date: nextWeekday(2) },
    { token: "wednesday", date: nextWeekday(3) },
    { token: "thursday", date: nextWeekday(4) },
    { token: "saturday", date: nextWeekday(6) },
    { token: "sunday", date: nextWeekday(0) },
  ];

  const matched = patterns.find((item) => lower.includes(item.token));
  const hourMatch = lower.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/);

  if (!matched) return { title: raw };

  const due = new Date(matched.date);
  due.setHours(17, 0, 0, 0);
  if (hourMatch) {
    let hour = Number(hourMatch[1]);
    const minute = Number(hourMatch[2] || 0);
    const meridiem = hourMatch[3];
    if (meridiem === "pm" && hour !== 12) hour += 12;
    if (meridiem === "am" && hour === 12) hour = 0;
    due.setHours(hour, minute, 0, 0);
  }

  const title = raw
    .replace(hourMatch?.[0] || "", "")
    .replace(matched.token, "")
    .trim()
    .replace(/\s+/g, " ");

  return {
    title: title || raw,
    dueAt: due.toISOString(),
  };
}

function nextWeekday(targetDay) {
  const date = new Date();
  const current = date.getDay();
  let diff = targetDay - current;
  if (diff <= 0) diff += 7;
  date.setDate(date.getDate() + diff);
  return date;
}

function onAddAssignment(event) {
  event.preventDefault();

  if (state.classes.length === 0) {
    els.formStatus.textContent = "Create a class first, then add your assignment.";
    return;
  }

  const natural = readNaturalLanguageInput(els.naturalInput.value);
  const title = natural.title || els.titleInput.value.trim();
  const dueAt = natural.dueAt || new Date(els.dueInput.value).toISOString();

  if (!title || !els.classInput.value || !els.dueInput.value && !natural.dueAt) {
    els.formStatus.textContent = "Add a title, class, and due date to save the assignment.";
    return;
  }

  upsertAssignment({
    title,
    classId: els.classInput.value,
    dueAt,
    priority: els.priorityInput.value,
    status: els.statusInput.value,
    submissionStatus: els.statusInput.value === "submitted" ? "submitted_online" : "not_submitted",
    estimatedHours: Number(els.effortInput.value) || 1,
    gradeWeight: Number(els.weightInput.value) || 0,
    recurring: els.recurringInput.value,
    availability: "normal",
    resources: [],
    subtasks: [],
  });

  els.assignmentForm.reset();
  els.classInput.value = state.classes[0]?.id || "";
  els.recurringInput.value = "none";
  els.priorityInput.value = "medium";
  els.statusInput.value = "not_started";
  els.dueInput.value = toLocalInputValue(addDays(new Date(), 1));
  els.formStatus.textContent = `"${title}" added to your plan.`;
}

function onSaveDetail(event) {
  event.preventDefault();
  const assignment = getSelectedAssignment();
  if (!assignment) return;

  assignment.title = els.detailAssignmentTitle.value.trim() || assignment.title;
  assignment.classId = els.detailClass.value;
  assignment.dueAt = new Date(els.detailDue.value).toISOString();
  assignment.status = els.detailStatus.value;
  assignment.submissionStatus = els.detailSubmission.value;
  assignment.priority = els.detailPriority.value;
  assignment.estimatedHours = Number(els.detailEffort.value) || 0;
  assignment.gradeWeight = Number(els.detailWeight.value) || 0;
  assignment.availability = els.detailAvailability.value;
  assignment.recurring = els.detailRecurring.value;
  assignment.customReminderAt = els.detailReminder.value
    ? new Date(els.detailReminder.value).toISOString()
    : "";
  assignment.blockedReason = els.detailBlocked.value.trim();
  assignment.notes = els.detailNotes.value.trim();
  assignment.teacherComments = els.detailComments.value.trim();
  assignment.rubric = els.detailRubric.value.trim();
  assignment.groupInfo = els.detailGroup.value.trim();
  assignment.resources = parseLines(els.detailLinks.value);

  if (assignment.status === "completed" && !assignment.completedAt) {
    assignment.completedAt = new Date().toISOString();
  }
  if (assignment.status === "submitted" && !assignment.submittedAt) {
    assignment.submittedAt = new Date().toISOString();
    ensureNextRecurringAssignment(assignment);
  }

  saveAndRender();
}

function addSubtask() {
  const assignment = getSelectedAssignment();
  if (!assignment) return;
  assignment.subtasks.push({
    id: createId("subtask"),
    title: "New step",
    done: false,
  });
  saveAndRender();
}

function deleteSelectedAssignment() {
  const assignment = getSelectedAssignment();
  if (!assignment) return;
  state.assignments = state.assignments.filter((item) => item.id !== assignment.id);
  state.ui.selectedAssignmentId = state.assignments[0]?.id || null;
  saveAndRender();
}

function clearSubmittedAssignments() {
  state.assignments = state.assignments.filter((item) => item.status !== "submitted");
  if (!state.assignments.some((item) => item.id === state.ui.selectedAssignmentId)) {
    state.ui.selectedAssignmentId = state.assignments[0]?.id || null;
  }
  saveAndRender();
}

function exportState() {
  const blob = new Blob([JSON.stringify(state, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `homework-hq-export-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function importState(event) {
  const [file] = event.target.files || [];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result);
      state = normalizeState(parsed);
      saveAndRender();
    } catch (error) {
      els.formStatus.textContent = "That file could not be imported.";
    }
  };
  reader.readAsText(file);
}

function resetFilters() {
  state.ui.search = "";
  state.ui.filterClass = "all";
  state.ui.filterStatus = "all";
  state.ui.filterPriority = "all";
  state.ui.filterAttachments = false;
  state.ui.filterOverdue = false;
  state.ui.currentView = "today";
  saveAndRender();
}

function startFresh() {
  state = createEmptyState();
  localStorage.removeItem(NOTIFICATION_KEY);
  saveAndRender();
  els.formStatus.textContent = "Planner cleared. Add your classes and assignments when you're ready.";
}

function bindEvents() {
  els.classForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = els.className.value.trim();
    if (!name) return;

    state.classes.push({
      id: createId("class"),
      name,
      teacher: els.classTeacher.value.trim(),
      schedule: els.classSchedule.value.trim(),
      color: els.classColor.value,
      gradingWeight: "",
    });
    els.classForm.reset();
    els.classColor.value = "#ff8a5b";
    saveAndRender();
  });

  els.assignmentForm.addEventListener("submit", onAddAssignment);
  els.detailForm.addEventListener("submit", onSaveDetail);
  els.addSubtask.addEventListener("click", addSubtask);
  els.deleteAssignment.addEventListener("click", deleteSelectedAssignment);
  els.createNextRecurring.addEventListener("click", () => {
    const assignment = getSelectedAssignment();
    if (!assignment) return;
    ensureNextRecurringAssignment(assignment);
    saveAndRender();
  });
  els.clearCompleted.addEventListener("click", clearSubmittedAssignments);
  els.exportData.addEventListener("click", exportState);
  els.importData.addEventListener("change", importState);
  els.startFresh.addEventListener("click", startFresh);
  els.resetFilters.addEventListener("click", resetFilters);

  els.searchInput.addEventListener("input", (event) => {
    state.ui.search = event.target.value;
    saveAndRender();
  });
  els.filterClass.addEventListener("change", (event) => {
    state.ui.filterClass = event.target.value;
    saveAndRender();
  });
  els.filterStatus.addEventListener("change", (event) => {
    state.ui.filterStatus = event.target.value;
    saveAndRender();
  });
  els.filterPriority.addEventListener("change", (event) => {
    state.ui.filterPriority = event.target.value;
    saveAndRender();
  });
  els.filterAttachments.addEventListener("change", (event) => {
    state.ui.filterAttachments = event.target.checked;
    saveAndRender();
  });
  els.filterOverdue.addEventListener("change", (event) => {
    state.ui.filterOverdue = event.target.checked;
    saveAndRender();
  });

  els.viewTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".tab");
    if (!button) return;
    state.ui.currentView = button.dataset.view;
    state.ui.currentPage = "assignments";
    saveAndRender();
  });

  els.pageNav.addEventListener("click", (event) => {
    const button = event.target.closest(".page-link");
    if (!button) return;
    state.ui.currentPage = button.dataset.page;
    saveAndRender();
  });

  els.prevMonth.addEventListener("click", () => {
    const date = new Date(state.ui.currentMonth);
    date.setMonth(date.getMonth() - 1);
    state.ui.currentMonth = date.toISOString();
    state.ui.currentPage = "calendar";
    saveAndRender();
  });

  els.nextMonth.addEventListener("click", () => {
    const date = new Date(state.ui.currentMonth);
    date.setMonth(date.getMonth() + 1);
    state.ui.currentMonth = date.toISOString();
    state.ui.currentPage = "calendar";
    saveAndRender();
  });

  els.enableNotifications.addEventListener("click", async () => {
    if (!("Notification" in window)) {
      els.formStatus.textContent = "This browser does not support notifications.";
      return;
    }
    const result = await Notification.requestPermission();
    els.formStatus.textContent =
      result === "granted"
        ? "Browser notifications are on."
        : "Notifications were not enabled.";
    maybeSendNotifications();
  });
}

function initializeDefaults() {
  els.dueInput.value = toLocalInputValue(addDays(new Date(), 1));
}

bindEvents();
initializeDefaults();
render();
maybeSendNotifications();
