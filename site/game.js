(() => {
  "use strict";

  const BEST_SCORE_KEY = "hlg_best_score";
  const SOUND_KEY = "hlg_sound_on";

  const el = (id) => document.getElementById(id);
  const panelLeft = el("panel-left");
  const panelRight = el("panel-right");
  const leftImg = el("left-img");
  const rightImg = el("right-img");
  const leftName = el("left-name");
  const rightName = el("right-name");
  const leftScore = el("left-score");
  const rightScore = el("right-score");
  const guessButtons = el("guess-buttons");
  const rightCaptionWord = el("right-caption-word");
  const leftAttr = el("left-attr");
  const rightAttr = el("right-attr");
  const btnHigher = el("btn-higher");
  const btnLower = el("btn-lower");
  const vsCircle = el("vs-circle");
  const toastEl = el("toast");
  const chipRow = el("category-chips");
  const btnSound = el("btn-sound");
  const btnShare = el("btn-share");
  const btnShare2 = el("btn-share-2");
  const btnRestart = el("btn-restart");
  const overlay = el("overlay");
  const overlayTitle = el("overlay-title");
  const overlayBody = el("overlay-body");
  const finalScoreEl = el("final-score");
  const finalBestEl = el("final-best");
  const scoreValueEl = el("score-value");
  const bestValueEl = el("best-value");

  const FALLBACK_IMG =
    "data:image/svg+xml;utf8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600">' +
      '<rect width="600" height="600" fill="#131a2e"/>' +
      '<circle cx="300" cy="260" r="90" fill="#1a2340" stroke="#2a3552" stroke-width="2"/>' +
      '<circle cx="300" cy="260" r="40" fill="#0a0e1b"/>' +
      "</svg>"
    );

  let allWords = [];
  let pool = [];
  let categoryFilter = "all";
  let score = 0;
  let best = Number(localStorage.getItem(BEST_SCORE_KEY) || 0);
  let soundOn = localStorage.getItem(SOUND_KEY) !== "off";
  let leftWord = null;
  let rightWord = null;
  let busy = false; // guard against double-clicks mid-transition

  bestValueEl.textContent = best;
  updateSoundButton();

  fetch("../data/words.json")
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then((data) => {
      allWords = data;
      buildCategoryChips();
      resetPool();
      startRound(true);
    })
    .catch((err) => {
      overlayTitle.textContent = "No signal";
      overlayBody.textContent =
        "Couldn't load the word data (" + err.message + "). Run the data pipeline, then reload.";
      el("final-score").parentElement.parentElement.style.display = "none";
      overlay.classList.add("show");
    });

  function buildCategoryChips() {
    const categories = Array.from(new Set(allWords.map((w) => w.category))).sort();
    const labels = { astronomy: "Astronomy", brainrot: "Brainrot" };
    const makeChip = (value, label) => {
      const b = document.createElement("button");
      b.className = "chip" + (value === categoryFilter ? " active" : "");
      b.textContent = label;
      b.addEventListener("click", () => {
        categoryFilter = value;
        chipRow.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        b.classList.add("active");
        resetPool();
        startRound(true);
      });
      return b;
    };
    chipRow.appendChild(makeChip("all", "All"));
    categories.forEach((c) => chipRow.appendChild(makeChip(c, labels[c] || c)));
  }

  function currentPoolSource() {
    return categoryFilter === "all"
      ? allWords
      : allWords.filter((w) => w.category === categoryFilter);
  }

  function resetPool() {
    pool = shuffle(currentPoolSource().slice());
  }

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function pickNext(exclude) {
    if (pool.length === 0) {
      // Ran through every word this filter offers — reshuffle and keep going,
      // matching the "infinite questions" behavior of the reference game.
      const source = currentPoolSource().filter((w) => w.word !== (exclude && exclude.word));
      pool = shuffle(source.slice());
    }
    let candidate = pool.pop();
    if (exclude && candidate && candidate.word === exclude.word && pool.length > 0) {
      pool.unshift(candidate);
      candidate = pool.pop();
    }
    return candidate;
  }

  function setPanelImage(imgEl, wordObj) {
    imgEl.src = wordObj.imageUrl || FALLBACK_IMG;
    imgEl.onerror = () => {
      imgEl.onerror = null;
      imgEl.src = FALLBACK_IMG;
    };
    imgEl.alt = wordObj.word;
  }

  function setAttribution(attrEl, wordObj) {
    attrEl.textContent = wordObj.category === "astronomy" ? "Image: Wikimedia Commons" : "";
  }

  function startRound(isFirst) {
    leftWord = isFirst ? pickNext(null) : leftWord;
    rightWord = pickNext(leftWord);

    setPanelImage(leftImg, leftWord);
    leftName.textContent = leftWord.word;
    leftScore.textContent = formatScore(leftWord.score);
    leftScore.className = "big-number";
    setAttribution(leftAttr, leftWord);

    setPanelImage(rightImg, rightWord);
    rightName.textContent = rightWord.word;
    rightCaptionWord.textContent = leftWord.word;
    setAttribution(rightAttr, rightWord);
    rightScore.textContent = "—";
    rightScore.className = "big-number big-number--right";
    guessButtons.classList.remove("answered");

    resetVsCircle();
    btnHigher.disabled = false;
    btnLower.disabled = false;
    busy = false;
  }

  // Our real number is a 0-100ish Google Trends relative-popularity index,
  // not an actual search-volume count (Trends doesn't expose real volume).
  // Scaled up here into a bigger, comma-formatted "dummy" number purely so
  // it reads like a search-volume figure, at the user's request — the
  // underlying comparison logic still uses the true, unscaled score.
  const DISPLAY_SCALE = 1000;
  function formatScore(n) {
    return Math.round(n * DISPLAY_SCALE).toLocaleString("en-US");
  }

  function resetVsCircle() {
    vsCircle.classList.remove("good", "bad", "pop");
  }

  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 1400);
  }

  function handleGuess(guessHigher) {
    if (busy || !leftWord || !rightWord) return;
    busy = true;
    btnHigher.disabled = true;
    btnLower.disabled = true;

    const tie = rightWord.score === leftWord.score;
    const actuallyHigher = rightWord.score > leftWord.score;
    const correct = tie || guessHigher === actuallyHigher;

    vsCircle.classList.add(correct ? "good" : "bad", "pop");
    setTimeout(() => vsCircle.classList.remove("pop"), 260);

    guessButtons.classList.add("answered");
    rightScore.textContent = formatScore(rightWord.score);
    rightScore.className = "big-number big-number--right reveal " + (correct ? "correct" : "incorrect");

    if (tie) showToast("Equal signal — streak continues");

    playTone(correct);

    if (correct) {
      score += 1;
      scoreValueEl.textContent = score;
      if (score > best) {
        best = score;
        bestValueEl.textContent = best;
        localStorage.setItem(BEST_SCORE_KEY, String(best));
      }
      setTimeout(() => advanceChain(), 1900);
    } else {
      setTimeout(() => endGame(), 1900);
    }
  }

  function advanceChain() {
    panelLeft.classList.add("slide-out");
    panelRight.classList.add("slide-out");
    setTimeout(() => {
      leftWord = rightWord;
      panelLeft.classList.remove("slide-out");
      panelRight.classList.remove("slide-out");
      startRound(false);
      panelRight.classList.add("slide-in");
      setTimeout(() => panelRight.classList.remove("slide-in"), 550);
    }, 380);
  }

  function endGame() {
    finalScoreEl.textContent = score;
    finalBestEl.textContent = best;
    overlayTitle.textContent = score === 0 ? "First contact lost" : "Streak broken";
    overlayBody.textContent =
      score === 0
        ? "The very first call went the wrong way. Every run starts at zero — try again."
        : "You called it right " + score + " time" + (score === 1 ? "" : "s") + " in a row before the signal flipped.";
    overlay.classList.add("show");
  }

  function restartGame() {
    score = 0;
    scoreValueEl.textContent = 0;
    overlay.classList.remove("show");
    resetPool();
    startRound(true);
  }

  btnHigher.addEventListener("click", () => handleGuess(true));
  btnLower.addEventListener("click", () => handleGuess(false));
  btnRestart.addEventListener("click", restartGame);

  document.addEventListener("keydown", (e) => {
    if (overlay.classList.contains("show")) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); restartGame(); }
      return;
    }
    if (e.key === "ArrowUp" || e.key.toLowerCase() === "h") handleGuess(true);
    if (e.key === "ArrowDown" || e.key.toLowerCase() === "l") handleGuess(false);
  });

  // ---------- share ----------
  function shareScore() {
    const text =
      "I scored " + score + " on Higher or Lower: Space Edition 🚀🌌 " +
      "Can you beat me?";
    if (navigator.share) {
      navigator.share({ text, url: location.href }).catch(() => {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text + " " + location.href).then(
        () => showToast("Score copied to clipboard"),
        () => showToast("Couldn't copy — try manually")
      );
    } else {
      showToast(text);
    }
  }
  btnShare.addEventListener("click", shareScore);
  btnShare2.addEventListener("click", shareScore);

  // ---------- sound (synthesized, no external assets) ----------
  let audioCtx = null;
  function playTone(correct) {
    if (!soundOn) return;
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const now = audioCtx.currentTime;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type = "sine";
      if (correct) {
        osc.frequency.setValueAtTime(520, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.18);
      } else {
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.exponentialRampToValueAtTime(120, now + 0.28);
      }
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.18, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + (correct ? 0.24 : 0.34));
      osc.start(now);
      osc.stop(now + 0.4);
    } catch (e) {
      /* audio unavailable — ignore */
    }
  }

  function updateSoundButton() {
    btnSound.setAttribute("aria-pressed", String(soundOn));
    btnSound.style.opacity = soundOn ? "1" : "0.55";
  }
  btnSound.addEventListener("click", () => {
    soundOn = !soundOn;
    localStorage.setItem(SOUND_KEY, soundOn ? "on" : "off");
    updateSoundButton();
  });
})();
