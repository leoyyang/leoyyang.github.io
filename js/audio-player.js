class PodcastPlayer {
  constructor() {
    this.currentPlayer = null;
    this.currentButton = null;
    this.init();
  }

  init() {
    // 如果DOM已经加载完成，立即执行
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.attachEventListeners();
      });
    } else {
      // DOM已经加载完成
      this.attachEventListeners();
    }
  }

  attachEventListeners() {
    console.log('Attaching podcast player event listeners...');
    const buttons = document.querySelectorAll('.podcast-btn');
    console.log('Found podcast buttons:', buttons.length);
    
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('Podcast button clicked');
        this.handlePodcastClick(btn);
      });
    });

    document.addEventListener('click', (e) => {
      if (this.currentPlayer && 
          !this.currentPlayer.contains(e.target) && 
          !e.target.classList.contains('podcast-btn')) {
        if (!this.currentPlayer.querySelector('audio').paused) {
          return;
        }
        this.closePlayer();
      }
    });
  }

  handlePodcastClick(btn) {
    const podcastData = {
      en: btn.dataset.podcastEn,
      zh: btn.dataset.podcastZh,
      title: btn.dataset.title
    };

    // 如果点击的是同一个按钮，关闭播放器
    if (this.currentButton === btn && this.currentPlayer) {
      this.closePlayer();
      return;
    }

    // 如果有其他播放器打开，先关闭
    if (this.currentPlayer) {
      this.closePlayer();
    }

    this.currentButton = btn;
    this.createPlayer(podcastData, btn);
  }

  createPlayer(podcastData, btn) {
    // 找到最近的publication-card
    const card = btn.closest('.publication-card') || btn.closest('.stream-item');
    if (!card) {
      console.error('Could not find publication card');
      return;
    }

    // 创建overlay
    const overlay = document.createElement('div');
    overlay.className = 'podcast-overlay';
    
    const playerHTML = `
      <div class="podcast-player">
        <div class="podcast-player-header">
          <h4>${podcastData.title || 'Podcast'}</h4>
          <button class="podcast-close" aria-label="Close player">×</button>
        </div>
        
        <div class="podcast-language-selector">
          ${podcastData.en ? '<button class="lang-btn active" data-lang="en">English</button>' : ''}
          ${podcastData.zh ? '<button class="lang-btn" data-lang="zh">中文</button>' : ''}
        </div>
        
        <audio class="podcast-audio" preload="metadata">
          <source src="${podcastData.en || podcastData.zh}" type="audio/mpeg">
          Your browser does not support the audio element.
        </audio>
        
        <div class="podcast-controls">
          <button class="play-pause-btn" aria-label="Play/Pause">
            <svg class="play-icon" viewBox="0 0 24 24" width="24" height="24">
              <path fill="currentColor" d="M8 5v14l11-7z"/>
            </svg>
            <svg class="pause-icon" style="display:none" viewBox="0 0 24 24" width="24" height="24">
              <path fill="currentColor" d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
          </button>
          
          <div class="time-display">
            <span class="current-time">0:00</span> / <span class="duration">0:00</span>
          </div>
          
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill"></div>
            </div>
          </div>
          
          <div class="volume-container">
            <button class="volume-btn" aria-label="Mute/Unmute">
              <svg class="volume-icon" viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
              </svg>
              <svg class="mute-icon" style="display:none" viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
              </svg>
            </button>
            <input type="range" class="volume-slider" min="0" max="100" value="70">
          </div>
          
          <button class="speed-btn" aria-label="Playback speed">1x</button>
        </div>
      </div>
    `;

    overlay.innerHTML = playerHTML;
    
    // 添加到card中
    card.style.position = 'relative';
    card.appendChild(overlay);
    
    // 添加半透明效果到card的其他内容
    card.classList.add('podcast-playing');
    
    this.currentPlayer = overlay;
    this.currentCard = card;
    this.initPlayerControls(overlay, podcastData);
    
    // 触发动画
    setTimeout(() => {
      overlay.classList.add('active');
    }, 10);
  }

  initPlayerControls(container, podcastData) {
    const audio = container.querySelector('.podcast-audio');
    const playPauseBtn = container.querySelector('.play-pause-btn');
    const playIcon = container.querySelector('.play-icon');
    const pauseIcon = container.querySelector('.pause-icon');
    const progressBar = container.querySelector('.progress-bar');
    const progressFill = container.querySelector('.progress-fill');
    const currentTimeSpan = container.querySelector('.current-time');
    const durationSpan = container.querySelector('.duration');
    const volumeBtn = container.querySelector('.volume-btn');
    const volumeSlider = container.querySelector('.volume-slider');
    const volumeIcon = container.querySelector('.volume-icon');
    const muteIcon = container.querySelector('.mute-icon');
    const speedBtn = container.querySelector('.speed-btn');
    const closeBtn = container.querySelector('.podcast-close');
    const langBtns = container.querySelectorAll('.lang-btn');

    const speeds = [1, 1.25, 1.5, 1.75, 2];
    let currentSpeedIndex = 0;

    audio.volume = 0.7;

    audio.addEventListener('loadedmetadata', () => {
      durationSpan.textContent = this.formatTime(audio.duration);
    });

    audio.addEventListener('timeupdate', () => {
      const progress = (audio.currentTime / audio.duration) * 100;
      progressFill.style.width = `${progress}%`;
      currentTimeSpan.textContent = this.formatTime(audio.currentTime);
    });

    audio.addEventListener('ended', () => {
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
    });

    playPauseBtn.addEventListener('click', () => {
      if (audio.paused) {
        audio.play();
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
      } else {
        audio.pause();
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
      }
    });

    progressBar.addEventListener('click', (e) => {
      const rect = progressBar.getBoundingClientRect();
      const percent = (e.clientX - rect.left) / rect.width;
      audio.currentTime = percent * audio.duration;
    });

    volumeBtn.addEventListener('click', () => {
      if (audio.muted) {
        audio.muted = false;
        volumeIcon.style.display = 'block';
        muteIcon.style.display = 'none';
        volumeSlider.value = audio.volume * 100;
      } else {
        audio.muted = true;
        volumeIcon.style.display = 'none';
        muteIcon.style.display = 'block';
        volumeSlider.value = 0;
      }
    });

    volumeSlider.addEventListener('input', (e) => {
      const volume = e.target.value / 100;
      audio.volume = volume;
      audio.muted = false;
      
      if (volume === 0) {
        volumeIcon.style.display = 'none';
        muteIcon.style.display = 'block';
      } else {
        volumeIcon.style.display = 'block';
        muteIcon.style.display = 'none';
      }
    });

    speedBtn.addEventListener('click', () => {
      currentSpeedIndex = (currentSpeedIndex + 1) % speeds.length;
      const speed = speeds[currentSpeedIndex];
      audio.playbackRate = speed;
      speedBtn.textContent = `${speed}x`;
    });

    langBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const lang = btn.dataset.lang;
        const wasPlaying = !audio.paused;
        const currentTime = audio.currentTime;
        
        langBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const newSrc = lang === 'en' ? podcastData.en : podcastData.zh;
        if (newSrc && audio.src !== newSrc) {
          audio.src = newSrc;
          audio.load();
          
          audio.addEventListener('loadedmetadata', () => {
            if (currentTime > 0 && currentTime < audio.duration) {
              audio.currentTime = currentTime;
            }
            if (wasPlaying) {
              audio.play();
            }
          }, { once: true });
        }
      });
    });

    closeBtn.addEventListener('click', () => {
      this.closePlayer();
    });
  }

  closePlayer() {
    if (this.currentPlayer) {
      const audio = this.currentPlayer.querySelector('.podcast-audio');
      if (audio) {
        audio.pause();
      }
      
      this.currentPlayer.classList.remove('active');
      
      if (this.currentCard) {
        this.currentCard.classList.remove('podcast-playing');
      }
      
      setTimeout(() => {
        if (this.currentPlayer) {
          this.currentPlayer.remove();
        }
        this.currentPlayer = null;
        this.currentCard = null;
        this.currentButton = null;
      }, 300);
    }
  }

  formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }
}

// 初始化播放器
console.log('Initializing PodcastPlayer...');
const podcastPlayer = new PodcastPlayer();
console.log('PodcastPlayer initialized');