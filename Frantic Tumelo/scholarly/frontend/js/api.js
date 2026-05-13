/* Scholarly API client */
const API='/api';
function getToken(){return localStorage.getItem('scholarly_token')}
function setToken(t){localStorage.setItem('scholarly_token',t)}
function clearToken(){localStorage.removeItem('scholarly_token')}
function getRole(){return localStorage.getItem('scholarly_role')}
function setRole(r){localStorage.setItem('scholarly_role',r)}
function clearRole(){localStorage.removeItem('scholarly_role')}
function isLoggedIn(){return !!getToken()}
function logout(){clearToken();clearRole();window.location.href='/'}

async function apiFetch(path,opts={}){
  const headers={...(opts.headers||{})};
  const token=getToken();
  if(token) headers['Authorization']=`Bearer ${token}`;
  if(opts.body&&!(opts.body instanceof FormData)&&!(opts.body instanceof URLSearchParams))
    headers['Content-Type']='application/json';
  const res=await fetch(`${API}${path}`,{...opts,headers});
  if(res.status===401){clearToken();clearRole();window.location.href='/';return}
  if(res.status===204) return null;
  const data=await res.json();
  if(!res.ok) throw new Error(data.detail||'Request failed');
  return data;
}

// Auth
async function apiLogin(loginName,password){
  const body=new URLSearchParams({username:loginName,password});
  const data=await apiFetch('/auth/login',{method:'POST',body});
  setToken(data.access_token);
  setRole(data.role);
  sessionStorage.setItem('playSplash', 'true');
  return data;
}
function apiGetMe(){return apiFetch('/auth/me')}

// Students (teacher)
function apiGetStudents(search){return apiFetch(`/students/?search=${encodeURIComponent(search||'')}`)}
function apiGetStudent(id){return apiFetch(`/students/${id}`)}
function apiCreateStudent(d){return apiFetch('/students/',{method:'POST',body:JSON.stringify(d)})}
function apiUpdateStudent(id,d){return apiFetch(`/students/${id}`,{method:'PUT',body:JSON.stringify(d)})}
function apiDeleteStudent(id){return apiFetch(`/students/${id}`,{method:'DELETE'})}

// Attendance (teacher)
function apiRecordAttendance(d){return apiFetch('/attendance/',{method:'POST',body:JSON.stringify(d)})}
function apiBulkAttendance(d){return apiFetch('/attendance/bulk',{method:'POST',body:JSON.stringify(d)})}
function apiGetAttendanceByDate(date){return apiFetch(`/attendance/date/${date}`)}
function apiGetAttendanceSummary(){return apiFetch('/attendance/summary')}
function apiGetStudentAttendance(id){return apiFetch(`/attendance/student/${id}`)}

// Scores (teacher)
function apiGetScoreConfig(){return apiFetch('/scores/config')}
function apiEnterScore(d){return apiFetch('/scores/',{method:'POST',body:JSON.stringify(d)})}
function apiBulkScores(d){return apiFetch('/scores/bulk',{method:'POST',body:JSON.stringify(d)})}
function apiGetStudentScores(id){return apiFetch(`/scores/student/${id}`)}
function apiGetExamScores(exam){return apiFetch(`/scores/exam/${encodeURIComponent(exam)}`)}

// Events (teacher)
function apiGetEvents(){return apiFetch('/events/')}
function apiCreateEvent(d){return apiFetch('/events/',{method:'POST',body:JSON.stringify(d)})}
function apiDeleteEvent(id){return apiFetch(`/events/${id}`,{method:'DELETE'})}

// Analytics (teacher)
function apiGetStudentAnalytics(id){return apiFetch(`/analytics/student/${id}`)}
function apiGetClassOverview(){return apiFetch('/analytics/class-overview')}

// Admin
function apiAdminStats(){return apiFetch('/admin/stats')}
function apiAdminListTeachers(){return apiFetch('/admin/teachers')}
function apiAdminCreateTeacher(d){return apiFetch('/admin/teachers',{method:'POST',body:JSON.stringify(d)})}
function apiAdminDeleteTeacher(id){return apiFetch(`/admin/teachers/${id}`,{method:'DELETE'})}
function apiAdminListStudents(){return apiFetch('/admin/all-students')}
function apiAdminCreateStudent(d){return apiFetch('/admin/students',{method:'POST',body:JSON.stringify(d)})}
function apiAdminDeleteStudent(id){return apiFetch(`/admin/students/${id}`,{method:'DELETE'})}

// Student portal (read-only)
function apiMyAttendance(){return apiFetch('/my/attendance')}
function apiMyScores(){return apiFetch('/my/scores')}
function apiMyAnalytics(){return apiFetch('/my/analytics')}
function apiMyEvents(){return apiFetch('/my/events')}

// AI Summary (streaming)
async function apiAISummary(studentId, onChunk, onDone){
  const token=getToken();
  const res=await fetch(`${API}/ai/summary/${studentId}`,{headers:{Authorization:`Bearer ${token}`}});
  if(!res.ok){const e=await res.json().catch(()=>({detail:'AI error'}));throw new Error(e.detail)}
  const reader=res.body.getReader();
  const decoder=new TextDecoder();
  let text='';
  while(true){
    const{done,value}=await reader.read();
    if(done) break;
    const chunk=decoder.decode(value,{stream:true});
    text+=chunk;
    if(onChunk) onChunk(text);
  }
  if(onDone) onDone(text);
  return text;
}
