/* Scholarly App — Core + Dashboard + Students */
initThemeToggle('theme-toggle');
if(!isLoggedIn()) window.location.href='/';

let currentTeacher=null;
let scoreConfig=null;
const COLORS=['#6366f1','#8b5cf6','#ec4899','#f59e0b','#22c55e','#06b6d4','#ef4444'];

// ── NAV ────────────────────────────────
document.querySelectorAll('.nav-item[data-page]').forEach(btn=>{
  btn.addEventListener('click',()=>navigateTo(btn.dataset.page));
});
function navigateTo(page){
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const nav=document.querySelector(`[data-page="${page}"]`);
  if(nav) nav.classList.add('active');
  document.querySelectorAll('.page-section').forEach(s=>s.classList.remove('active'));
  const sec=document.getElementById('page-'+page);
  if(sec) sec.classList.add('active');
  const titles={dashboard:'Dashboard',students:'Students',attendance:'Attendance',exams:'Exam Scores',analytics:'Analytics',schedule:'Schedule',admin:'Manage Accounts'};
  document.getElementById('page-title').textContent=titles[page]||page;
  const loaders={dashboard:loadDashboard,students:loadStudents,attendance:loadAttendance,exams:loadExams,analytics:loadAnalytics,schedule:loadSchedule,admin:loadAdmin};
  if(loaders[page]) loaders[page]();
}

// ── PROFILE DROPDOWN ───────────────────
const profTrigger=document.getElementById('profile-trigger');
const profDD=document.getElementById('profile-dropdown');
profTrigger.addEventListener('click',e=>{e.stopPropagation();profDD.classList.toggle('hidden')});
document.addEventListener('click',()=>profDD.classList.add('hidden'));
profDD.addEventListener('click',e=>e.stopPropagation());
document.getElementById('dd-logout-btn').addEventListener('click',logout);
document.getElementById('dd-theme-btn').addEventListener('click',()=>{
  const c=document.documentElement.getAttribute('data-theme');
  const n=c==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',n);
  localStorage.setItem('scholarly_theme',n);
});

// ── MOBILE SIDEBAR ─────────────────────
const sidebarToggle=document.getElementById('sidebar-toggle');
const sidebar=document.getElementById('sidebar');
if(window.innerWidth<=768) sidebarToggle.style.display='flex';
sidebarToggle.addEventListener('click',()=>sidebar.classList.toggle('open'));

// ── INIT ───────────────────────────────
async function init(){
  try{
    currentTeacher=await apiGetMe();
    scoreConfig=await apiGetScoreConfig();
    document.getElementById('topbar-avatar').textContent=currentTeacher.initials;
    document.getElementById('topbar-name').textContent=currentTeacher.full_name.split(' ')[0];
    document.getElementById('dd-name').textContent=currentTeacher.full_name;
    document.getElementById('dd-class').textContent=currentTeacher.class_section?'Class '+currentTeacher.class_section:'No class assigned';
    if(currentTeacher.is_admin){
      const adminNav=document.getElementById('admin-nav-section');
      if(adminNav) adminNav.classList.remove('hidden');
    }
    loadDashboard();
  }catch(e){
    document.getElementById('app-main').innerHTML='<div class="loading">Failed to load. <a href="/" style="color:var(--primary)">Sign in again</a></div>';
  }
}
init();

// ── GREETING ───────────────────────────
function getGreeting(){
  const h=new Date().getHours();
  if(h<12) return 'Good Morning';
  if(h<17) return 'Good Afternoon';
  return 'Good Evening';
}

// ── DASHBOARD ──────────────────────────
async function loadDashboard(){
  const pg=document.getElementById('page-dashboard');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const ov=await apiGetClassOverview();
    const events=await apiGetEvents();
    const attSum=await apiGetAttendanceSummary();
    const name=currentTeacher.full_name.split(' ')[0];
    const avgAtt=attSum.length?Math.round(attSum.reduce((a,b)=>a+b.percentage,0)/attSum.length):0;
    const upcoming=events.filter(e=>new Date(e.event_date)>=new Date()).slice(0,3);
    
    let trendCounts={improving:0,declining:0,stable:0};
    ov.students.forEach(s=>trendCounts[s.overall_trend]=(trendCounts[s.overall_trend]||0)+1);

    pg.innerHTML=`
      <div class="greeting-big" style="text-align:left;margin-bottom:1.5rem">
        <span>${getGreeting()},</span> ${name} 👋
      </div>
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">Students</div><div class="stat-value">${ov.total_students}</div><div class="stat-sub">Class ${ov.class}-${ov.section}</div></div>
        <div class="stat-card"><div class="stat-label">Avg Attendance</div><div class="stat-value">${avgAtt}%</div><div class="stat-sub">${attSum.length} students tracked</div></div>
        <div class="stat-card"><div class="stat-label">Improving</div><div class="stat-value trend-up">${trendCounts.improving}</div><div class="stat-sub">students trending up</div></div>
        <div class="stat-card"><div class="stat-label">Need Attention</div><div class="stat-value trend-down">${trendCounts.declining}</div><div class="stat-sub">students declining</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
        <div class="card">
          <div class="card-header"><div class="card-title">Class Overview</div></div>
          <div id="dash-students-list"></div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Upcoming</div></div>
          <div id="dash-events-list"></div>
        </div>
      </div>`;
    
    const sl=document.getElementById('dash-students-list');
    if(!ov.students.length) sl.innerHTML='<div class="empty-state"><div class="empty-icon">📚</div><div class="empty-text">No students yet</div></div>';
    else sl.innerHTML=ov.students.slice(0,6).map(s=>`
      <div class="student-card" onclick="navigateTo('analytics');setTimeout(()=>loadStudentAnalytics(${s.student_id}),200)">
        <div class="student-avatar">${s.initials}</div>
        <div class="student-info"><div class="s-name">${s.student_name}</div><div class="s-meta">${s.roll_number||''} · Att: ${s.attendance_pct}%</div></div>
        <span class="badge ${s.overall_trend==='improving'?'badge-green':s.overall_trend==='declining'?'badge-red':'badge-yellow'}">${s.overall_trend}</span>
      </div>`).join('');

    const el=document.getElementById('dash-events-list');
    if(!upcoming.length) el.innerHTML='<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-text">No upcoming events</div></div>';
    else el.innerHTML=upcoming.map(ev=>renderEventCard(ev)).join('');
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-text">${e.message}</div></div>`}
}

function renderEventCard(ev){
  const d=new Date(ev.event_date);
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `<div class="event-card">
    <div class="event-date-badge"><div class="edb-day">${d.getDate()}</div><div class="edb-month">${months[d.getMonth()]}</div></div>
    <div class="event-info"><div class="ei-title">${ev.title} <span class="event-type-badge ${ev.event_type}">${ev.event_type}</span></div><div class="ei-meta">Class ${ev.target_class||'—'}-${ev.target_section||'—'}</div>${ev.description?`<div class="ei-desc">${ev.description}</div>`:''}</div>
  </div>`;
}

// ── STUDENTS ───────────────────────────
async function loadStudents(){
  const pg=document.getElementById('page-students');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const students=await apiGetStudents();
    pg.innerHTML=`
      <div class="toolbar">
        <input class="toolbar-search" id="student-search" placeholder="Search students…">
        <button class="btn btn-primary" id="btn-add-student">+ Add Student</button>
      </div>
      <div id="student-form-area"></div>
      <div id="student-list"></div>`;
    renderStudentList(students);
    document.getElementById('student-search').addEventListener('input',async e=>{
      const s=await apiGetStudents(e.target.value);renderStudentList(s);
    });
    document.getElementById('btn-add-student').addEventListener('click',showStudentForm);
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-text">${e.message}</div></div>`}
}

function renderStudentList(students){
  const el=document.getElementById('student-list');
  if(!students.length){el.innerHTML='<div class="empty-state"><div class="empty-icon">👨‍🎓</div><div class="empty-text">No students found</div><div class="empty-sub">Add students to get started</div></div>';return}
  el.innerHTML=students.map(s=>`
    <div class="student-card">
      <div class="student-avatar">${s.initials}</div>
      <div class="student-info">
        <div class="s-name">${s.name}</div>
        <div class="s-meta">Roll: ${s.roll_number||'—'} · ${s.class_section}</div>
      </div>
      <div class="btn-row">
        <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation();editStudent(${s.id},'${s.name.replace(/'/g,"\\'")}','${s.roll_number||''}','${(s.remarks||'').replace(/'/g,"\\'")}')">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();deleteStudentConfirm(${s.id},'${s.name.replace(/'/g,"\\'")}')">Del</button>
      </div>
    </div>`).join('');
}

function showStudentForm(name,roll,remarks,id){
  const area=document.getElementById('student-form-area');
  const isEdit=!!id;
  area.innerHTML=`<div class="form-panel">
    <div class="form-panel-title">${isEdit?'Edit':'Add'} Student</div>
    <div class="form-grid">
      <div class="form-group"><label>Name</label><input id="sf-name" value="${name||''}" placeholder="Full name" required></div>
      <div class="form-group"><label>Roll Number</label><input id="sf-roll" value="${roll||''}" placeholder="Optional"></div>
    </div>
    <div class="form-group"><label>Remarks</label><textarea id="sf-remarks" rows="2" placeholder="Teacher notes…">${remarks||''}</textarea></div>
    <div class="form-actions">
      <button class="btn btn-primary" id="sf-submit">${isEdit?'Update':'Add'} Student</button>
      <button class="btn btn-secondary" onclick="document.getElementById('student-form-area').innerHTML=''">Cancel</button>
    </div></div>`;
  document.getElementById('sf-submit').addEventListener('click',async()=>{
    const n=document.getElementById('sf-name').value.trim();
    if(!n){alert('Name required');return}
    try{
      if(isEdit) await apiUpdateStudent(id,{name:n,roll_number:document.getElementById('sf-roll').value,remarks:document.getElementById('sf-remarks').value});
      else await apiCreateStudent({name:n,roll_number:document.getElementById('sf-roll').value,remarks:document.getElementById('sf-remarks').value});
      loadStudents();
    }catch(e){alert(e.message)}
  });
}
function editStudent(id,name,roll,remarks){showStudentForm(name,roll,remarks,id)}
async function deleteStudentConfirm(id,name){
  if(!confirm(`Delete student "${name}"?`)) return;
  try{await apiDeleteStudent(id);loadStudents()}catch(e){alert(e.message)}
}
