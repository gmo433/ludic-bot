(function(){
  const tg = window.Telegram.WebApp;
  try { tg.expand(); } catch(e){}
  const matchesEl = document.getElementById('matches');
  const refreshBtn = document.getElementById('refresh');
  const closeBtn = document.getElementById('close');

  async function loadMatches(){
    matchesEl.innerHTML = '⏳ Загрузка...';
    try{
      const resp = await fetch('/api/matches');
      if(!resp.ok) throw new Error('Network response not ok');
      const data = await resp.json();
      const matches = data.data || [];
      if(matches.length === 0){
        matchesEl.innerHTML = '<div class="match">⚽ Нет матчей в ближайшие 2 часов</div>';
        return;
      }
      matchesEl.innerHTML = matches.map(m => {
        const league = (m.league && m.league.name) || '—';
        const home = (m.teams && m.teams.home && m.teams.home.name) || 'Home';
        const away = (m.teams && m.teams.away && m.teams.away.name) || 'Away';
        const time = m.time || '';
        return `<div class="match"><div class="league">${league}</div><div class="vs">⚽ ${home} — ${away}</div><div class="time">🕒 ${time}</div></div>`;
      }).join('');
    }catch(e){
      console.error(e);
      matchesEl.innerHTML = '<div class="match">❌ Ошибка при загрузке матчей</div>';
    }
  }

  refreshBtn.addEventListener('click', loadMatches);
  closeBtn.addEventListener('click', ()=>{ try{ tg.close(); }catch(e){} });

  // initial load
  loadMatches();
})();
