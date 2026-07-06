*Charles — setup for your part (frontend)*

Repo: https://github.com/asiertxo09/amazon-project
Your zone: `frontend/` (only has a `fixtures/` folder so far — rest is yours)

*1. Clone the repo*
```
git clone https://github.com/asiertxo09/amazon-project.git
cd amazon-project
```

*2. Check you're on the right branch*
```
git branch -a
git checkout master
git pull
```

*3. Install Node (if you don't have it)*
```
node -v
```
If that errors or shows < v18, install via nvm:
```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install --lts
nvm use --lts
```

*4. Init your frontend project*
No package.json exists yet in `frontend/`, so this is a fresh start:
```
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm run dev
```
(If you're using Lovable directly instead of local Vite, just connect Lovable to the `frontend/` path in the repo and skip this step — ask me first so we don't end up with two conflicting setups.)

*5. Install Claude Code (so you can use the same AI setup I'm using)*
```
npm install -g @anthropic-ai/claude-code
claude
```
Then inside Claude Code, once in the repo folder, run:
```
/init
```
This scans the repo and sets up project context for you.

*6. Git basics you'll need*
```
git status
git add .
git commit -m "your message"
git push
```
Always `git pull` before you start working each session, so you don't diverge from what I push.

---

*Problem solving*

- `git clone` fails / permission denied → you need to be added as a collaborator on the GitHub repo, or use SSH instead of HTTPS. Ping me.
- `npm install` fails with weird peer-dependency errors → try `npm install --legacy-peer-deps`.
- `npm run dev` says port already in use → kill whatever's on it: `lsof -i :5173` then `kill -9 <PID>`, or just let Vite pick another port (it asks automatically).
- `node -v` not found at all → you don't have Node installed, do step 3 above.
- Merge conflicts after `git pull` → don't panic, don't `git reset --hard`. Just message me the file names and we'll sort it together.
- Nothing renders / blank page → open browser dev tools console (F12), send me the error, way faster to debug than guessing.
- Claude Code asks about "sandbox"/"permissions" on first run → just accept defaults, we can tune later.
- Anything ML/backend-shaped (endpoints, contract JSON fields, pricing logic) → not your problem, that's on my side, just flag it to me and keep building your UI against the mock/fixture data for now.

Message me the second you're stuck instead of sinking 30 min into it — we're on a hard deadline.
