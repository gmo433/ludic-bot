(function(){
  const tg = window.Telegram.WebApp;
  try { tg.expand(); } catch(e){}
  const matchesEl = document.getElementById('matches');
  const refreshBtn = document.getElementById('refresh');
  const closeBtn = document.getElementById('close');

  // Функция для получения initData из Telegram Web App
  function getInitData() {
    return tg.initData || '';
  }

  // Функция для показа уведомлений
  function showNotification(message, isError = false) {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      padding: 12px 20px;
      background: ${isError ? '#f44336' : '#4CAF50'};
      color: white;
      border-radius: 8px;
      z-index: 1000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      font-size: 14px;
      max-width: 80%;
      text-align: center;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Автоматически удаляем через 5 секунд
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 5000);
  }

  async function loadMatches(){
    matchesEl.innerHTML = '⏳ Загрузка...';
    try{
      // Получаем initData для проверки авторизации
      const initData = getInitData();
      
      const resp = await fetch('/api/matches', {
        headers: {
          'X-Telegram-Init-Data': initData
        }
      });
      
      if(!resp.ok) {
        if (resp.status === 401) {
          throw new Error('Ошибка авторизации. Пожалуйста, откройте приложение через Telegram.');
        }
        throw new Error('Network response not ok');
      }
      
      const data = await resp.json();
      const matches = data.data || [];
      
      if(matches.length === 0){
        matchesEl.innerHTML = '<div class="match">⚽ Нет матчей в ближайшие 2 часа</div>';
        return;
      }
      
      matchesEl.innerHTML = matches.map(m => {
        const league = (m.league && m.league.name) || '—';
        const home = (m.teams && m.teams.home && m.teams.home.name) || 'Home';
        const away = (m.teams && m.teams.away && m.teams.away.name) || 'Away';
        const time = m.time || '';
        const scoreHome = m.scores && m.scores.home !== null ? m.scores.home : '';
        const scoreAway = m.scores && m.scores.away !== null ? m.scores.away : '';
        
        const scoreText = (scoreHome !== '' && scoreAway !== '') 
          ? `<div class="score">${scoreHome} - ${scoreAway}</div>` 
          : '';
        
        return `
          <div class="match">
            <div class="league">${league}</div>
            <div class="vs">⚽ ${home} — ${away}</div>
            ${scoreText}
            <div class="time">🕒 ${time}</div>
          </div>
        `;
      }).join('');
      
      // Показываем уведомление об успешной загрузке
      showNotification(`Загружено ${matches.length} матчей`);
      
    } catch(e) {
      console.error('Error loading matches:', e);
      let errorMessage = '❌ Ошибка при загрузке матчей';
      
      if (e.message.includes('авторизации')) {
        errorMessage = '❌ ' + e.message;
      }
      
      matchesEl.innerHTML = `<div class="match error">${errorMessage}</div>`;
      showNotification(errorMessage, true);
    }
  }

  // Обработчики событий
  refreshBtn.addEventListener('click', loadMatches);
  
  closeBtn.addEventListener('click', () => { 
    try { 
      tg.close(); 
    } catch(e) {
      console.log('Cannot close WebApp:', e);
      showNotification('Приложение можно закрыть через Telegram', false);
    }
  });

  // Добавляем обработчик для кнопки "Назад" в Telegram
  tg.BackButton.show();
  tg.BackButton.onClick(() => {
    tg.close();
  });

  // Показываем информацию о пользователе (опционально)
  function displayUserInfo() {
    const user = tg.initDataUnsafe.user;
    if (user) {
      console.log('User info:', user);
      // Можно добавить отображение информации о пользователе в интерфейсе
      const userInfo = document.createElement('div');
      userInfo.style.cssText = 'text-align: center; margin-bottom: 10px; font-size: 12px; color: #666;';
      userInfo.textContent = `Привет, ${user.first_name || 'пользователь'}!`;
      matchesEl.parentNode.insertBefore(userInfo, matchesEl);
    }
  }

  // Инициализация при загрузке
  document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, что мы в Telegram Web App
    if (!tg.initData) {
      matchesEl.innerHTML = '<div class="match error">Пожалуйста, откройте приложение через Telegram</div>';
      return;
    }
    
    displayUserInfo();
    loadMatches();
  });

  // Initial load
  loadMatches();
})();
