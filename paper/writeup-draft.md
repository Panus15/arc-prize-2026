<!--
ร่างเนื้อ Kaggle Writeup — ภาษาอังกฤษเพราะกรรมการอ่านอังกฤษ
ปรับปรุง 21 ก.ย. 2026 · repo commit `e63c0f3`

สถานะ: §3 §4 §5 เขียนครบแล้ว (~950 คำ) — ไม่ต้องรอผลเกมสด
        §1 §2 §6 §7 เป็นโครง ต้องเติมหลังได้ผลเกมสด (~550 คำ)
ทุกตัวเลขในร่างนี้มาจากไฟล์ใน docs/ ห้ามเติมตัวเลขที่ยังไม่ได้วัด
-->

# What a program-only agent can establish about an unknown environment

## 1. The problem  *(~120 words — DRAFT, needs the live run to finish)*

> เติมหลังได้ผลเกมสด: ย่อหน้าเปิดควรจบด้วยสิ่งที่เราวัดได้จริงกับเกมจริง

An ARC-AGI-3 agent starts without knowing what any button does. It cannot be
told, because the mapping is part of what the environment is hiding, and it
cannot experiment freely, because the score counts every action taken against a
per-level baseline. Establishing the rules is therefore not preparation for the
task; it is part of the task, and it has a price.

We built a program-only agent — no neural network, no GPU — to ask a narrow
question: how much can a method establish about an environment it has never
seen, and how would we know if it were fooling us?

The answer to the second half turned out to matter more than the first.

## 2. Method  *(~200 words — DRAFT)*

The agent never sees raw grids. A perception layer reduces each 64×64 board to
4-connected same-colour objects with a position-invariant shape signature, so an
object can be recognised after it moves. Policies reason over that.

Control semantics are learned rather than assumed. The agent presses an
unknown action, measures how the board responded, and keeps the effect when it
can be attributed. What it learns is which colour moves, and in which direction,
per action. It then routes with shortest-path search over cells whose colours it
has observed to be passable, and it abandons a learned mapping when its own
predictions stop coming true.

A second policy family handles the games that take no directional input at all.
Across the 25 official games, eight are played almost entirely with MOUSE and
never once with a direction — 32% of the field, including ft09, the
highest-scoring game in the Milestone #1 winner's recorded run.

> เติม: สถาปัตยกรรมส่วนที่รันจริงบน Kaggle + ผลที่ได้

## 3. Simulation does not predict reality  *(~350 words — COMPLETE)*

We measure every policy in two arenas: the quiet environment we first wrote,
and one carrying noise measured from recorded real games — a HUD strip that
advances on every action, sprites that change shape as they move, and as a
consequence a board that changes on essentially every action.

```
policy       learns?        quiet mock   noise-calibrated mock
--------------------------------------------------------------
random            no          lost 2/3             lost 2/3
greedy            no           WIN 3/3              WIN 3/3
explorer         yes           WIN 3/3             lost 0/3
navigator        yes           WIN 3/3             lost 0/3
```

Three things follow. First, the noise destroys only the methods that learn:
the random and hard-coded policies score identically in both arenas, because
neither has a model for the noise to corrupt. Second, on a board carrying the
noise real boards carry, random play beats both of our deliberate policies,
two levels to none. Third, and least comfortable, results in the quiet arena
carry no information about the noisy one: three policies clear every level
there and their fates diverge completely once the board is realistic.

A fourth point separates two measurements that are easy to conflate. Our
control learner recovers the true action-to-direction mapping on real recorded
boards 79% of the time, across 17 of 25 games. A policy built on that same
79%-accurate mapping finishes no levels at all once the board is noisy.
Component accuracy is not playing ability, and reporting the former as though
it were the latter — which we did, for a while — overstates what has been shown.

We also tried to put a number on the gap by sweeping 18 configurations and
correlating their simulated and real scores. The rank correlation is −0.93, but
it should not be quoted that way: the simulated column takes exactly two values,
decided entirely by one design choice, while the other two parameters move it
not at all. Stated correctly the finding is sharper than a correlation. Our
calibrated simulator discriminates on one axis out of three, ranks that axis
backwards against real data, and behaves as a pass-fail gate rather than a
signal that can be tuned against.

## 4. Four times the simulator convinced us  *(~400 words — COMPLETE)*

Each of the following looked settled in one arena and failed in the next. Each
was caught by testing against data we had not generated.

**One.** Our first control learner matched objects between frames by exact shape
signature and scored 88% in the quiet environment. On 2,276 movement transitions
from recorded games it produced a usable reading 10 times — 0.4% — and recovered
the full mapping in 1 game of 25. The cause is visible in the diffs: real
transitions show 1,040 object appearances and 786 disappearances against 992
movements, because a sprite that animates does not match itself between frames.

**Two.** Our click policy learned which colours respond to a click, on the
reasoning that a responsive colour is worth clicking. In our environment a wrong
click left the board still, which made that signal decisive. In the recorded
click-driven games, between 91% and 100% of all clicks change the board. The
signal separates nothing. What does discriminate is level completion: the best
colour in a game completes levels about 5.2 times more often than average — but
only 1.0% of clicks complete anything, so the evidence is extremely sparse.

**Three.** Our best walking policy cleared every level of the quiet environment
and none of the noise-calibrated one.

**Four, and most pointedly.** Diagnosing failure three, we found that an
animating sprite drags its colour's centre of mass sideways, so a straight move
is learned as a diagonal. Aligning the colour's cells between frames instead
fixes it completely: on the calibrated mock the policy went from clearing no
levels to clearing all three. On real boards that same change scored 55% where
the centroid scored 79%. The arena it passed was itself calibrated from
statistics measured over 500 recorded runs, so matching measured numbers is not
sufficient to make a simulator trustworthy — the statistics we chose to match
came from the same understanding that shaped the method.

We then found most of that fourth gap was repairable. Cell alignment discards an
observation whenever nothing lines up, which on real frames is often; falling
back to the centre of mass in that case scores 77%, recovering 22 of the 24
points while still clearing the noisy mock. The failure was real, but its cause
was a discarded-evidence bug rather than a conflict of principle — which is a
more useful thing to report than the anecdote alone.

Finally, an ablation says what kind of noise matters. Animating the controlled
object alone defeats the policy; animating the goal alone, or every small
object, or adding the HUD, costs nothing. More noise made the test easier. It is
not noise that defeats control learning, but noise on the signal being learned
from.

## 5. What probing actually costs  *(~200 words — COMPLETE)*

Because every action is scored, the price of establishing the rules is a real
constraint rather than a detail.

Feeding recorded transitions to the learner in order, a mapping that is correct
about two directions costs a median of 12 observations. Average accuracy across
all recovered mappings needs considerably more: 56% at 10 observations, 72% at
40, and 81% at 80, after which it flattens. These answer different questions, and
conflating them — as we did — makes starting look far more expensive than it is.
An agent does not need 80 actions before it moves: two correct directions cost
around 12 observations and are enough to begin, and the rest can be learned in
play.

The learner's own confidence is a usable filter with a sharp threshold. Below
0.6 the mapping it reports is 36% accurate; above it, 84–85%. Waiting for higher
confidence buys no further accuracy while costing actions.

Deliberate probing helps, moderately. Replaying the same recorded evidence in a
balanced order rather than the order it occurred lowers the median cost from 12
observations to 10 and learns sooner in 7 of 11 games — but one game doubles in
cost, and the number of games learnable at all does not change.

## 6. What we are releasing  *(~130 words — DRAFT)*

The noise used above is packaged as a wrapper that takes any environment
returning `FrameData`, so the same check can be run against someone else's
agent and environment, with each property switchable to attribute a failure to
one of them.

Three checks would have caught all four of our failures, and we suggest them as
a minimum before believing an agent works: test against data you did not
generate; measure the base rate of whatever signal you learn from, since a
signal present 95% of the time separates nothing; and measure component
accuracy and playing ability separately rather than letting one stand for the
other.

> เติม: ลิงก์ repo · คำสั่งเดียวที่ reproduce ตารางในข้อ 3

## 7. Limitations  *(~100 words — DRAFT, needs the live run)*

> เติมหลังได้ผลเกมสด — ตอนนี้เขียนได้แค่ว่า "ยังไม่เคยรัน" ซึ่งอ่อนเกินไปสำหรับเปเปอร์

The largest limitation is that everything above was measured against recorded
games and against environments we wrote. Our own account predicts that a live
game would reveal a further gap, and until that is run the prediction is
untested.

> เติม: ผลจากเกมสด · ช่องว่างชั้นที่ 5 เจอหรือไม่ · คะแนนที่ได้จริง
