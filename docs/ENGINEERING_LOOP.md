# RushPoppy engineering loop (hackathon)

Goal: continuous **PR → review → Vercel → demo video → bug QA → Linear backlog** until demos (~17:15 PT).

## Blockers (must clear once)
1. **GitHub Poppy** — push on `poppyia2026-code/FlowerLabsHackathon` (PAT `POPPY_GITHUB_PAT` or Cursor access card).
2. **Vercel Poppy** — token for `poppy.ia2026` / team `poppyia2026-5777`.

## Cycle
| Step | Who | Output |
|------|-----|--------|
| 1 Build | Cloud agent grok-4.7 xhigh + P Stack | Small PR |
| 2 Review | Second Grok pass | PR comments; fix or merge |
| 3 Deploy | `vercel --prod` from landing / web | Prod URL |
| 4 Demo video | Short walkthrough of deploy | Drive folder Builder en la Bahía / hackathon demos |
| 5 Video QA | watchVideo / visual pass | Bug list |
| 6 Backlog | Linear `user-Linear--poppyai` | Issues in locked format |

## Luigi lane first
F0 Grid tools → F5 Orchestrator → F6 claim contract. Landing deploy can run in parallel once Vercel token exists.

## Issue format (locked)
Title: `[P#] Area — verb + outcome (Fx)`
Body: Contexto → Owner → Qué hacer → Done when → Paths/links → Fuera de scope
