// Tokens remain in encrypted HttpOnly cookies.
(() => {
 const originalFetch=window.fetch.bind(window); let renewing;
 function renew(){
  if(!renewing) renewing=originalFetch('/api/account/refresh',{method:'POST',credentials:'same-origin'}).then(r=>r.ok).catch(()=>false).finally(()=>{renewing=null;});
  return renewing;
 }
 window.fetch=async(input,options)=>{
  const response=await originalFetch(input,options);
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(response.status===401 && url.origin===location.origin && url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/account/') && await renew()) return originalFetch(input,options);
  return response;
 };
 window.jobpilotSessionReady=renew();
 setInterval(renew,45*60*1000);
})();
