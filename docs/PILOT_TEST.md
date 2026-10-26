# L.I.S.A. pilot test (15–20 minutes, one real K-pop fan)

Goal: measure, with a real fan, how long the same tasks take **the usual way** (Weverse, X, Google/Naver,
ticketing sites) versus **with L.I.S.A.**. Results feed section 7 (Impact) of the report automatically.

## Before you start
- Run the app (`python app.py`) and open http://127.0.0.1:8050 in a fresh browser tab.
- Have a phone stopwatch ready. Do **not** help the participant during a task.
- Ask permission to quote them (first name or initials only).

## Round 1 — the usual way (any apps or sites, no L.I.S.A.)
Time each task from "go" until the participant says "done". Count how many different sites or apps they opened.

| Task | Read aloud |
|---|---|
| A | "BTS plays Singapore in December. Find the dates, when tickets went on sale, the price range, and the official ticket site." |
| B | "BTS has a video-call fansign at Ktown4u. How many albums would you need for a good chance, and what would it cost?" |
| C | "You land at Changi Airport. How do you get to the stadium, and where can you leave a suitcase?" |
| D | "TXT's next album comes out soon. When is it, and what should a one-hour streaming playlist look like?" |

## Round 2 — with L.I.S.A.
Same tasks; the participant may click or type. Time them the same way.

## After both rounds (ask and write down)
1. Ease of use with L.I.S.A., 1 (hard) – 5 (very easy)
2. Confidence in the answer: usual way 1–5, L.I.S.A. 1–5
3. Would you use L.I.S.A. before your next concert or fansign? (yes / maybe / no)
4. Did anything confuse you, or was anything wrong?
5. One sentence quote about the experience.

## Where to record
- `docs/pilot_results.csv` — one row per task and method:
  `participant,task,method,seconds,sites_or_apps_opened,confidence_1to5,correct_yes_no,notes`
  with `method` = `manual` or `lisa`, `task` = `A`–`D`. Example: `P1,A,manual,540,5,3,yes,"had to check three vendor pages"`.
- `docs/pilot_participants.json` — who they are (initials, fandom, how they do it today, album spend, quote).
- Then rebuild: `python docs/build_report.py` and `python docs/build_slides.py`.

Tip: with a second participant, swap the order (L.I.S.A. first) so learning the task in round 1 does not make round 2 look faster.
