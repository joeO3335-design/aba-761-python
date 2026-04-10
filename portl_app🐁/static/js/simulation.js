// ============================================================
// PORTL Simulation
// ============================================================

// ---------------------------------------------------------------------------
// 47 PORTL Exercises
// ---------------------------------------------------------------------------
const PORTL_EXERCISES = [
  { num:  1, title: "Charge the Clicker",               chapter:  1, procedure: "shaping",                  behavior: "Sits still while clicker charges",            goal: "Classically condition the clicker as a conditioned reinforcer by pairing it with a treat 10 times." },
  { num:  2, title: "The Name Game",                    chapter:  1, procedure: "shaping",                  behavior: "Orients / looks toward teacher",              goal: "Reinforce the learner for responding to their name by delivering a click+treat." },
  { num:  3, title: "Free Shaping",                     chapter:  2, procedure: "shaping",                  behavior: "Any offered object interaction",              goal: "Free-shape the learner to interact with a target object through successive approximations." },
  { num:  4, title: "Shaping a New Behavior",           chapter:  2, procedure: "shaping",                  behavior: "Successive approximations to target",         goal: "Use shaping to build a completely new behavior from scratch across multiple intervals." },
  { num:  5, title: "100 Reinforcers",                  chapter:  2, procedure: "shaping",                  behavior: "Any behavior — high rate",                    goal: "Deliver 100 reinforcers as quickly as possible to build fluency and teacher mechanics." },
  { num:  6, title: "Differential Reinforcement",       chapter:  3, procedure: "differential_reinforcement", behavior: "Target behavior vs. other",                 goal: "Reinforce one specific behavior while withholding reinforcement for all other behaviors." },
  { num:  7, title: "DRI — Incompatible Behavior",      chapter:  3, procedure: "differential_reinforcement", behavior: "Behavior incompatible with problem",        goal: "Reinforce a behavior that is physically incompatible with an undesired behavior." },
  { num:  8, title: "DRO — Other Behavior",             chapter:  3, procedure: "differential_reinforcement", behavior: "Any behavior except target problem",        goal: "Reinforce the absence of the target problem behavior for a set interval." },
  { num:  9, title: "DRL — Low Rate",                   chapter:  3, procedure: "differential_reinforcement", behavior: "Target behavior at low rate",               goal: "Reinforce the behavior only when it occurs at or below a specified rate per interval." },
  { num: 10, title: "DRH — High Rate",                  chapter:  3, procedure: "differential_reinforcement", behavior: "Target behavior at high rate",              goal: "Reinforce the behavior only when it occurs at or above a specified rate per interval." },
  { num: 11, title: "Errorless Learning — Most-to-Least", chapter: 4, procedure: "errorless_learning",       behavior: "Touch correct object",                       goal: "Use a most-to-least prompt hierarchy to teach object selection with zero or near-zero errors." },
  { num: 12, title: "Errorless Learning — Least-to-Most", chapter: 4, procedure: "errorless_learning",       behavior: "Touch correct object",                       goal: "Use a least-to-most prompt hierarchy, adding prompts only when the learner does not respond." },
  { num: 13, title: "Progressive Prompt Delay",         chapter:  4, procedure: "errorless_learning",        behavior: "Touch correct object independently",         goal: "Systematically increase the delay before prompting to build independent responding." },
  { num: 14, title: "Constant Prompt Delay",            chapter:  4, procedure: "errorless_learning",        behavior: "Touch correct object independently",         goal: "Use a fixed delay before prompting and fade the prompt over trials." },
  { num: 15, title: "Stimulus Control — Discrimination", chapter: 5, procedure: "stimulus_control",          behavior: "Touch S+ object only",                       goal: "Teach the learner to respond to S+ and not respond to S− using simple discrimination training." },
  { num: 16, title: "Simple Discrimination",            chapter:  5, procedure: "stimulus_control",          behavior: "S+ vs. S− selection",                        goal: "Present S+ and S− trials in alternation; reinforce correct selection of S+." },
  { num: 17, title: "Conditional Discrimination",       chapter:  5, procedure: "stimulus_control",          behavior: "Match sample to comparison",                 goal: "Teach the learner to select a comparison stimulus based on a sample stimulus (matching-to-sample)." },
  { num: 18, title: "Successive Discrimination",        chapter:  5, procedure: "stimulus_control",          behavior: "Respond in S+ context only",                 goal: "Reinforce the target behavior only when the S+ is present; extinguish in the presence of S−." },
  { num: 19, title: "Multiple Schedules",               chapter:  5, procedure: "schedule",                  behavior: "Respond differentially to schedule signals",  goal: "Alternate between reinforcement and extinction components signaled by discriminative stimuli." },
  { num: 20, title: "Behavior Chain — Forward",         chapter:  6, procedure: "behavior_chain",            behavior: "Step 1 → Step 2 → Step 3 sequence",          goal: "Teach each step of a behavior chain starting from the first step using forward chaining." },
  { num: 21, title: "Behavior Chain — Backward",        chapter:  6, procedure: "behavior_chain",            behavior: "Final step → second-to-last → first",        goal: "Teach each step of a behavior chain starting from the last step using backward chaining." },
  { num: 22, title: "Total Task Presentation",          chapter:  6, procedure: "behavior_chain",            behavior: "Complete chain from start to finish",        goal: "Prompt all steps of a chain on every trial, fading prompts across sessions." },
  { num: 23, title: "Behavior Chain Interruption",      chapter:  6, procedure: "behavior_chain",            behavior: "Mand or request within chain",               goal: "Interrupt the learner's preferred behavior chain to create an opportunity to mand." },
  { num: 24, title: "CRF — Continuous Reinforcement",   chapter:  7, procedure: "schedule",                  behavior: "Any target behavior",                        goal: "Reinforce every instance of the target behavior (FR-1); used during initial skill acquisition." },
  { num: 25, title: "FR Schedule",                      chapter:  7, procedure: "schedule",                  behavior: "Repeated target behavior",                   goal: "Reinforce after a fixed number of responses (e.g., FR-3: every third response)." },
  { num: 26, title: "VR Schedule",                      chapter:  7, procedure: "schedule",                  behavior: "Repeated target behavior",                   goal: "Reinforce after a variable number of responses around a mean (e.g., VR-5); produces steady high rates." },
  { num: 27, title: "FI Schedule",                      chapter:  7, procedure: "schedule",                  behavior: "Responding after time interval",             goal: "Reinforce the first response after a fixed time interval (e.g., FI-1 min); produces scallop pattern." },
  { num: 28, title: "VI Schedule",                      chapter:  7, procedure: "schedule",                  behavior: "Responding after variable interval",         goal: "Reinforce the first response after a variable time interval; produces steady moderate rates." },
  { num: 29, title: "Extinction",                       chapter:  7, procedure: "differential_reinforcement", behavior: "Previously reinforced behavior",            goal: "Discontinue all reinforcement for a previously reinforced behavior; observe extinction burst and gradual decrease." },
  { num: 30, title: "Spontaneous Recovery",             chapter:  7, procedure: "differential_reinforcement", behavior: "Previously extinguished behavior",          goal: "After extinction, allow a rest period and observe re-emergence of extinguished behavior." },
  { num: 31, title: "Generalization Training",          chapter:  8, procedure: "stimulus_control",          behavior: "Target behavior across multiple SDs",        goal: "Train the behavior in multiple environments, with multiple trainers, and with varied stimuli." },
  { num: 32, title: "Maintenance Training",             chapter:  8, procedure: "schedule",                  behavior: "Previously acquired behavior",               goal: "Thin the reinforcement schedule systematically to maintain the behavior without continuous reinforcement." },
  { num: 33, title: "Thinning — VR",                   chapter:  8, procedure: "schedule",                  behavior: "Target behavior on lean schedule",           goal: "Gradually increase the VR value across intervals while maintaining high-rate responding." },
  { num: 34, title: "Natural Reinforcement",            chapter:  8, procedure: "shaping",                   behavior: "Functional behavior in context",             goal: "Transition from arbitrary reinforcers to natural/intrinsic reinforcers embedded in the activity." },
  { num: 35, title: "Mand Training",                    chapter:  9, procedure: "shaping",                   behavior: "Request / mand for desired item",            goal: "Establish a functional mand (request) by capturing or contrive motivating operations and reinforcing mands." },
  { num: 36, title: "Tact Training",                    chapter:  9, procedure: "stimulus_control",          behavior: "Label or name object when shown",            goal: "Teach the learner to label objects or actions in their environment as a tact (verbal operant)." },
  { num: 37, title: "Echoic Training",                  chapter:  9, procedure: "errorless_learning",        behavior: "Repeat spoken word or sound",                goal: "Establish vocal imitation by reinforcing close approximations and successive approximations to the model." },
  { num: 38, title: "Intraverbal Training",             chapter:  9, procedure: "stimulus_control",          behavior: "Verbal response to verbal antecedent",       goal: "Teach conversational responses, fill-ins, and WH-questions as intraverbal verbal operants." },
  { num: 39, title: "Listener Responding",              chapter:  9, procedure: "stimulus_control",          behavior: "Follow instruction / touch named item",      goal: "Teach the learner to respond to verbal instructions by selecting or touching the correct item." },
  { num: 40, title: "Imitation Training",               chapter: 10, procedure: "errorless_learning",        behavior: "Copy motor action modeled by teacher",       goal: "Use a Do-as-I-Do procedure to build generalized imitation across novel motor actions." },
  { num: 41, title: "Textual Behavior",                 chapter: 10, procedure: "stimulus_control",          behavior: "Read written word aloud",                    goal: "Teach the learner to emit a vocal response under the control of written text (reading)." },
  { num: 42, title: "Transcription",                    chapter: 10, procedure: "stimulus_control",          behavior: "Write or type dictated word",                goal: "Teach the learner to write or type a word under the control of a spoken model (dictation)." },
  { num: 43, title: "PORTL Token Economy",              chapter: 11, procedure: "schedule",                  behavior: "Any target behavior",                        goal: "Implement a token economy: deliver tokens contingent on behavior and exchange for backup reinforcers." },
  { num: 44, title: "Group Contingency",                chapter: 11, procedure: "differential_reinforcement", behavior: "On-task group behavior",                   goal: "Set a shared group criterion; reinforce the group when the collective behavior meets the standard." },
  { num: 45, title: "Behavioral Momentum",              chapter: 11, procedure: "schedule",                  behavior: "High-p then low-p behavior sequence",        goal: "Precede low-probability requests with a sequence of high-probability requests to build momentum." },
  { num: 46, title: "Competing Stimulus Assessment",    chapter: 12, procedure: "differential_reinforcement", behavior: "Engagement with competing item",            goal: "Assess which stimuli compete most effectively with a problem behavior to identify potential reinforcers." },
  { num: 47, title: "Single-Subject Research Design",   chapter: 12, procedure: "shaping",                   behavior: "Any operationally defined behavior",         goal: "Design and implement a simple reversal (ABA) design to demonstrate experimental control over a target behavior." },
];

// ---------------------------------------------------------------------------
// PORTL objects
// ---------------------------------------------------------------------------
const PORTL_OBJECTS = [
  { emoji: '🔵', label: 'Blue disc'     },
  { emoji: '🟥', label: 'Red square'    },
  { emoji: '🟨', label: 'Yellow square' },
  { emoji: '🟢', label: 'Green circle'  },
  { emoji: '🔺', label: 'Orange tri'    },
  { emoji: '🟪', label: 'Purple sq'     },
  { emoji: '⬜', label: 'White sq'      },
  { emoji: '⬛', label: 'Black sq'      },
  { emoji: '🔶', label: 'Gold diamond'  },
  { emoji: '🔷', label: 'Blue diamond'  },
  { emoji: '🟫', label: 'Brown sq'      },
  { emoji: '⭕', label: 'Ring'          },
];

// ---------------------------------------------------------------------------
// Gamification
// ---------------------------------------------------------------------------
const LEVEL_THRESHOLDS  = [0,150,350,650,1050,1600,2300,3100,4100,5300,6700,8300,10200,12400,15000];
const TIER_UNLOCK_LEVELS = [0,1,4,8,12];
const TIER_NAMES         = ['','Novice','Apprentice','Practitioner','Expert'];

const EXERCISE_TIERS = {};
[1,2,3,4,5,6,7,8,9,10,11,12].forEach(n => EXERCISE_TIERS[n] = 1);
[13,14,15,16,17,18,19,20,21,22,23,24,25].forEach(n => EXERCISE_TIERS[n] = 2);
[26,27,28,29,30,31,32,33,34,35,36,37].forEach(n => EXERCISE_TIERS[n] = 3);
[38,39,40,41,42,43,44,45,46,47].forEach(n => EXERCISE_TIERS[n] = 4);

function loadGame() {
  try {
    const s = JSON.parse(localStorage.getItem('portl_game') || '{}');
    return { xp: s.xp||0, achievements: s.achievements||[], totalReinforcements: s.totalReinforcements||0, sessionsCompleted: s.sessionsCompleted||0 };
  } catch(e) { return { xp:0, achievements:[], totalReinforcements:0, sessionsCompleted:0 }; }
}
function saveGame() { localStorage.setItem('portl_game', JSON.stringify(GAME)); }

let GAME = loadGame();

function getLevel(xp) {
  let level = 1;
  for (let i = 0; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) level = i+1; else break;
  }
  return Math.min(level, LEVEL_THRESHOLDS.length);
}
function getLevelProgress(xp) {
  const level = getLevel(xp);
  const floor  = LEVEL_THRESHOLDS[level-1] || 0;
  const ceil   = LEVEL_THRESHOLDS[level];
  if (!ceil) return { pct:100, current: xp-floor, needed:0 };
  return { pct: Math.round(((xp-floor)/(ceil-floor))*100), current: xp-floor, needed: ceil-floor };
}
function isExerciseUnlocked(n) { return getLevel(GAME.xp) >= TIER_UNLOCK_LEVELS[EXERCISE_TIERS[n]||1]; }
function currentTierName() {
  const lv = getLevel(GAME.xp);
  for (let t=4;t>=1;t--) if (lv >= TIER_UNLOCK_LEVELS[t]) return TIER_NAMES[t];
  return TIER_NAMES[1];
}

function updateXPBar() {
  const lv   = getLevel(GAME.xp);
  const prog = getLevelProgress(GAME.xp);
  const el   = document.getElementById('xp-level-num');
  const bar  = document.getElementById('xp-bar-inner');
  const txt  = document.getElementById('xp-bar-text');
  const tot  = document.getElementById('xp-total');
  const tier = document.getElementById('xp-tier-label');
  if (el)   el.textContent   = lv;
  if (bar)  bar.style.width  = prog.pct + '%';
  if (txt)  txt.textContent  = prog.needed ? `${prog.current} / ${prog.needed} XP to level ${lv+1}` : 'MAX LEVEL';
  if (tot)  tot.textContent  = GAME.xp.toLocaleString() + ' XP';
  if (tier) tier.textContent = currentTierName();
  refreshExerciseDropdown();
}

function awardXP(amount) {
  const prevLevel = getLevel(GAME.xp);
  const actual    = (state.role === 'learner') ? Math.round(amount * 1.5) : amount;
  GAME.xp += actual;
  saveGame();
  updateXPBar();
  showXPPopup(actual);
  checkAchievements();
  if (getLevel(GAME.xp) > prevLevel) showLevelUp(getLevel(GAME.xp));
}

function showXPPopup(amount) {
  const p = document.createElement('div');
  p.className = 'xp-popup';
  p.textContent = '+' + amount + ' XP';
  document.body.appendChild(p);
  requestAnimationFrame(() => requestAnimationFrame(() => p.classList.add('xp-popup-go')));
  setTimeout(() => p.remove(), 1200);
}

function showLevelUp(level) {
  const tierIdx = TIER_UNLOCK_LEVELS.indexOf(level);
  const extra   = tierIdx > 0 ? `<p class="levelup-unlock">Unlocked: <strong>${TIER_NAMES[tierIdx]} exercises!</strong></p>` : '';
  const b = document.createElement('div');
  b.className = 'level-up-banner';
  b.innerHTML = `<div class="levelup-inner"><div class="levelup-star">★</div><div><h3>Level Up! → Level ${level}</h3>${extra}</div></div>`;
  document.body.appendChild(b);
  requestAnimationFrame(() => requestAnimationFrame(() => b.classList.add('levelup-show')));
  setTimeout(() => { b.classList.remove('levelup-show'); setTimeout(() => b.remove(), 400); }, 2800);
}

const ACHIEVEMENTS = [
  { id:'first_click',   label:'First Click',       desc:'Delivered your first conditioned reinforcer',        check:() => GAME.totalReinforcements >= 1   },
  { id:'ten_reinf',     label:'Ten Reinforcers',   desc:'Delivered 10 total reinforcers',                    check:() => GAME.totalReinforcements >= 10  },
  { id:'fifty_reinf',   label:'Halfway There',     desc:'Delivered 50 total reinforcers',                    check:() => GAME.totalReinforcements >= 50  },
  { id:'hundred_reinf', label:'Century',           desc:'Delivered 100 total reinforcers',                   check:() => GAME.totalReinforcements >= 100 },
  { id:'first_session', label:'First Session',     desc:'Completed your first full session',                 check:() => GAME.sessionsCompleted >= 1     },
  { id:'five_sessions', label:'Dedicated Trainer', desc:'Completed 5 sessions',                              check:() => GAME.sessionsCompleted >= 5     },
  { id:'tier2',         label:'Apprentice',        desc:'Reached Level 4 — Apprentice exercises unlocked',   check:() => getLevel(GAME.xp) >= 4          },
  { id:'tier3',         label:'Practitioner',      desc:'Reached Level 8 — Practitioner exercises unlocked', check:() => getLevel(GAME.xp) >= 8          },
  { id:'tier4',         label:'Expert',            desc:'Reached Level 12 — Expert exercises unlocked',      check:() => getLevel(GAME.xp) >= 12         },
];

function checkAchievements() {
  ACHIEVEMENTS.forEach(a => {
    if (!GAME.achievements.includes(a.id) && a.check()) {
      GAME.achievements.push(a.id);
      saveGame();
      showAchievementToast(a.label, a.desc);
    }
  });
}

function showAchievementToast(label, desc) {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'achievement-toast';
  t.innerHTML = `<span class="achievement-icon">🏆</span><div><strong>${label}</strong><p>${desc}</p></div>`;
  c.appendChild(t);
  requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('toast-show')));
  setTimeout(() => { t.classList.remove('toast-show'); setTimeout(() => t.remove(), 400); }, 3500);
}

// ---------------------------------------------------------------------------
// Exercise selector
// ---------------------------------------------------------------------------
function buildExerciseOptions() {
  const sel = document.getElementById('exercise-select');
  if (!sel) return;
  const grouped = {};
  PORTL_EXERCISES.forEach(ex => { if (!grouped[ex.chapter]) grouped[ex.chapter]=[]; grouped[ex.chapter].push(ex); });
  Object.keys(grouped).sort((a,b)=>+a-+b).forEach(ch => {
    const og = document.createElement('optgroup');
    og.label = `Chapter ${ch}`;
    grouped[ch].forEach(ex => {
      const opt = document.createElement('option');
      const tier = EXERCISE_TIERS[ex.num]||1;
      const ok   = isExerciseUnlocked(ex.num);
      opt.value   = ex.num;
      opt.textContent = ok ? `${ex.num}. ${ex.title}  [${TIER_NAMES[tier]}]`
                           : `🔒 ${ex.num}. ${ex.title}  — Level ${TIER_UNLOCK_LEVELS[tier]} required`;
      opt.disabled = !ok;
      og.appendChild(opt);
    });
    sel.appendChild(og);
  });

  // Populate target-object dropdown
  const objSel = document.getElementById('target-object-select');
  if (objSel && objSel.options.length === 0) {
    PORTL_OBJECTS.forEach((obj,i) => {
      const o = document.createElement('option');
      o.value = i; o.textContent = `${obj.emoji} ${obj.label}`;
      objSel.appendChild(o);
    });
  }
}

function refreshExerciseDropdown() {
  document.querySelectorAll('#exercise-select option[value]').forEach(opt => {
    const n = +opt.value; if (!n) return;
    const tier = EXERCISE_TIERS[n]||1;
    const ok   = isExerciseUnlocked(n);
    const ex   = PORTL_EXERCISES.find(e => e.num === n);
    if (!ex) return;
    opt.disabled    = !ok;
    opt.textContent = ok ? `${ex.num}. ${ex.title}  [${TIER_NAMES[tier]}]`
                         : `🔒 ${ex.num}. ${ex.title}  — Level ${TIER_UNLOCK_LEVELS[tier]} required`;
  });
}

function onExerciseChange() {
  const sel = document.getElementById('exercise-select');
  const box = document.getElementById('exercise-info');
  const val = sel.value;
  if (!val) { box.classList.add('hidden'); return; }
  const ex = PORTL_EXERCISES.find(e => e.num === +val);
  if (!ex) return;
  document.getElementById('procedure').value       = ex.procedure;
  document.getElementById('target-behavior').value = ex.behavior;
  document.getElementById('exercise-goal').textContent = ex.goal;
  box.classList.remove('hidden');
}

function onRoleChange() {
  const role = document.querySelector('input[name="role"]:checked').value;
  document.getElementById('target-object-group').classList.toggle('hidden', role !== 'learner');
  document.getElementById('schedule-type-group').classList.toggle('hidden', role !== 'learner');
}

// ---------------------------------------------------------------------------
// Board Builder
// ---------------------------------------------------------------------------
let boardPieces  = [];   // { id, objIdx, x, y, rotation }
let boardIdCount = 0;

function initBoardBuilder() {
  boardPieces  = [];
  boardIdCount = 0;

  // Palette — click to place, or drag onto board
  const palette = document.getElementById('piece-palette');
  if (!palette) return;
  palette.innerHTML = '';
  PORTL_OBJECTS.forEach((obj, i) => {
    const item = document.createElement('div');
    item.className = 'palette-item';
    item.draggable = true;
    item.innerHTML = `<span class="piece-emoji-sm">${obj.emoji}</span><span class="palette-label">${obj.label}</span>`;
    item.addEventListener('dragstart', e => { e.dataTransfer.setData('portl-obj', i); });
    item.addEventListener('click', () => {
      const board = document.getElementById('setup-board');
      const bw = board.offsetWidth, bh = board.offsetHeight;
      placePieceOnBoard(i, bw/2 - 40 + (Math.random()-0.5)*80, bh/2 - 40 + (Math.random()-0.5)*80);
    });
    palette.appendChild(item);
  });

  // Board drop zone
  const board = document.getElementById('setup-board');
  if (!board) return;
  board.innerHTML = '<div class="board-empty-hint">Drag objects here to set up the board</div>';
  board.addEventListener('dragover', e => e.preventDefault());
  board.addEventListener('drop', e => {
    e.preventDefault();
    const objIdx = parseInt(e.dataTransfer.getData('portl-obj'));
    if (isNaN(objIdx)) return;
    const rect = board.getBoundingClientRect();
    placePieceOnBoard(objIdx, e.clientX - rect.left - 40, e.clientY - rect.top - 40);
  });

  updateBoardTargetOptions();
}

function placePieceOnBoard(objIdx, x, y, rotation = 0) {
  const id    = boardIdCount++;
  const board = document.getElementById('setup-board');
  if (!board) return;

  // Remove empty hint
  const hint = board.querySelector('.board-empty-hint');
  if (hint) hint.remove();

  // Clamp to board
  const bw = board.offsetWidth - 85, bh = board.offsetHeight - 85;
  x = Math.max(4, Math.min(bw, x));
  y = Math.max(22, Math.min(bh, y));

  const piece = document.createElement('div');
  piece.className   = 'board-piece';
  piece.dataset.id  = id;
  piece.dataset.rotation = rotation;
  piece.style.left  = x + 'px';
  piece.style.top   = y + 'px';
  piece.style.transform = `rotate(${rotation}deg)`;
  piece.innerHTML   = `
    <div class="piece-rotate-handle" title="Drag to rotate">↻</div>
    <div class="piece-body">
      <span class="piece-emoji">${PORTL_OBJECTS[objIdx].emoji}</span>
      <span class="piece-label-sm">${PORTL_OBJECTS[objIdx].label}</span>
    </div>
    <button class="piece-remove" title="Remove">×</button>
  `;

  piece.querySelector('.piece-remove').addEventListener('click', e => {
    e.stopPropagation();
    const idx = boardPieces.findIndex(p => p.id === id);
    if (idx !== -1) { boardPieces[idx].el.remove(); boardPieces.splice(idx,1); }
    updateBoardTargetOptions();
    if (!boardPieces.length) board.innerHTML = '<div class="board-empty-hint">Drag objects here to set up the board</div>';
  });

  makePieceDraggable(piece);
  makePieceRotatable(piece);

  board.appendChild(piece);
  boardPieces.push({ id, objIdx, x, y, rotation, el: piece });
  updateBoardTargetOptions();
}

function makePieceDraggable(piece) {
  let active = false, startX, startY, startL, startT;

  piece.addEventListener('pointerdown', e => {
    if (e.target.classList.contains('piece-rotate-handle') ||
        e.target.classList.contains('piece-remove')) return;
    e.preventDefault(); e.stopPropagation();
    active = true;
    piece.setPointerCapture(e.pointerId);
    startX = e.clientX; startY = e.clientY;
    startL = parseFloat(piece.style.left)||0;
    startT = parseFloat(piece.style.top)||0;
    piece.classList.add('piece-dragging');
    piece.style.zIndex = 50;
  });

  piece.addEventListener('pointermove', e => {
    if (!active || !piece.hasPointerCapture(e.pointerId)) return;
    const nl = startL + (e.clientX - startX);
    const nt = startT + (e.clientY - startY);
    piece.style.left = nl + 'px';
    piece.style.top  = nt + 'px';
    const bp = boardPieces.find(p => p.el === piece);
    if (bp) { bp.x = nl; bp.y = nt; }
  });

  piece.addEventListener('pointerup', e => {
    if (!piece.hasPointerCapture(e.pointerId)) return;
    active = false;
    piece.releasePointerCapture(e.pointerId);
    piece.classList.remove('piece-dragging');
    piece.style.zIndex = '';
  });
}

function makePieceRotatable(piece) {
  const handle = piece.querySelector('.piece-rotate-handle');
  if (!handle) return;
  let active = false, cx, cy, startAngle, startRot;

  handle.addEventListener('pointerdown', e => {
    e.preventDefault(); e.stopPropagation();
    active = true;
    handle.setPointerCapture(e.pointerId);
    const rect = piece.getBoundingClientRect();
    cx = rect.left + rect.width/2;
    cy = rect.top  + rect.height/2;
    startAngle = Math.atan2(e.clientY - cy, e.clientX - cx);
    startRot   = parseFloat(piece.dataset.rotation) || 0;
    piece.style.zIndex = 50;
  });

  handle.addEventListener('pointermove', e => {
    if (!active || !handle.hasPointerCapture(e.pointerId)) return;
    const angle  = Math.atan2(e.clientY - cy, e.clientX - cx);
    const newRot = startRot + (angle - startAngle) * (180 / Math.PI);
    piece.dataset.rotation = newRot;
    piece.style.transform  = `rotate(${newRot}deg)`;
    const bp = boardPieces.find(p => p.el === piece);
    if (bp) bp.rotation = newRot;
  });

  handle.addEventListener('pointerup', e => {
    if (!handle.hasPointerCapture(e.pointerId)) return;
    active = false;
    handle.releasePointerCapture(e.pointerId);
    piece.style.zIndex = '';
  });
}

function updateBoardTargetOptions() {
  const sel = document.getElementById('board-target-select');
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = '<option value="">— Pick the target piece —</option>';
  boardPieces.forEach(bp => {
    const opt = document.createElement('option');
    opt.value = bp.id;
    opt.textContent = `${PORTL_OBJECTS[bp.objIdx].emoji} ${PORTL_OBJECTS[bp.objIdx].label}`;
    sel.appendChild(opt);
  });
  if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
}

function clearBoard() {
  boardPieces.forEach(bp => bp.el.remove());
  boardPieces = [];
  const board = document.getElementById('setup-board');
  if (board) board.innerHTML = '<div class="board-empty-hint">Drag objects here to set up the board</div>';
  updateBoardTargetOptions();
}

// Render locked (session) board into #session-board
function renderSessionBoard() {
  const board = document.getElementById('session-board');
  if (!board) return;
  board.innerHTML = '';

  boardPieces.forEach(bp => {
    const piece = document.createElement('div');
    piece.className   = 'board-piece board-piece-locked';
    piece.dataset.id  = bp.id;
    piece.style.left  = bp.x + 'px';
    piece.style.top   = bp.y + 'px';
    piece.style.transform = `rotate(${bp.rotation}deg)`;
    piece.innerHTML   = `
      <div class="piece-body">
        <span class="piece-emoji">${PORTL_OBJECTS[bp.objIdx].emoji}</span>
        <span class="piece-label-sm">${PORTL_OBJECTS[bp.objIdx].label}</span>
      </div>
    `;
    piece.addEventListener('click', () => selectBoardPiece(bp.id, bp.objIdx));
    board.appendChild(piece);
    bp.sessionEl = piece;
  });
}

// ---------------------------------------------------------------------------
// Session state
// ---------------------------------------------------------------------------
let state = {
  running: false,
  role: 'teacher',
  procedure: '',
  targetBehavior: '',
  targetBoardId: null,     // id of the target boardPiece
  targetObjectIdx: 0,
  scheduleType: 'VR',
  scheduleCounter: 0,
  scheduleNext: 1,
  chainStep: 0,
  sdActive: true,
  sdCorrectStreak: 0,
  shapingStage: 0,
  shapingStageCount: 0,
  intervalSize: 10,
  totalIntervals: 3,
  currentInterval: 1,
  reinforcersThisInterval: 0,
  pendingClick: false,
  selectedBoardId: null,
  sessionLog: [],
  intervalData: [],
  startTime: null,
};

function ts() { return formatTime(Date.now() - state.startTime); }

function logEvent(type, msg) {
  const entry = { time: ts(), type, msg };
  state.sessionLog.push(entry);
  const log = document.getElementById('event-log');
  const div = document.createElement('div');
  div.className = `log-entry log-${type}`;
  div.textContent = `[${entry.time}] ${msg}`;
  log.prepend(div);
}

function updateMeter() {
  const m = document.getElementById('reinf-meter');
  if (!m) return;
  m.innerHTML = '';
  for (let i = 0; i < state.intervalSize; i++) {
    const d = document.createElement('div');
    d.className = 'reinf-dot' + (i < state.reinforcersThisInterval ? ' filled' : '');
    m.appendChild(d);
  }
}

function updateCounters() {
  document.getElementById('reinf-count').textContent      = state.reinforcersThisInterval;
  document.getElementById('reinf-target').textContent     = state.intervalSize;
  document.getElementById('current-interval').textContent = state.currentInterval;
  document.getElementById('total-intervals').textContent  = state.totalIntervals;
  updateMeter();
}

// ---------------------------------------------------------------------------
// Board piece selection (unified teacher + learner entry point)
// ---------------------------------------------------------------------------
function selectBoardPiece(boardId, objIdx) {
  if (!state.running) return;

  // Highlight selected piece
  document.querySelectorAll('#session-board .board-piece').forEach(p => p.classList.remove('piece-selected'));
  const bp = boardPieces.find(p => p.id === boardId);
  if (bp && bp.sessionEl) bp.sessionEl.classList.add('piece-selected');

  if (state.role === 'teacher') {
    state.selectedBoardId = boardId;
    state.pendingClick    = true;
    document.getElementById('click-btn').disabled  = false;
    document.getElementById('block-btn').disabled  = false;
    logEvent('object', `Learner touched: ${PORTL_OBJECTS[objIdx].label}`);
  } else {
    learnerTouchObject(boardId, objIdx);
  }
}

// Teacher: conditioned reinforcer
function deliverClick() {
  if (!state.running || !state.pendingClick) return;
  const btn = document.getElementById('click-btn');
  btn.classList.add('flash');
  setTimeout(() => btn.classList.remove('flash'), 300);
  const bp = boardPieces.find(p => p.id === state.selectedBoardId);
  logEvent('click', `CLICK → ${bp ? PORTL_OBJECTS[bp.objIdx].label : 'behavior'}`);
}

// Teacher: unconditioned reinforcer
function deliverBlock() {
  if (!state.running) return;
  const btn = document.getElementById('block-btn');
  btn.classList.add('pulse');
  setTimeout(() => btn.classList.remove('pulse'), 200);
  state.reinforcersThisInterval++;
  GAME.totalReinforcements++;
  logEvent('block', `Block delivered (${state.reinforcersThisInterval}/${state.intervalSize})`);
  awardXP(5);

  state.pendingClick = false;
  state.selectedBoardId = null;
  document.querySelectorAll('#session-board .board-piece').forEach(p => p.classList.remove('piece-selected'));
  document.getElementById('click-btn').disabled = true;
  document.getElementById('block-btn').disabled = true;

  updateCounters();
  if (state.reinforcersThisInterval >= state.intervalSize) setTimeout(triggerBreak, 300);
}

function recordReset() {
  logEvent('reset', 'Reset — learner returned to base position');
  state.pendingClick = false;
  state.selectedBoardId = null;
  document.querySelectorAll('#session-board .board-piece').forEach(p => p.classList.remove('piece-selected'));
  document.getElementById('click-btn').disabled = true;
  document.getElementById('block-btn').disabled = true;
}

// ---------------------------------------------------------------------------
// Simulated teacher (learner mode)
// ---------------------------------------------------------------------------
function nextVR(mean) { return Math.floor(Math.random() * (2*mean-1)) + 1; }

function simTeacherHit(label) {
  const resp = document.getElementById('teacher-response');
  if (resp) { resp.textContent = '✅ CLICK + Block!'; resp.className = 'teacher-response-area tr-hit'; }
  // Flash the selected piece
  const bp = boardPieces.find(p => p.id === state.selectedBoardId);
  if (bp && bp.sessionEl) {
    bp.sessionEl.classList.add('piece-reinforced');
    setTimeout(() => bp.sessionEl.classList.remove('piece-reinforced'), 500);
  }
  state.reinforcersThisInterval++;
  GAME.totalReinforcements++;
  logEvent('block', `Teacher: CLICK + Block → ${label} (${state.reinforcersThisInterval}/${state.intervalSize})`);
  awardXP(5);
  updateCounters();
  if (state.reinforcersThisInterval >= state.intervalSize) setTimeout(triggerBreak, 300);
}

function simTeacherMiss(label) {
  const resp = document.getElementById('teacher-response');
  if (resp) { resp.textContent = '— No response'; resp.className = 'teacher-response-area tr-miss'; }
  logEvent('object', `Touched: ${label} — no reinforcement`);
}

function simTeacherPrompt(targetLabel) {
  const resp = document.getElementById('teacher-response');
  if (resp) {
    const bp = boardPieces.find(p => p.id === state.targetBoardId);
    const emoji = bp ? PORTL_OBJECTS[bp.objIdx].emoji : '';
    resp.textContent = `💡 Prompt → try the ${emoji} ${targetLabel}`;
    resp.className = 'teacher-response-area tr-prompt';
  }
  logEvent('reset', `Prompt: try the ${targetLabel}`);
}

function learnerTouchObject(boardId, objIdx) {
  if (!state.running) return;
  state.selectedBoardId = boardId;
  const label   = PORTL_OBJECTS[objIdx].label;
  const target  = state.targetObjectIdx;   // target objIdx
  const proc    = state.procedure;

  if (proc === 'shaping') {
    let hit = false;
    if      (state.shapingStage === 0) hit = true;
    else if (state.shapingStage === 1) hit = Math.abs(objIdx - target) <= 1;
    else                               hit = objIdx === target;

    if (hit) {
      state.shapingStageCount++;
      const thresh = Math.ceil(state.intervalSize / 2);
      if (state.shapingStage < 2 && state.shapingStageCount >= thresh) {
        state.shapingStage++;
        state.shapingStageCount = 0;
        const msgs = ['', 'Criteria raised — getting closer to the target!', `Criteria raised — only ${PORTL_OBJECTS[target].label} now`];
        logEvent('system', msgs[state.shapingStage]);
        const resp = document.getElementById('teacher-response');
        if (resp) { resp.textContent = `📈 ${msgs[state.shapingStage]}`; resp.className = 'teacher-response-area tr-prompt'; }
      }
      simTeacherHit(label);
    } else {
      simTeacherMiss(label);
    }

  } else if (proc === 'differential_reinforcement') {
    objIdx === target ? simTeacherHit(label) : simTeacherMiss(label);

  } else if (proc === 'errorless_learning') {
    if (objIdx === target) {
      simTeacherHit(label);
    } else {
      simTeacherPrompt(PORTL_OBJECTS[target].label);
    }

  } else if (proc === 'stimulus_control') {
    const sdEl = document.getElementById('sd-indicator');
    if (state.sdActive) {
      if (objIdx === target) {
        state.sdCorrectStreak++;
        simTeacherHit(label);
        if (state.sdCorrectStreak >= 3) {
          state.sdActive = false; state.sdCorrectStreak = 0;
          if (sdEl) { sdEl.textContent = 'S− active'; sdEl.className = 'sd-indicator sd-minus'; }
          logEvent('system', 'S− in effect');
        }
      } else { simTeacherMiss(label); }
    } else {
      state.sdCorrectStreak++;
      simTeacherMiss(label);
      if (state.sdCorrectStreak >= 3) {
        state.sdActive = true; state.sdCorrectStreak = 0;
        if (sdEl) { sdEl.textContent = 'S+ active'; sdEl.className = 'sd-indicator sd-plus'; }
        logEvent('system', 'S+ in effect — touch the target!');
      }
    }

  } else if (proc === 'behavior_chain') {
    const targets = boardPieces.map(bp => bp.objIdx);  // order on board = chain order
    const required = targets[state.chainStep] !== undefined ? targets[state.chainStep] : target;
    const chainEl  = document.getElementById('chain-progress');
    if (objIdx === required) {
      if (state.chainStep < targets.length - 1) {
        const resp = document.getElementById('teacher-response');
        if (resp) { resp.textContent = `✅ Step ${state.chainStep+1} — continue!`; resp.className = 'teacher-response-area tr-hit'; }
        logEvent('click', `Chain step ${state.chainStep+1}: ${label}`);
        state.chainStep++;
        if (chainEl) {
          const nextObj = PORTL_OBJECTS[targets[state.chainStep]];
          chainEl.textContent = `Step ${state.chainStep+1}/${targets.length} — touch ${nextObj ? nextObj.emoji+' '+nextObj.label : '?'}`;
        }
      } else {
        state.chainStep = 0;
        if (chainEl) {
          const first = PORTL_OBJECTS[targets[0]];
          chainEl.textContent = `Chain complete! Step 1/${targets.length} — ${first ? first.emoji+' '+first.label : '?'}`;
        }
        simTeacherHit(label);
      }
    } else {
      state.chainStep = 0;
      const first = PORTL_OBJECTS[targets[0]];
      if (chainEl) chainEl.textContent = `Chain reset — step 1/${targets.length}: ${first ? first.emoji+' '+first.label : '?'}`;
      const resp = document.getElementById('teacher-response');
      if (resp) { resp.textContent = '↺ Wrong step — chain reset'; resp.className = 'teacher-response-area tr-miss'; }
      logEvent('reset', `Wrong step — chain reset`);
    }

  } else if (proc === 'schedule') {
    if (objIdx === target) {
      state.scheduleCounter++;
      const s  = state.scheduleType;
      let hit  = false;
      if      (s === 'CRF') { hit = true; }
      else if (s === 'FR' ) { if (state.scheduleCounter >= state.scheduleNext) { hit = true; state.scheduleCounter = 0; } }
      else if (s === 'FR5') { if (state.scheduleCounter >= state.scheduleNext) { hit = true; state.scheduleCounter = 0; } }
      else if (s === 'VR' ) { if (state.scheduleCounter >= state.scheduleNext) { hit = true; state.scheduleCounter = 0; state.scheduleNext = nextVR(3); } }
      else if (s === 'VR5') { if (state.scheduleCounter >= state.scheduleNext) { hit = true; state.scheduleCounter = 0; state.scheduleNext = nextVR(5); } }
      hit ? simTeacherHit(label) : simTeacherMiss(label);
    } else {
      simTeacherMiss(label);
    }
  } else {
    objIdx === target ? simTeacherHit(label) : simTeacherMiss(label);
  }
}

// ---------------------------------------------------------------------------
// Interval / session flow
// ---------------------------------------------------------------------------
function triggerBreak() {
  state.running = false;
  awardXP(25);
  logEvent('system', `Interval ${state.currentInterval} complete — record data.`);
  document.getElementById('break-panel').classList.remove('hidden');
  document.getElementById('break-behavior-count').value = state.reinforcersThisInterval;
  document.getElementById('break-errors').value = 0;
  document.getElementById('break-plan').value   = '';
}

function continueSession() {
  state.intervalData.push({
    interval:      state.currentInterval,
    behaviorCount: parseInt(document.getElementById('break-behavior-count').value)||0,
    errors:        parseInt(document.getElementById('break-errors').value)||0,
    plan:          document.getElementById('break-plan').value,
  });
  if (state.currentInterval >= state.totalIntervals) {
    document.getElementById('break-panel').classList.add('hidden');
    showSummary(); return;
  }
  state.currentInterval++;
  state.reinforcersThisInterval = 0;
  state.running = true;
  document.getElementById('break-panel').classList.add('hidden');
  updateCounters();
  logEvent('system', `Interval ${state.currentInterval} started`);
}

function endSession() {
  state.intervalData.push({
    interval:      state.currentInterval,
    behaviorCount: parseInt(document.getElementById('break-behavior-count').value)||0,
    errors:        parseInt(document.getElementById('break-errors').value)||0,
    plan:          document.getElementById('break-plan').value,
  });
  document.getElementById('break-panel').classList.add('hidden');
  showSummary();
}

function showSummary() {
  state.running = false;
  const totalErrors = state.intervalData.reduce((s,d)=>s+d.errors,0);
  const bonus       = totalErrors === 0 ? 25 : totalErrors <= 3 ? 15 : 0;
  awardXP(75 + bonus);
  GAME.sessionsCompleted++;
  saveGame();
  checkAchievements();

  const totalBehavior = state.intervalData.reduce((s,d)=>s+d.behaviorCount,0);
  const targetBp      = boardPieces.find(p => p.id === state.targetBoardId);
  const targetName    = targetBp ? `${PORTL_OBJECTS[targetBp.objIdx].emoji} ${PORTL_OBJECTS[targetBp.objIdx].label}` : '—';

  document.getElementById('summary-panel').classList.remove('hidden');

  let html = `
    <div class="reveal-banner">
      <h3>🎉 Session Revealed</h3>
      <div class="form-grid">
        <div class="info-item"><strong>Role</strong><p>${state.role === 'learner' ? 'Learner (1.5× XP)' : 'Teacher'}</p></div>
        <div class="info-item"><strong>Procedure</strong><p>${state.procedure.replace(/_/g,' ')}</p></div>
        <div class="info-item"><strong>Target Object</strong><p>${targetName}</p></div>
        <div class="info-item"><strong>Intervals</strong><p>${state.intervalData.length}</p></div>
        <div class="info-item"><strong>Total Behavior</strong><p>${totalBehavior}</p></div>
        <div class="info-item"><strong>Accuracy Bonus</strong><p>+${bonus} XP${totalErrors===0?' 🎯':''}</p></div>
      </div>
    </div>
    <table class="data-table" style="margin-top:1rem">
      <thead><tr><th>Interval</th><th>Behavior</th><th>Errors</th><th>Plan</th></tr></thead>
      <tbody>
  `;
  state.intervalData.forEach(d => {
    html += `<tr><td>${d.interval}</td><td>${d.behaviorCount}</td><td>${d.errors}</td><td>${d.plan||'—'}</td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('summary-content').innerHTML = html;
}

function saveSession() {
  fetch('/api/simulation/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ procedure: state.procedure, target_behavior: state.targetBehavior, log: state.sessionLog })
  }).then(r => r.json()).then(() => alert('Session saved!'));
}

// ---------------------------------------------------------------------------
// Flow: Setup → Board → Session
// ---------------------------------------------------------------------------
function goToBoard() {
  document.getElementById('setup-panel').classList.add('hidden');
  document.getElementById('board-panel').classList.remove('hidden');
  initBoardBuilder();
}

function backToSetup() {
  document.getElementById('board-panel').classList.add('hidden');
  document.getElementById('setup-panel').classList.remove('hidden');
}

function startSession() {
  if (!boardPieces.length) { alert('Place at least one object on the board first.'); return; }

  state.role           = document.querySelector('input[name="role"]:checked').value;
  state.procedure      = document.getElementById('procedure').value;
  state.targetBehavior = document.getElementById('target-behavior').value;
  state.scheduleType   = document.getElementById('schedule-type').value;
  state.intervalSize   = parseInt(document.getElementById('interval-size').value)||10;
  state.totalIntervals = parseInt(document.getElementById('num-intervals').value)||3;

  // Resolve target from board-target-select (by board piece id)
  const sel = document.getElementById('board-target-select');
  const selId = sel ? parseInt(sel.value) : NaN;
  const targetBp = !isNaN(selId) ? boardPieces.find(p => p.id === selId) : boardPieces[0];
  state.targetBoardId   = targetBp ? targetBp.id  : (boardPieces[0] ? boardPieces[0].id : null);
  state.targetObjectIdx = targetBp ? targetBp.objIdx : (boardPieces[0] ? boardPieces[0].objIdx : 0);

  // Reset counters
  Object.assign(state, {
    currentInterval: 1, reinforcersThisInterval: 0, pendingClick: false, selectedBoardId: null,
    sessionLog: [], intervalData: [], startTime: Date.now(), running: true,
    chainStep: 0, sdActive: true, sdCorrectStreak: 0,
    shapingStage: 0, shapingStageCount: 0, scheduleCounter: 0,
    scheduleNext: (['FR5','VR5'].includes(state.scheduleType)) ? 5 : 3,
  });
  if (state.scheduleType.startsWith('VR')) state.scheduleNext = nextVR(state.scheduleType==='VR5'?5:3);

  // Show panels
  document.getElementById('board-panel').classList.add('hidden');
  document.getElementById('session-panel').classList.remove('hidden');
  document.getElementById('break-panel').classList.add('hidden');
  document.getElementById('summary-panel').classList.add('hidden');

  // Badges — hide procedure/goal for learner
  if (state.role === 'learner') {
    document.getElementById('procedure-badge').textContent = '???';
    document.getElementById('behavior-badge').textContent  = '???  (discover through play)';
  } else {
    document.getElementById('procedure-badge').textContent = state.procedure.replace(/_/g,' ');
    document.getElementById('behavior-badge').textContent  = state.targetBehavior || 'No target set';
  }

  // Show/hide teacher vs learner controls
  const teacherControls = document.querySelector('.teacher-controls');
  const learnerFeedback = document.getElementById('learner-feedback');
  teacherControls.classList.toggle('hidden', state.role === 'learner');
  learnerFeedback.classList.toggle('hidden',  state.role === 'teacher');

  // Learner-specific hints
  if (state.role === 'learner') {
    const resp = document.getElementById('teacher-response');
    if (resp) { resp.textContent = 'Touch objects on the board to begin…'; resp.className = 'teacher-response-area'; }
    const sdEl = document.getElementById('sd-indicator');
    const chainEl = document.getElementById('chain-progress');
    sdEl.classList.toggle('hidden', state.procedure !== 'stimulus_control');
    chainEl.classList.toggle('hidden', state.procedure !== 'behavior_chain');
    if (sdEl && state.procedure === 'stimulus_control') { sdEl.textContent = 'S+ active'; sdEl.className = 'sd-indicator sd-plus'; }
    if (chainEl && state.procedure === 'behavior_chain') {
      const first = boardPieces[0];
      chainEl.textContent = first ? `Step 1/${boardPieces.length} — ${PORTL_OBJECTS[first.objIdx].emoji} ${PORTL_OBJECTS[first.objIdx].label}` : 'Chain ready';
    }
  }

  // Render locked session board
  renderSessionBoard();

  // Reinforcer meter
  const prog = document.querySelector('.session-progress');
  if (prog && !document.getElementById('reinf-meter')) {
    const m = document.createElement('div');
    m.id = 'reinf-meter'; m.className = 'reinf-meter';
    prog.appendChild(m);
  }

  updateCounters();
  const roleLabel = state.role === 'learner' ? 'LEARNER (1.5× XP)' : 'TEACHER';
  logEvent('system', `[${roleLabel}] ${state.procedure.replace(/_/g,' ')} — ${state.totalIntervals} × ${state.intervalSize} reinforcers`);
}

// ---------------------------------------------------------------------------
// Init + keyboard shortcuts
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  buildExerciseOptions();
  updateXPBar();
});

document.addEventListener('keydown', e => {
  if (!state.running) return;
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (state.role === 'teacher') {
    if (e.code === 'Space') { e.preventDefault(); deliverClick(); }
    if (e.key === 'b' || e.key === 'B') deliverBlock();
    if (e.key === 'r' || e.key === 'R') recordReset();
  }
});
