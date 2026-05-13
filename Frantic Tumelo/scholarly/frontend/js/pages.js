/* Scholarly Pages — Attendance, Exams, Analytics, Schedule */

// ── ATTENDANCE ─────────────────────────
async function loadAttendance(){
  const pg=document.getElementById('page-attendance');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const today=new Date().toISOString().split('T')[0];
    const summary=await apiGetAttendanceSummary();
    pg.innerHTML=`
      <div class="toolbar">
        <input type="date" class="toolbar-search" id="att-date" value="${today}" style="max-width:200px">
        <button class="btn btn-primary" id="btn-load-att">Load / Take Attendance</button>
        <button class="btn btn-secondary" onclick="showAttSummary()">Summary</button>
      </div>
      <div id="att-content"></div>`;
    document.getElementById('btn-load-att').addEventListener('click',loadAttForDate);
    showAttSummary(summary);
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

function showAttSummary(data){
  const el=document.getElementById('att-content');
  if(!el) return;
  apiGetAttendanceSummary().then(summary=>{
    if(!summary.length){el.innerHTML='<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-text">No attendance data yet</div></div>';return}
    // Bar chart
    let html=`<div class="chart-wrap"><div class="chart-title">Attendance Overview (%)</div><div class="chart-bar-group">`;
    summary.forEach((s,i)=>{
      const h=s.percentage*1.6;
      const clr=s.percentage>=75?'#22c55e':s.percentage>=50?'#f59e0b':'#ef4444';
      html+=`<div class="chart-bar" style="height:${h}px;background:${clr}"><div class="bar-val">${s.percentage}%</div><div class="bar-label">${s.student_name.split(' ')[0]}</div></div>`;
    });
    html+=`</div></div>`;
    // Table
    html+=`<div class="card"><div class="card-title" style="margin-bottom:1rem">Attendance Summary</div>
      <table class="data-table"><thead><tr><th>Student</th><th>Total</th><th>Present</th><th>Absent</th><th>%</th></tr></thead>
      <tbody>${summary.map(s=>`<tr>
        <td><strong>${s.student_name}</strong></td><td>${s.total_days}</td><td>${s.present_days}</td><td>${s.absent_days}</td>
        <td><span class="badge ${s.percentage>=75?'badge-green':s.percentage>=50?'badge-yellow':'badge-red'}">${s.percentage}%</span></td>
      </tr>`).join('')}</tbody></table></div>`;
    el.innerHTML=html;
  });
}

async function loadAttForDate(){
  const date=document.getElementById('att-date').value;
  if(!date){alert('Select a date');return}
  const el=document.getElementById('att-content');
  el.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const records=await apiGetAttendanceByDate(date);
    if(!records.length){el.innerHTML='<div class="empty-state"><div class="empty-text">No students found</div></div>';return}
    el.innerHTML=`<div class="card"><div class="card-header"><div class="card-title">Attendance — ${date}</div>
      <button class="btn btn-primary btn-sm" id="btn-save-att">Save All</button></div>
      <table class="data-table"><thead><tr><th>Student</th><th>Roll</th><th>Status</th></tr></thead>
      <tbody>${records.map(r=>`<tr>
        <td><strong>${r.student_name}</strong></td><td>${r.roll_number||'—'}</td>
        <td><button class="att-toggle ${r.present===false?'absent':'present'}" data-sid="${r.student_id}" onclick="this.classList.toggle('present');this.classList.toggle('absent')"></button></td>
      </tr>`).join('')}</tbody></table></div>`;
    document.getElementById('btn-save-att').addEventListener('click',async()=>{
      const toggles=document.querySelectorAll('.att-toggle');
      const recs=[];
      toggles.forEach(t=>recs.push({student_id:parseInt(t.dataset.sid),present:t.classList.contains('present')}));
      try{
        await apiBulkAttendance({date,records:recs});
        alert('Attendance saved!');
      }catch(e){alert(e.message)}
    });
  }catch(e){el.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

// ── EXAMS ──────────────────────────────
async function loadExams(){
  const pg=document.getElementById('page-exams');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const students=await apiGetStudents();
    const cfg=scoreConfig||await apiGetScoreConfig();
    pg.innerHTML=`
      <div class="toolbar">
        <select class="toolbar-select" id="exam-student">${students.map(s=>`<option value="${s.id}">${s.name}</option>`).join('')}</select>
        <select class="toolbar-select" id="exam-period">${cfg.exam_periods.map(e=>`<option value="${e}">${e}</option>`).join('')}</select>
        <button class="btn btn-primary" id="btn-load-scores">Load Scores</button>
        <button class="btn btn-secondary" id="btn-enter-marks">Enter Marks</button>
      </div>
      <div id="exam-content"></div>`;
    document.getElementById('btn-load-scores').addEventListener('click',loadStudentScoreView);
    document.getElementById('btn-enter-marks').addEventListener('click',showMarksEntry);
    
    const refreshView = () => { if(document.getElementById('btn-save-marks')) showMarksEntry(); else loadStudentScoreView(); };
    document.getElementById('exam-student').addEventListener('change', refreshView);
    document.getElementById('exam-period').addEventListener('change', () => { if(document.getElementById('btn-save-marks')) showMarksEntry(); });
    
    if(students.length) loadStudentScoreView();
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

async function loadStudentScoreView(){
  const sid=document.getElementById('exam-student').value;
  const el=document.getElementById('exam-content');
  el.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const data=await apiGetStudentScores(sid);
    if(!Object.keys(data.scores_by_exam).length){el.innerHTML='<div class="empty-state"><div class="empty-icon">📝</div><div class="empty-text">No scores recorded yet</div></div>';return}
    let html=`<h3 style="font-size:1rem;font-weight:700;margin-bottom:1rem">${data.student_name} — Class ${data.student_class}-${data.section}</h3>`;
    for(const[exam,info] of Object.entries(data.scores_by_exam)){
      html+=`<div class="card" style="margin-bottom:.75rem"><div class="card-header"><div class="card-title">${exam}</div>
        <span class="badge badge-primary">${info.percentage}%</span></div>
        <table class="data-table"><thead><tr><th>Subject</th><th>Marks</th><th>Max</th><th>%</th></tr></thead>
        <tbody>${info.subjects.map(s=>`<tr><td>${s.subject}</td><td>${s.marks_obtained}</td><td>${s.max_marks}</td>
        <td><span class="badge ${s.percentage>=75?'badge-green':s.percentage>=40?'badge-yellow':'badge-red'}">${s.percentage}%</span></td></tr>`).join('')}
        <tr style="font-weight:800"><td>Total</td><td>${info.total_obtained}</td><td>${info.total_max}</td><td>${info.percentage}%</td></tr>
        </tbody></table></div>`;
    }
    el.innerHTML=html;
  }catch(e){el.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

async function showMarksEntry(){
  const sid=document.getElementById('exam-student').value;
  const exam=document.getElementById('exam-period').value;
  const cfg=scoreConfig||await apiGetScoreConfig();
  const el=document.getElementById('exam-content');
  el.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  
  let existing = {};
  try{
    const data=await apiGetStudentScores(sid);
    if(data.scores_by_exam[exam]){
      data.scores_by_exam[exam].subjects.forEach(s=>existing[s.subject]=s.marks_obtained);
    }
  }catch(e){}
  
  el.innerHTML=`<div class="form-panel"><div class="form-panel-title">Enter Marks — ${exam}</div>
    <table class="data-table"><thead><tr><th>Subject</th><th>Marks</th><th>Max</th></tr></thead>
    <tbody>${cfg.subjects.map(s=>{
      const val = existing[s] !== undefined ? existing[s] : 0;
      return `<tr><td>${s}</td><td><input type="number" id="mark-${s.replace(/\s/g,'_')}" min="0" max="100" value="${val}"></td><td>100</td></tr>`
    }).join('')}</tbody></table>
    <div class="form-actions" style="margin-top:1rem">
      <button class="btn btn-primary" id="btn-save-marks">Save Marks</button>
      <button class="btn btn-secondary" onclick="loadStudentScoreView()">Cancel</button>
    </div></div>`;
  document.getElementById('btn-save-marks').addEventListener('click',async()=>{
    const scores=cfg.subjects.map(s=>({subject:s,marks_obtained:parseFloat(document.getElementById('mark-'+s.replace(/\s/g,'_')).value)||0,max_marks:100}));
    try{
      await apiBulkScores({student_id:parseInt(sid),exam_period:exam,scores});
      alert('Marks saved!');loadStudentScoreView();
    }catch(e){alert(e.message)}
  });
}

// ── ANALYTICS ──────────────────────────
async function loadAnalytics(){
  const pg=document.getElementById('page-analytics');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const students=await apiGetStudents();
    if(!students.length){pg.innerHTML='<div class="empty-state"><div class="empty-icon">📊</div><div class="empty-text">No students to analyze</div></div>';return}
    pg.innerHTML=`
      <div class="toolbar">
        <select class="toolbar-select" id="analytics-student">${students.map(s=>`<option value="${s.id}">${s.name}</option>`).join('')}</select>
        <button class="btn btn-primary" id="btn-load-analytics">Analyze</button>
      </div>
      <div id="analytics-content"></div>`;
    document.getElementById('btn-load-analytics').addEventListener('click',()=>{
      loadStudentAnalytics(document.getElementById('analytics-student').value);
    });
    loadStudentAnalytics(students[0].id);
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

async function loadStudentAnalytics(sid){
  const el=document.getElementById('analytics-content');
  if(!el) return;
  el.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const data=await apiGetStudentAnalytics(sid);
    const trendIcon=data.overall_trend==='improving'?'📈':data.overall_trend==='declining'?'📉':'➡️';
    const trendClass=data.overall_trend==='improving'?'trend-up':data.overall_trend==='declining'?'trend-down':'trend-stable';

    let html=`<div class="stats-grid" style="margin-top:1rem">
      <div class="stat-card"><div class="stat-label">Student</div><div class="stat-value" style="font-size:1.2rem">${data.student_name}</div><div class="stat-sub">Class ${data.student_class}-${data.section}</div></div>
      <div class="stat-card"><div class="stat-label">Overall Trend</div><div class="stat-value ${trendClass}">${trendIcon} ${data.overall_trend}</div></div>
      <div class="stat-card"><div class="stat-label">Attendance</div><div class="stat-value">${data.attendance.percentage}%</div><div class="stat-sub">${data.attendance.present}/${data.attendance.total} days</div></div>
    </div>`;

    // Exam trend chart
    html+=`<div class="chart-wrap"><div class="chart-title">Exam-wise Performance</div><div class="chart-bar-group">`;
    data.exam_order.forEach((exam,i)=>{
      const val=data.exam_trends[exam];
      const h=val!==null?val*1.6:0;
      html+=`<div class="chart-bar" style="height:${h}px;background:${COLORS[i%COLORS.length]}${val===null?';opacity:.2':''}">
        <div class="bar-val">${val!==null?val+'%':'—'}</div><div class="bar-label">${exam}</div></div>`;
    });
    html+=`</div></div>`;

    // Subject trend chart
    html+=`<div class="chart-wrap"><div class="chart-title">Subject-wise Trends (Latest Exam)</div><div class="chart-bar-group">`;
    data.subjects.forEach((subj,i)=>{
      const vals=data.subject_trends[subj];
      const lastVal=vals.filter(v=>v!==null).pop();
      const h=lastVal!==null&&lastVal!==undefined?lastVal*1.6:0;
      html+=`<div class="chart-bar" style="height:${h}px;background:${COLORS[i%COLORS.length]}${lastVal==null?';opacity:.2':''}">
        <div class="bar-val">${lastVal!=null?lastVal+'%':'—'}</div><div class="bar-label">${subj.substring(0,4)}</div></div>`;
    });
    html+=`</div></div>`;

    // Subject-wise detailed table
    html+=`<div class="card"><div class="card-title" style="margin-bottom:1rem">Subject-wise Scores Across Exams</div>
      <div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Subject</th>`;
    data.exam_order.forEach(e=>html+=`<th>${e}</th>`);
    html+=`</tr></thead><tbody>`;
    data.subjects.forEach(subj=>{
      html+=`<tr><td><strong>${subj}</strong></td>`;
      data.subject_trends[subj].forEach(v=>{
        if(v===null) html+=`<td>—</td>`;
        else html+=`<td><span class="badge ${v>=75?'badge-green':v>=40?'badge-yellow':'badge-red'}">${v}%</span></td>`;
      });
      html+=`</tr>`;
    });
    html+=`</tbody></table></div></div>`;

    // Weakness & Strength
    html+=`<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">`;
    html+=`<div class="card"><div class="card-title" style="margin-bottom:.75rem">⚠️ Weaknesses</div>`;
    if(data.weak_subjects.length) data.weak_subjects.forEach(w=>html+=`<div class="weakness-card"><div class="wc-subject">${w.subject}</div><div class="wc-reason">${w.reason} — Avg: ${w.avg.toFixed(1)}%</div></div>`);
    else html+=`<div class="empty-state" style="padding:1rem"><div class="empty-text">No weaknesses detected</div></div>`;
    html+=`</div>`;

    html+=`<div class="card"><div class="card-title" style="margin-bottom:.75rem">💪 Strengths</div>`;
    if(data.strong_subjects.length) data.strong_subjects.forEach(s=>html+=`<div class="strength-card"><div class="sc-subject">${s.subject}</div><div class="sc-avg">Avg: ${s.avg.toFixed(1)}%</div></div>`);
    else html+=`<div class="empty-state" style="padding:1rem"><div class="empty-text">Not enough data</div></div>`;
    html+=`</div></div>`;

    // Declining subjects
    if(data.declining_subjects.length){
      html+=`<div class="card" style="margin-top:1rem"><div class="card-title" style="margin-bottom:.75rem">📉 Sudden Drops</div>`;
      data.declining_subjects.forEach(d=>html+=`<div class="weakness-card"><div class="wc-subject">${d.subject}</div><div class="wc-reason">Dropped ${d.drop}% from ${d.from_exam}</div></div>`);
      html+=`</div>`;
    }
    // AI Summary button
    html+=`<div class="card" style="margin-top:1rem"><div class="card-header"><div class="card-title">🤖 AI Academic Advisor</div>
      <button class="btn btn-primary btn-sm" id="btn-ai-summary" data-sid="${sid}">Generate Summary</button></div>
      <div id="ai-summary-box" style="padding:.5rem 0;font-size:.88rem;font-weight:600;color:var(--text-light);line-height:1.6;white-space:pre-wrap"></div></div>`;
    
    el.innerHTML=html;
    document.getElementById('btn-ai-summary')?.addEventListener('click',async function(){
      const btn=this;const box=document.getElementById('ai-summary-box');
      btn.disabled=true;btn.textContent='Thinking…';
      box.innerHTML='<div class="spinner"></div>';
      try{
        await apiAISummary(btn.dataset.sid, text=>{box.textContent=text}, text=>{btn.textContent='Regenerate';btn.disabled=false});
      }catch(e){box.textContent='⚠️ '+e.message;btn.textContent='Retry';btn.disabled=false}
    });
  }catch(e){el.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

// ── SCHEDULE ───────────────────────────
async function loadSchedule(){
  const pg=document.getElementById('page-schedule');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const events=await apiGetEvents();
    pg.innerHTML=`
      <div class="toolbar">
        <span style="font-weight:700;font-size:.9rem">Tests & PTM Schedule</span>
        <button class="btn btn-primary" id="btn-add-event">+ Add Event</button>
      </div>
      <div id="event-form-area"></div>
      <div id="event-list"></div>`;
    document.getElementById('btn-add-event').addEventListener('click',showEventForm);
    renderEvents(events);
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

function renderEvents(events){
  const el=document.getElementById('event-list');
  if(!events.length){el.innerHTML='<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-text">No events scheduled</div></div>';return}
  el.innerHTML=events.map(ev=>`${renderEventCard(ev)}<div style="text-align:right;margin-top:-0.25rem;margin-bottom:.5rem"><button class="btn btn-sm btn-danger" onclick="deleteEventConfirm(${ev.id},'${ev.title.replace(/'/g,"\\'")}')">Delete</button></div>`).join('');
}

function showEventForm(){
  const area=document.getElementById('event-form-area');
  const today=new Date().toISOString().split('T')[0];
  area.innerHTML=`<div class="form-panel"><div class="form-panel-title">Add Event</div>
    <div class="form-grid">
      <div class="form-group"><label>Title</label><input id="ev-title" placeholder="Event title" required></div>
      <div class="form-group"><label>Type</label><select id="ev-type"><option value="test">Test</option><option value="ptm">PTM</option></select></div>
      <div class="form-group"><label>Date</label><input type="date" id="ev-date" value="${today}"></div>
      <div class="form-group"><label>Description</label><input id="ev-desc" placeholder="Optional notes"></div>
    </div>
    <div class="form-actions">
      <button class="btn btn-primary" id="ev-submit">Create Event</button>
      <button class="btn btn-secondary" onclick="document.getElementById('event-form-area').innerHTML=''">Cancel</button>
    </div></div>`;
  document.getElementById('ev-submit').addEventListener('click',async()=>{
    const title=document.getElementById('ev-title').value.trim();
    if(!title){alert('Title required');return}
    try{
      await apiCreateEvent({title,event_type:document.getElementById('ev-type').value,event_date:document.getElementById('ev-date').value,description:document.getElementById('ev-desc').value});
      loadSchedule();
    }catch(e){alert(e.message)}
  });
}

async function deleteEventConfirm(id,title){
  if(!confirm(`Delete "${title}"?`)) return;
  try{await apiDeleteEvent(id);loadSchedule()}catch(e){alert(e.message)}
}

// ── ADMIN ──────────────────────────────
let adminTab='teachers';
async function loadAdmin(){
  const pg=document.getElementById('page-admin');
  pg.innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const stats=await apiAdminStats();
    pg.innerHTML=`
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">Teachers</div><div class="stat-value">${stats.total_teachers}</div></div>
        <div class="stat-card"><div class="stat-label">Students</div><div class="stat-value">${stats.total_students}</div></div>
      </div>
      <div class="toolbar">
        <div class="btn-row" style="margin:0">
          <button class="btn ${adminTab==='teachers'?'btn-primary':'btn-secondary'}" onclick="adminTab='teachers';loadAdmin()">Teachers</button>
          <button class="btn ${adminTab==='students'?'btn-primary':'btn-secondary'}" onclick="adminTab='students';loadAdmin()">Students</button>
        </div>
      </div>
      <div id="admin-form-area"></div>
      <div id="admin-list-area"></div>`;
    if(adminTab==='teachers') await loadAdminTeachers();
    else await loadAdminStudentAccounts();
  }catch(e){pg.innerHTML=`<div class="empty-state"><div class="empty-text">${e.message}</div></div>`}
}

async function loadAdminTeachers(){
  const list=await apiAdminListTeachers();
  document.getElementById('admin-form-area').innerHTML=`
    <div class="form-panel"><div class="form-panel-title">Create Teacher Account</div>
      <div class="form-grid">
        <div class="form-group"><label>Login Name</label><input id="at-login" placeholder="e.g. john"></div>
        <div class="form-group"><label>Full Name</label><input id="at-name" placeholder="John Smith"></div>
        <div class="form-group"><label>Email</label><input id="at-email" placeholder="Optional" type="email"></div>
        <div class="form-group"><label>Password</label><input id="at-pass" type="password" placeholder="Password"></div>
        <div class="form-group"><label>Assigned Class</label><select id="at-class"><option value="">None</option>${[5,6,7,8,9].map(c=>`<option value="${c}">${c}</option>`).join('')}</select></div>
        <div class="form-group"><label>Section</label><input id="at-section" placeholder="e.g. A" maxlength="5"></div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" onclick="createTeacherAccount()">Create Teacher</button>
      </div>
    </div>`;
  const el=document.getElementById('admin-list-area');
  el.innerHTML=list.map(t=>`
    <div class="student-card">
      <div class="student-avatar">${t.initials}</div>
      <div class="student-info">
        <div class="s-name">${t.full_name} ${t.is_admin?'<span class="badge badge-primary">Admin</span>':''}</div>
        <div class="s-meta">@${t.login_name} · ${t.class_section||'No class'} · ${t.email||'—'}</div>
      </div>
      <button class="btn btn-sm btn-danger" onclick="deleteTeacherConfirm(${t.id},'${t.full_name.replace(/'/g,"\\'")}')">Del</button>
    </div>`).join('');
}

async function createTeacherAccount(){
  const login=document.getElementById('at-login').value.trim();
  const name=document.getElementById('at-name').value.trim();
  const pass=document.getElementById('at-pass').value;
  const cls=document.getElementById('at-class').value;
  if(!login||!name||!pass){alert('Login, name and password required');return}
  try{
    await apiAdminCreateTeacher({
      login_name:login, full_name:name, password:pass,
      email:document.getElementById('at-email').value||null,
      assigned_class:cls?parseInt(cls):null,
      assigned_section:document.getElementById('at-section').value.trim()||null,
    });
    alert('Teacher created!'); loadAdmin();
  }catch(e){alert(e.message)}
}

async function deleteTeacherConfirm(id,name){
  if(!confirm(`Delete teacher "${name}"?`)) return;
  try{await apiAdminDeleteTeacher(id);loadAdmin()}catch(e){alert(e.message)}
}

async function loadAdminStudentAccounts(){
  const list=await apiAdminListStudents();
  document.getElementById('admin-form-area').innerHTML=`
    <div class="form-panel"><div class="form-panel-title">Create Student Account</div>
      <div class="form-grid">
        <div class="form-group"><label>Login Name</label><input id="as-login" placeholder="e.g. ravi7a"></div>
        <div class="form-group"><label>Full Name</label><input id="as-name" placeholder="Ravi Kumar"></div>
        <div class="form-group"><label>Email</label><input id="as-email" placeholder="Optional" type="email"></div>
        <div class="form-group"><label>Password</label><input id="as-pass" type="password" placeholder="Password"></div>
        <div class="form-group"><label>Class</label><select id="as-class">${[5,6,7,8,9].map(c=>`<option value="${c}">${c}</option>`).join('')}</select></div>
        <div class="form-group"><label>Section</label><input id="as-section" value="A" placeholder="e.g. A" maxlength="5"></div>
        <div class="form-group"><label>Roll Number</label><input id="as-roll" placeholder="Optional"></div>
      </div>
      <div class="form-actions">
        <button class="btn btn-primary" onclick="createStudentAccount()">Create Student</button>
      </div>
    </div>`;
  const el=document.getElementById('admin-list-area');
  if(!list.length){el.innerHTML='<div class="empty-state"><div class="empty-icon">👨‍🎓</div><div class="empty-text">No student accounts yet</div></div>';return}
  el.innerHTML=list.map(s=>`
    <div class="student-card">
      <div class="student-avatar">${s.initials}</div>
      <div class="student-info">
        <div class="s-name">${s.name}</div>
        <div class="s-meta">@${s.login_name} · Class ${s.class_section} · Roll: ${s.roll_number||'—'} · Teacher: ${s.teacher_name}</div>
      </div>
      <button class="btn btn-sm btn-danger" onclick="deleteStudentAccountConfirm(${s.id},'${s.name.replace(/'/g,"\\'")}')">Del</button>
    </div>`).join('');
}

async function createStudentAccount(){
  const login=document.getElementById('as-login').value.trim();
  const name=document.getElementById('as-name').value.trim();
  const pass=document.getElementById('as-pass').value;
  if(!login||!name||!pass){alert('Login, name and password required');return}
  try{
    await apiAdminCreateStudent({
      login_name:login, name:name, password:pass,
      email:document.getElementById('as-email').value||null,
      student_class:parseInt(document.getElementById('as-class').value),
      section:document.getElementById('as-section').value.trim()||'A',
      roll_number:document.getElementById('as-roll').value||null,
    });
    alert('Student created!'); loadAdmin();
  }catch(e){alert(e.message)}
}

async function deleteStudentAccountConfirm(id,name){
  if(!confirm(`Delete student account "${name}"?`)) return;
  try{await apiAdminDeleteStudent(id);loadAdmin()}catch(e){alert(e.message)}
}
