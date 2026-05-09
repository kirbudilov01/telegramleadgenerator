# 🚀 Быстрый старт: Threads + X агенты на Linux

## 1. Клонируй репозиторий

```bash
git clone https://github.com/kirbudilov01/telegramleadgenerator.git
cd telegramleadgenerator
```

## 2. Сохрани GitHub токен

```bash
echo 'export GITHUB_TOKEN="твой_токен"' >> ~/.bashrc
source ~/.bashrc
# или для zsh:
echo 'export GITHUB_TOKEN="твой_токен"' >> ~/.zshrc
source ~/.zshrc
```

Если хочешь, чтобы настройки подхватывались автоматически, можешь один раз создать локальный файл окружения и подключить его в shell.

```bash
cat > ~/.env_threads_x <<'EOF'
export GITHUB_TOKEN="твой_токен"
export DUAL_LAYOUT=even-horizontal
export DUAL_TMUX_WIDTH=240
export DUAL_TMUX_HEIGHT=60
export THREADS_WIN_X=0
export THREADS_WIN_Y=0
export THREADS_WIN_WIDTH=960
export THREADS_WIN_HEIGHT=1080
export X_BROWSER_X=970
export X_BROWSER_Y=0
export X_BROWSER_WIDTH=950
export X_BROWSER_HEIGHT=1080
EOF
echo 'source ~/.env_threads_x' >> ~/.zshrc
source ~/.zshrc
```

## 3. Инициализация окружения

```bash
./go.sh init
```
- Установит Python venv, Playwright, браузеры, npm-зависимости для X-агента.

## 4. Авторизация в Threads и X

```bash
./go.sh login
```
- Откроются окна Chrome для ручного входа (используется твой профиль, не headless).

## 5. Запуск агентов

```bash
./go.sh start
```
- Откроется tmux: слева Threads, справа X.
- Оба браузера будут видны на экране, всё красиво и удобно.

## 6. (Опционально) Настрой размеры окон

В .env или перед запуском:

```bash
export THREADS_WIN_WIDTH=960
export X_BROWSER_WIDTH=960
export THREADS_WIN_HEIGHT=1080
export X_BROWSER_HEIGHT=1080
```

### Полный набор настроек

Если хочешь полный контроль, используй эти параметры из `.env.example`:

- `GITHUB_TOKEN` — токен GitHub Models для Threads
- `OPENROUTER_API_KEY` — fallback для X или запасной LLM
- `DUAL_LAYOUT` — `even-horizontal`, `even-vertical`, `main-horizontal`, `main-vertical`, `tiled`
- `DUAL_TMUX_WIDTH` / `DUAL_TMUX_HEIGHT` — размер tmux-сессии
- `THREADS_WIN_X` / `THREADS_WIN_Y` / `THREADS_WIN_WIDTH` / `THREADS_WIN_HEIGHT` — окно Threads
- `X_BROWSER_X` / `X_BROWSER_Y` / `X_BROWSER_WIDTH` / `X_BROWSER_HEIGHT` — окно X
- `OLLAMA_HOST` / `OLLAMA_MODEL` — если нужен локальный LLM fallback
- `DEBUG` / `VERBOSE` — расширенные логи

### Что влияет на стиль сообщений

- `threads_autopilot/config.json` — ключевые слова, лимиты, пороги уверенности, persona
- `threads_autopilot/persona.md` — твой стиль, примеры, тональность, словарь
- `llm_provider` — сейчас `github_models`, можно переключить на `openrouter` для GPT-4o или Claude Opus, если есть ключ
- `auto_send_min_score` / `draft_min_score` — насколько смело агент отправляет ответ сам

Если хочешь более human-стиль, сначала усиливай `persona.md`, а уже потом меняй модель.

## 7. Проверка

- Логи: autopilot.log (Threads), ../X-ACTIONS-AGENT/logs/agent.log (X)
- Если что-то не так — просто перезапусти ./go.sh start

---

## 🤖 Какое качество сообщений и какая модель?

- Используется модель **Claude 3.5 Sonnet** (github_models через Azure endpoint).
- Качество: топовое, максимально "человеческое" (лучше GPT-4 для длинных и сложных ответов).
- Контекст учитывается полностью:
  - В каждый промпт подставляется твоя persona (36 KB about3.md)
  - Вся история диалога и поста анализируется
  - Модель видит, что уже было написано, и не повторяет себя
- Если Claude недоступен — fallback на OpenRouter или Ollama (локально), но при наличии токена всегда будет Claude.

---

## ⚠️ Ограничения и совершенство агентов

- **Human-like**: Claude 3.5 Sonnet — одна из самых "человеческих" моделей на рынке (лучше GPT-4 по стилю и контексту), но всё равно не 100% человек.
- **Ограничения**:
  - Иногда может "перестраховываться" и писать чуть более формально, чем живой человек.
  - Не всегда идеально угадывает тональность (особенно если в persona мало примеров нужного стиля).
  - Не умеет читать приватные сообщения, только публичные посты.
  - Не может лайкать/отвечать быстрее лимитов (это специально для антибана).
- **Контекст**: модель видит всю историю поста, persona, предыдущие ответы — но не читает чужие DM.
- **Можем ли взять модель покруче?**
  - Сейчас Claude 3.5 Sonnet — топ-2 в мире (по human-like), выше только Claude 3.5 Opus (но она платная и не всегда доступна через GitHub Models).
  - Можно подключить GPT-4o или Claude Opus через OpenRouter, если есть платный ключ (см. config.json, поменять model и endpoint).
  - Для максимального human-стиля: добавь больше примеров в persona.md, чтобы модель копировала твой стиль.

### Моя оценка качества
- Для LinkedIn/Threads/X — это один из лучших вариантов на рынке.
- Если нужен ещё более "живой" стиль — экспериментируй с persona.md и настройками scoring (auto_send_min_score, draft_min_score).
- Если появится доступ к Claude Opus или GPT-4o — можно быстро переключить модель (скажу как).

---

**Всё готово для запуска!**
Если хочешь — можешь сразу посмотреть autopilot.log после первого запуска: там будут все ответы, которые пишет агент.

## Самая короткая команда для Linux

Если токен уже задан и `./go.sh init` уже был выполнен, запуск сводится к одной команде:

```bash
cd telegramleadgenerator && ./go.sh start
```

Если хочешь подхватить свой локальный файл окружения перед стартом:

```bash
cd telegramleadgenerator && source ~/.env_threads_x && ./go.sh start
```

Если поднимаешь всё с нуля на чистом Linux, полный порядок такой:

```bash
cd telegramleadgenerator && ./go.sh doctor && ./go.sh init && ./go.sh login && ./go.sh start
```

`login` открывает браузер для ручной авторизации, поэтому его один раз надо пройти глазами. После этого дальнейший запуск — это уже только `./go.sh start`.
