"use strict";
const $ = s => document.querySelector(s);
const names = {ESTUDIANTE:'Estudiante',DOCENTE:'Docente',ADMINISTRATIVO:'Administrativo'};
const fields = {
  ESTUDIANTE:[['codigoEstudiante','Código de estudiante',true],['matricula','Matrícula'],['ciclo','Ciclo',true,'number'],['semestreAcademico','Semestre académico'],['estadoMatricula','Estado de matrícula']],
  DOCENTE:[['codigoDocente','Código de docente',true],['departamentoAcademico','Departamento académico'],['facultad','Facultad'],['escuelaProfesional','Escuela profesional']],
  ADMINISTRATIVO:[['codigoEmpleado','Código de empleado',true],['area','Área']]
};
let people = [], timer;
function node(tag, text, cls){const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e;}
async function request(data){
  const response=await fetch('/api/personas',data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});
  if(response.status===401){window.location.replace('/login');throw new Error('La sesión terminó.');}
  const body=await response.json(); if(!response.ok)throw new Error(body.error||'No se pudo completar la operación.'); return body;
}
async function load(){
  $('#status').textContent='Cargando personas...'; $('#retry').hidden=true;
  try{
    people=(await request()).personas;
    for(const [id,type] of [['students','ESTUDIANTE'],['teachers','DOCENTE'],['staff','ADMINISTRATIVO']])$('#'+id).textContent=people.filter(p=>p.tipo===type).length;
    $('#status').textContent=''; $('#new-person').disabled=false; render(); return true;
  }catch(error){$('#status').textContent='No se pudo cargar el directorio. Revisa el servidor y la conexión MySQL.';$('#retry').hidden=false;return false;}
}
const normalized=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function render(){
  const query=normalized($('#search').value.trim()), type=$('#person-filter').value;
  const results=people.filter(p=>(!type||p.tipo===type)&&normalized([p.nombres,p.apellidos,p.documentoIdentidad,...Object.values(p.detalles)].join(' ')).includes(query));
  $('#people').replaceChildren(); $('#result-count').textContent=results.length; $('#empty').hidden=results.length>0;
  results.forEach(p=>{
    const row=node('tr'), name=node('td',p.nombres+' '+p.apellidos), type=node('td',names[p.tipo]), state=node('td'), action=node('td');
    name.append(node('small',p.correo));type.append(node('small',p.detalles[fields[p.tipo][0][0]]));state.append(node('span',p.estado,'badge'));
    const button=node('button','Ver ficha ','card-button');button.setAttribute('aria-label','Ver ficha de '+p.nombres+' '+p.apellidos);button.onclick=()=>showDetail(p);action.append(button);
    row.append(name,type,node('td',p.documentoIdentidad),state,action);$('#people').append(row);
  });
}
function showFields(){
  $('#specific-fields').replaceChildren();
  fields[$('#person-type').value].forEach(([key,label,required,type])=>{
    const wrapper=node('label',label+(required?' *':'')), input=node('input');input.name=key;input.required=!!required;input.type=type||'text';input.maxLength=120;
    if(type==='number'){input.min=1;input.max=20;input.step=1;}wrapper.append(input);$('#specific-fields').append(wrapper);
  });
}
function showDetail(p){
  $('#detail-title').textContent=p.nombres+' '+p.apellidos;$('#detail-fields').replaceChildren();
  const values=[['Tipo',names[p.tipo]],['Documento',p.documentoIdentidad],['Correo',p.correo],['Teléfono',p.telefono||'No registrado'],['Estado',p.estado],['Fecha de registro',p.fechaRegistro.replace('T',' ')],...fields[p.tipo].map(([key,label])=>[label,p.detalles[key]||'No registrado'])];
  values.forEach(([label,value])=>{const item=node('div');item.append(node('dt',label),node('dd',value));$('#detail-fields').append(item);});$('#person-detail').showModal();
}
$('#new-person').onclick=()=>{$('#person-form').reset();showFields();$('#form-error').hidden=true;$('#person-dialog').showModal();};
$('#person-type').onchange=showFields;
$('#person-form').onsubmit=async event=>{
  event.preventDefault();const data=Object.fromEntries(new FormData(event.target));if(data.tipo==='ESTUDIANTE')data.ciclo=Number(data.ciclo);
  $('#save-person').disabled=true;$('#save-person').textContent='Guardando...';$('#form-error').hidden=true;
  try{
    await request(data);$('#person-dialog').close();const ok=await load();
    clearTimeout(timer);$('#toast').textContent=ok?'Persona registrada correctamente.':'Persona guardada. Reintenta la conexión para actualizar el directorio.';$('#toast').hidden=false;timer=setTimeout(()=>$('#toast').hidden=true,5000);
  }catch(error){$('#form-error').textContent=error.message;$('#form-error').hidden=false;}
  finally{$('#save-person').disabled=false;$('#save-person').textContent='Guardar persona';}
};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>{if(!$('#save-person').disabled)document.getElementById(b.dataset.close).close();});
$('#person-dialog').addEventListener('cancel',e=>{if($('#save-person').disabled)e.preventDefault();});
$('#search').oninput=render;$('#person-filter').onchange=render;
$('#clear').onclick=()=>{$('#search').value='';$('#person-filter').value='';render();};$('#retry').onclick=load;load();
