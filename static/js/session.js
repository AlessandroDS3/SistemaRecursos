"use strict";
async function sessionInfo(){
  try{
    const response=await fetch('/api/sesion');
    if(response.status===401){window.location.replace('/login');return;}
    if(!response.ok)return;
    const data=await response.json();document.querySelector('#session-user').textContent=data.usuario;
  }catch(error){document.querySelector('#session-user').textContent='Sesión';}
}
document.querySelector('#logout').onclick=async event=>{
  event.target.disabled=true;
  try{
    const response=await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    if(response.ok||response.status===401){window.location.replace('/login');return;}
    throw new Error('No se pudo cerrar sesión.');
  }catch(error){document.querySelector('#session-user').textContent='No se pudo cerrar sesión. Reintenta.';event.target.disabled=false;}
};
sessionInfo();

document.addEventListener('pointerdown', () => { document.documentElement.dataset.input = 'pointer'; }, {passive:true});
document.addEventListener('keydown', () => { document.documentElement.dataset.input = 'keyboard'; });
