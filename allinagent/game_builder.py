"""Game builder for ALLINAGENT.

Creates playable browser games with HTML5 Canvas.
Supports player movement, enemies, health, score, levels, menus,
pause, restart, win/lose states, difficulty, and settings.
"""
from __future__ import annotations

from .tools import WorkspaceTools
from .website_builder import CreationSpec


class GameBuilder:
    """Builds complete browser game projects."""

    def __init__(self, tools: WorkspaceTools) -> None:
        self.tools = tools

    def build_game(self, spec: CreationSpec) -> list[str]:
        """Create a complete game project. Returns list of created files."""
        created: list[str] = []
        base = spec.target_path or spec.name

        # HTML
        html = self._generate_html(spec)
        result = self.tools.write_file(f"{base}/index.html", html)
        if "WRITE OK" in result:
            created.append(f"{base}/index.html")

        # CSS
        css = self._generate_css(spec)
        result = self.tools.write_file(f"{base}/styles.css", css)
        if "WRITE OK" in result:
            created.append(f"{base}/styles.css")

        # Game JS
        js = self._generate_js(spec)
        result = self.tools.write_file(f"{base}/game.js", js)
        if "WRITE OK" in result:
            created.append(f"{base}/game.js")

        # README
        readme = self._generate_readme(spec)
        result = self.tools.write_file(f"{base}/README.md", readme)
        if "WRITE OK" in result:
            created.append(f"{base}/README.md")

        return created

    def _generate_html(self, spec: CreationSpec) -> str:
        name = spec.name.replace("-", " ").title()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="game-container">
    <div id="hud">
      <div class="hud-item">Score: <span id="score">0</span></div>
      <div class="hud-item">Health: <span id="health">3</span></div>
      <div class="hud-item">Level: <span id="level">1</span></div>
    </div>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <div id="menu" class="overlay">
      <h1>{name}</h1>
      <button id="start-btn" class="btn">Start Game</button>
      <div class="difficulty">
        <label for="difficulty">Difficulty:</label>
        <select id="difficulty">
          <option value="easy">Easy</option>
          <option value="normal" selected>Normal</option>
          <option value="hard">Hard</option>
        </select>
      </div>
    </div>
    <div id="pause-menu" class="overlay hidden">
      <h2>Paused</h2>
      <button id="resume-btn" class="btn">Resume</button>
      <button id="restart-btn" class="btn">Restart</button>
    </div>
    <div id="game-over" class="overlay hidden">
      <h2 id="end-title">Game Over</h2>
      <p id="end-message"></p>
      <button id="play-again-btn" class="btn">Play Again</button>
    </div>
    <div id="settings" class="overlay hidden">
      <h2>Settings</h2>
      <div class="setting">
        <label>Sound: <input type="checkbox" id="sound-toggle" checked></label>
      </div>
      <button id="close-settings" class="btn">Close</button>
    </div>
    <div class="controls-hint">
      <p>Arrow keys to move | Space to shoot | P to pause | S for settings</p>
    </div>
  </div>
  <script src="game.js"></script>
</body>
</html>"""

    def _generate_css(self, spec: CreationSpec) -> str:
        return """:root {
  --bg: #0a0a1a;
  --accent: #e94560;
  --secondary: #0f3460;
  --text: #e0e0e0;
  --green: #2ecc71;
  --red: #e74c3c;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, sans-serif;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

#game-container {
  position: relative;
  text-align: center;
}

#hud {
  display: flex;
  justify-content: center;
  gap: 2rem;
  padding: 1rem;
  font-size: 1.2rem;
  font-weight: bold;
}

.hud-item { color: var(--accent); }

canvas {
  border: 2px solid var(--accent);
  border-radius: 8px;
  background: #000;
  display: block;
}

.overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(10, 10, 26, 0.95);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  border-radius: 8px;
}

.overlay.hidden { display: none; }

.overlay h1, .overlay h2 {
  color: var(--accent);
  font-size: 2.5rem;
}

.btn {
  padding: 0.8rem 2rem;
  font-size: 1.1rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4);
}

.difficulty, .setting {
  margin: 1rem 0;
}

.difficulty select, .setting input {
  padding: 0.5rem;
  font-size: 1rem;
  background: var(--secondary);
  color: var(--text);
  border: 1px solid var(--accent);
  border-radius: 4px;
}

.controls-hint {
  margin-top: 1rem;
  opacity: 0.6;
  font-size: 0.9rem;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

#end-message {
  font-size: 1.2rem;
  animation: pulse 2s infinite;
}
"""

    def _generate_js(self, spec: CreationSpec) -> str:
        features = spec.features or []
        has_enemies = "enemies" in features or "game" in (spec.kind or "")
        has_levels = "levels" in features
        has_sound = "sound" in features

        return f"""// {spec.name} - Game Engine

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const W = canvas.width;
const H = canvas.height;

// Game state
let gameState = 'menu'; // menu, playing, paused, gameover, win
let score = 0;
let health = 3;
let level = 1;
let soundEnabled = true;
let lastTime = 0;

// Player
const player = {{
  x: W / 2,
  y: H - 60,
  w: 40,
  h: 40,
  speed: 6,
  bullets: [],
  cooldown: 0,
}};

// Enemies
let enemies = [];
let enemyBullets = [];
let particles = [];

// Input
const keys = {{}};

document.addEventListener('keydown', e => {{
  keys[e.key.toLowerCase()] = true;
  keys[e.code] = true;
  if (e.key === 'p' || e.key === 'P') togglePause();
  if (e.key === 's' || e.key === 'S') toggleSettings();
  if (e.key === ' ') {{
    e.preventDefault();
    shoot();
  }}
}});
document.addEventListener('keyup', e => {{
  keys[e.key.toLowerCase()] = false;
  keys[e.code] = false;
}});

// Difficulty settings
const difficulties = {{
  easy: {{ enemySpeed: 1.5, spawnRate: 0.02, enemyHealth: 1, playerSpeed: 7 }},
  normal: {{ enemySpeed: 2.5, spawnRate: 0.03, enemyHealth: 1, playerSpeed: 6 }},
  hard: {{ enemySpeed: 3.5, spawnRate: 0.04, enemyHealth: 2, playerSpeed: 5 }},
}};
let currentDifficulty = 'normal';

// UI elements
const startBtn = document.getElementById('start-btn');
const resumeBtn = document.getElementById('resume-btn');
const restartBtn = document.getElementById('restart-btn');
const playAgainBtn = document.getElementById('play-again-btn');
const difficultySelect = document.getElementById('difficulty');
const soundToggle = document.getElementById('sound-toggle');
const closeSettings = document.getElementById('close-settings');
const menuEl = document.getElementById('menu');
const pauseMenuEl = document.getElementById('pause-menu');
const gameOverEl = document.getElementById('game-over');
const settingsEl = document.getElementById('settings');
const endTitle = document.getElementById('end-title');
const endMessage = document.getElementById('end-message');
const scoreEl = document.getElementById('score');
const healthEl = document.getElementById('health');
const levelEl = document.getElementById('level');

startBtn.addEventListener('click', startGame);
resumeBtn.addEventListener('click', togglePause);
restartBtn.addEventListener('click', restartGame);
playAgainBtn.addEventListener('click', restartGame);
closeSettings.addEventListener('click', () => toggleSettings());
difficultySelect.addEventListener('change', e => {{
  currentDifficulty = e.target.value;
}});
soundToggle.addEventListener('change', e => {{
  soundEnabled = e.target.checked;
}});

function startGame() {{
  menuEl.classList.add('hidden');
  resetGame();
  gameState = 'playing';
  requestAnimationFrame(gameLoop);
}}

function resetGame() {{
  score = 0;
  health = 3;
  level = 1;
  player.x = W / 2;
  player.y = H - 60;
  player.bullets = [];
  enemies = [];
  enemyBullets = [];
  particles = [];
  updateHUD();
}}

function restartGame() {{
  resetGame();
  pauseMenuEl.classList.add('hidden');
  gameOverEl.classList.add('hidden');
  settingsEl.classList.add('hidden');
  gameState = 'playing';
  requestAnimationFrame(gameLoop);
}}

function togglePause() {{
  if (gameState === 'playing') {{
    gameState = 'paused';
    pauseMenuEl.classList.remove('hidden');
  }} else if (gameState === 'paused') {{
    gameState = 'playing';
    pauseMenuEl.classList.add('hidden');
    requestAnimationFrame(gameLoop);
  }}
}}

function toggleSettings() {{
  if (gameState === 'playing' || gameState === 'paused') {{
    settingsEl.classList.toggle('hidden');
  }}
}}

function shoot() {{
  if (gameState !== 'playing' || player.cooldown > 0) return;
  player.bullets.push({{ x: player.x + player.w / 2, y: player.y, w: 4, h: 12, speed: 10 }});
  player.cooldown = 15;
}}

function spawnEnemy() {{
  const diff = difficulties[currentDifficulty];
  enemies.push({{
    x: Math.random() * (W - 40),
    y: -40,
    w: 35,
    h: 35,
    speed: diff.enemySpeed,
    health: diff.enemyHealth,
    type: Math.random() < 0.3 ? 'shooter' : 'chaser',
    shootCooldown: Math.floor(Math.random() * 60) + 60,
  }});
}}

function spawnParticles(x, y, color, count) {{
  for (let i = 0; i < count; i++) {{
    particles.push({{
      x: x, y: y,
      vx: (Math.random() - 0.5) * 6,
      vy: (Math.random() - 0.5) * 6,
      life: 30,
      color: color,
    }});
  }}
}}

function updateHUD() {{
  scoreEl.textContent = score;
  healthEl.textContent = health;
  levelEl.textContent = level;
}}

function update() {{
  const diff = difficulties[currentDifficulty];

  // Player movement
  if (keys['arrowleft'] || keys['a']) player.x -= player.speed;
  if (keys['arrowright'] || keys['d']) player.x += player.speed;
  player.x = Math.max(0, Math.min(W - player.w, player.x));
  if (player.cooldown > 0) player.cooldown--;

  // Player bullets
  player.bullets = player.bullets.filter(b => {{
    b.y -= b.speed;
    return b.y > 0;
  }});

  // Spawn enemies
  if (Math.random() < diff.spawnRate * (1 + level * 0.1)) {{
    spawnEnemy();
  }}

  // Update enemies
  enemies.forEach((e, i) => {{
    e.y += e.speed;
    if (e.type === 'shooter') {{
      e.shootCooldown--;
      if (e.shootCooldown <= 0) {{
        enemyBullets.push({{ x: e.x + e.w / 2, y: e.y + e.h, w: 4, h: 10, speed: 4 }});
        e.shootCooldown = 90;
      }}
    }}

    // Collision with player bullets
    player.bullets.forEach((b, bi) => {{
      if (b.x < e.x + e.w && b.x + b.w > e.x &&
          b.y < e.y + e.h && b.y + b.h > e.y) {{
        player.bullets.splice(bi, 1);
        e.health--;
        spawnParticles(b.x, b.y, '#e94560', 5);
        if (e.health <= 0) {{
          enemies.splice(i, 1);
          score += 10;
          spawnParticles(e.x, e.y, '#2ecc71', 10);
          updateHUD();
        }}
      }}
    }});

    // Collision with player
    if (e.x < player.x + player.w && e.x + e.w > player.x &&
        e.y < player.y + player.h && e.y + e.h > player.y) {{
      enemies.splice(i, 1);
      health--;
      spawnParticles(player.x, player.y, '#e74c3c', 15);
      updateHUD();
      if (health <= 0) {{
        gameOver(false);
      }}
    }}

    // Off screen
    if (e.y > H) enemies.splice(i, 1);
  }});

  // Enemy bullets
  enemyBullets = enemyBullets.filter(b => {{
    b.y += b.speed;
    if (b.x < player.x + player.w && b.x + b.w > player.x &&
        b.y < player.y + player.h && b.y + b.h > player.y) {{
      health--;
      spawnParticles(player.x, player.y, '#e74c3c', 10);
      updateHUD();
      if (health <= 0) gameOver(false);
      return false;
    }}
    return b.y < H;
  }});

  // Particles
  particles = particles.filter(p => {{
    p.x += p.vx;
    p.y += p.vy;
    p.life--;
    return p.life > 0;
  }});

  // Level progression
  if (score > 0 && score % 100 === 0 && score > 0) {{
    level = Math.floor(score / 100) + 1;
    updateHUD();
  }}
}}

function draw() {{
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = '#0a0a1a';
  ctx.fillRect(0, 0, W, H);

  // Stars
  ctx.fillStyle = 'rgba(255,255,255,0.3)';
  for (let i = 0; i < 50; i++) {{
    ctx.fillRect(Math.random() * W, Math.random() * H, 1, 1);
  }}

  // Player
  ctx.fillStyle = '#e94560';
  ctx.fillRect(player.x, player.y, player.w, player.h);
  ctx.fillStyle = '#fff';
  ctx.fillRect(player.x + player.w / 2 - 2, player.y - 10, 4, 10);

  // Player bullets
  ctx.fillStyle = '#2ecc71';
  player.bullets.forEach(b => ctx.fillRect(b.x, b.y, b.w, b.h));

  // Enemies
  enemies.forEach(e => {{
    ctx.fillStyle = e.type === 'shooter' ? '#e67e22' : '#9b59b6';
    ctx.fillRect(e.x, e.y, e.w, e.h);
  }});

  // Enemy bullets
  ctx.fillStyle = '#e74c3c';
  enemyBullets.forEach(b => ctx.fillRect(b.x, b.y, b.w, b.h));

  // Particles
  particles.forEach(p => {{
    ctx.fillStyle = p.color;
    ctx.globalAlpha = p.life / 30;
    ctx.fillRect(p.x, p.y, 3, 3);
    ctx.globalAlpha = 1;
  }});
}}

function gameOver(won) {{
  gameState = 'gameover';
  if (won) {{
    endTitle.textContent = 'You Win!';
    endMessage.textContent = `Final Score: ${{score}} | Level: ${{level}}`;
  }} else {{
    endTitle.textContent = 'Game Over';
    endMessage.textContent = `Score: ${{score}} | Level: ${{level}}`;
  }}
  gameOverEl.classList.remove('hidden');
}}

function gameLoop(timestamp) {{
  if (gameState !== 'playing') return;
  const dt = timestamp - lastTime;
  lastTime = timestamp;
  update();
  draw();
  requestAnimationFrame(gameLoop);
}}
"""

    def _generate_readme(self, spec: CreationSpec) -> str:
        name = spec.name.replace("-", " ").title()
        return f"""# {name}

A browser game built with HTML5 Canvas. Generated by ALLINAGENT v1.2.5.

## How to Play

- Arrow keys or A/D to move
- Space to shoot
- P to pause
- S for settings

## Features

- Player movement and shooting
- Enemy AI (chasers and shooters)
- Health system (3 lives)
- Score tracking
- Level progression (increasing difficulty)
- Start menu with difficulty selection
- Pause menu
- Game over / win screen
- Particle effects
- Sound toggle
- Settings menu

## Difficulty Levels

- **Easy**: Slower enemies, more player speed
- **Normal**: Balanced gameplay
- **Hard**: Faster enemies, more enemy health

## Technologies

- HTML5 Canvas
- Vanilla JavaScript
- CSS3

## Usage

Open `index.html` in your browser, or serve locally:

```bash
python -m http.server 8000
```

Visit `http://localhost:8000`.

Generated by ALLINAGENT v1.2.5.
"""
