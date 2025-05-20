/* ui/static/dashboard.js — inject cards + wire up backend */

const agentList = document.getElementById("agentList");
const sugGrid   = document.getElementById("sugGrid");
const liveBox   = document.getElementById("live");
const datetime  = document.getElementById("datetime");

let current = null, ws = null;

/* footer clock */
setInterval(()=>datetime.textContent=new Date().toLocaleString(),1000);

/* build agent card */
function card(name, qlen){
  return `
<div class="agent-card bg-dark-700 rounded-lg p-3 cursor-pointer ${current===name?'active':''}"
     onclick="openLog('${name}')">
  <div class="flex justify-between">
    <div><h3 class="font-medium ${current===name?'text-primary-300':''}">${name}</h3>
        <p class="text-xs text-gray-400 mt-1">Queue ${qlen}</p></div>
    <span class="px-2 py-1 bg-green-900 text-green-300 rounded-full text-xs">Online</span>
  </div>
</div>`}

/* refresh queues + rebuild list */
async function loadAgents(){
  const {queues}=await (await fetch("/api/queues")).json();
  agentList.innerHTML = AGENTS.map(n=>card(n,queues[n]||0)).join("");
}
setInterval(loadAgents,3000); loadAgents();

/* websocket log */
function openLog(name){
  current = name; loadAgents();               // highlight
  if(ws) ws.close();
  liveBox.textContent="";
  const proto=location.protocol==="https:"?"wss":"ws";
  ws=new WebSocket(`${proto}://${location.host}/ws/${name}`);
  ws.onmessage=ev=>{
    liveBox.textContent+=ev.data+"\n";
    liveBox.scrollTop=liveBox.scrollHeight;
  };
}

/* suggestions grid */
function sugCard(s){
return `
<div class="bg-dark-700 rounded-lg border border-dark-600 p-4">
  <div class="flex justify-between items-start mb-3">
    <div><h3 class="font-medium text-primary-300 truncate">${s.path}</h3>
        <p class="text-xs text-gray-400 mt-1">${s.id.slice(0,8)}…</p></div>
    <span class="px-2 py-1 bg-blue-900 text-blue-300 rounded-full text-xs">Code</span>
  </div>
  <div class="text-sm text-gray-300 mb-4 overflow-y-auto max-h-24">${s.note||''}</div>
  <div class="flex justify-end space-x-2">
    <button class="px-3 py-1 bg-green-600 hover:bg-green-500 rounded-md text-xs"
            onclick="actSug('${s.id}','accept')"><i class="fas fa-check mr-1"></i>Approve</button>
    <button class="px-3 py-1 bg-red-600 hover:bg-red-500 rounded-md text-xs"
            onclick="actSug('${s.id}','reject')"><i class="fas fa-times mr-1"></i>Reject</button>
  </div>
</div>`}

async function loadSuggestions(){
  const list = await (await fetch("/suggestions/json")).json();
  sugGrid.innerHTML = list.map(sugCard).join("");
}
setInterval(loadSuggestions,3000); loadSuggestions();

async function actSug(id,action){
  await fetch(`/suggestions/${id}/${action}`,{method:'POST'});
  loadSuggestions();
}

/* optional demo task sender */
document.getElementById("taskSend").addEventListener("click",()=>{
  const box=document.getElementById("taskBox");
  if(!current||!box.value.trim()) return;
  fetch(`/cmd/${current}`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({cmd:"message",input:box.value.trim()})
  });
  box.value="";
});

async function loadGantt(){
  const list = await (await fetch("/suggestions/json")).json();
  let rows = list.map(s => {
    const m = s.meta || {};
    return `<tr>
      <td class="border-b border-dark-600 px-2 py-1">${s.path}</td>
      <td class="border-b border-dark-600 px-2 py-1">${m.priority || '—'}</td>
      <td class="border-b border-dark-600 px-2 py-1">${m.status || '—'}</td>
      <td class="border-b border-dark-600 px-2 py-1">${m.depends_on || '—'}</td>
    </tr>`;
  }).join("");

  document.getElementById("ganttChart").innerHTML = `
    <table class="w-full text-left">
      <thead>
        <tr class="text-primary-400 border-b border-dark-600">
          <th class="px-2 py-1">File</th>
          <th class="px-2 py-1">Priority</th>
          <th class="px-2 py-1">Status</th>
          <th class="px-2 py-1">Depends On</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}
