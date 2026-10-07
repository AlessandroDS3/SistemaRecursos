"use strict";
const form=document.querySelector('#login-form');
document.querySelector('#show-password').onchange=event=>{form.elements.contrasena.type=event.target.checked?'text':'password';};
form.onsubmit=async event=>{
  event.preventDefault();const button=document.querySelector('#login-submit'), error=document.querySelector('#login-error');
  button.disabled=true;button.textContent='Ingresando...';error.hidden=true;
  try{
    const response=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(form)))});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'No se pudo iniciar sesión.');
    window.location.assign('/');
  }catch(exc){error.textContent=exc.message||'No se pudo conectar con el servidor.';error.hidden=false;}
  finally{button.disabled=false;button.textContent='Iniciar sesión';}
};

document.addEventListener('pointerdown', () => { document.documentElement.dataset.input = 'pointer'; }, {passive:true});
document.addEventListener('keydown', () => { document.documentElement.dataset.input = 'keyboard'; });
