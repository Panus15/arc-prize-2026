<!--
ร่าง Kaggle Writeup — ภาษาอังกฤษ (กรรมการอ่านอังกฤษ)
ปรับปรุง 22 ก.ย. 2026 · repo commit `7fa680a`

โครงนี้จัดตาม **เกณฑ์ให้คะแนน 6 ข้อที่ถ่วงน้ำหนักเท่ากัน** ไม่ใช่ตามลำดับเหตุการณ์
ดู docs/rubric-audit.md — ร่างเดิมทุ่ม 950/1080 คำให้ Theory ข้อเดียว

สถานะ: §2–§8 เขียนครบ · §1 กับท้าย §8 รอผลเกมสด
ทุกตัวเลขต้องย้อนไปหาไฟล์ใน docs/ ได้ · ห้ามเคลมเรื่องคะแนนจนกว่าจะรันจริง
-->

# What a program-only agent can establish about an unknown environment

## 1. The problem  *(~120 words — DRAFT, closing line needs the live run)*

An ARC-AGI-3 agent starts without knowing what any button does. It cannot be
told, because the mapping is part of what the environment hides, and it cannot
experiment freely, because the score counts every action against a per-level
baseline. Establishing the rules is not preparation for the task; it is part of
the task, and it has a price.

We built a program-only agent — no neural network, no GPU — to ask how much a
method can establish about an environment it has never seen, and how one would
know if it were being fooled.

The second half of that question turned out to matter more than the first.

> เติมหลังรันเกมสด: ปิดย่อหน้าด้วยสิ่งที่วัดได้กับเกมจริง

## 2. Method  *(~180 words)*

The agent never sees raw grids. A perception layer reduces each 64×64 board to
4-connected same-colour objects with a position-invariant shape signature, so an
object stays recognisable after it moves.

Control semantics are learned, not assumed. The agent presses an unknown action,
measures how the board responded, and keeps the effect when it can be
attributed to that action rather than to the game moving on its own — learning
which colour moves, and in which direction, per action. It routes by shortest
path over cells it has observed to be passable, and abandons a mapping when its
own predictions stop coming true.

A second policy clicks: in games taking no directional input, and wherever
walking stops producing levels. Of the 25 official games, eight are played
almost entirely with MOUSE and never once with a direction, including the
highest-scoring game in the Milestone #1 winner's recorded run.

Neither policy is the contribution. What they produced is.

## 3. Simulation does not predict reality  *(~280 words)*

Every policy, as first built, runs in two arenas: the quiet environment we first
wrote, and one carrying noise measured from recorded games — a HUD strip
advancing every action, sprites changing shape as they move, and so a board that
changes on essentially every action.

```
policy       learns?        quiet mock   noise-calibrated mock
--------------------------------------------------------------
random            no          lost 2/3             lost 2/3
greedy            no           WIN 3/3              WIN 3/3
explorer         yes           WIN 3/3             lost 0/3
navigator        yes           WIN 3/3             lost 0/3
```

The noise destroys only the methods that learn: the random and hard-coded
policies score identically in both arenas, having no model for it to corrupt. On
a board carrying the noise real boards carry, random play beats both of our
deliberate policies, two levels to none. And the quiet arena carries no
information about the noisy one — three policies clear every level there, then
their fates diverge completely.

Two measurements are easy to conflate. Our control learner recovers the true
action-to-direction mapping on real boards 79% of the time across 17 of 25
games. A policy built on that mapping finishes no levels once the board is
noisy. Component accuracy is not playing ability, and reporting the former as
the latter — which we did — overstates what has been shown.

Across 18 configurations, simulated and real scores correlate at −0.93, a figure
we will not quote: one design choice sets the simulated column's two values, and
the other parameters move it not at all. Correctly stated, the simulator
discriminates on one axis of three, ranks it backwards, and acts as a pass-fail
gate, not a signal to tune against.

## 4. Five failures, and the mechanism behind each  *(~340 words)*

Each looked settled in one arena and failed in the next. Each was caught by
testing against data we had not generated. The mechanisms, not the anecdotes,
are the result.

**One.** Matching objects between frames by exact shape signature scored 88% in
the quiet environment and 0.4% on 2,276 real transitions, recovering the full
mapping in 1 game of 25. *Mechanism:* real transitions show 1,040 object
appearances and 786 disappearances against 992 movements — an animating sprite
does not match itself between frames.

**Two.** Our click policy learned which colours respond to a click. In our
environment a wrong click left the board still, making the signal decisive. In
recorded click-driven games, 91–100% of clicks change the board. *Mechanism:* a
signal present almost always separates nothing. What does discriminate is level
completion — the best colour completes levels 5.2 times more often than average —
but only 1.0% of clicks complete anything.

**Three.** Our best walking policy cleared every level of the quiet environment
and none of the noisy one.

**Four.** Diagnosing three, we found an animating sprite drags its colour's
centre of mass sideways, so a straight move is learned as a diagonal. Aligning
cells between frames fixed the mock completely — and scored 55% on real boards
where the centroid scored 79%. *Mechanism:* cell alignment discards an
observation whenever nothing lines up, which on real frames is often. Falling
back to the centre of mass recovers 22 of those 24 points, at 77%, while still
clearing the noisy mock.

**Five.** Replaying recorded real boards through the agent we were about to
submit, it pressed ACTION5 on 97–100% of turns in all eight walking games
offering it. *Mechanism:* our environment offered interaction only on the goal;
the real engine fixes the action list for a whole game.

An ablation says which noise matters. Animating the controlled object alone
defeats the policy; animating the goal, or every small object, or adding the HUD,
costs nothing. More noise made the test easier. It is not noise that defeats
learning, but noise on the signal being learned from.

## 5. What probing costs  *(~180 words)*

A mapping correct about two directions costs a median of 12 observations.
Average accuracy across all recovered mappings needs far more — 56% at 10
observations, 72% at 40, 81% at 80, then flat. These answer different questions, and
conflating them, as we did, makes starting look far costlier than it is: two
correct directions are enough to begin; the rest is learned in play.

The learner's own confidence is a usable filter with a sharp threshold. Below
0.6 its mapping is 36% accurate; above it, 84–85%. Waiting for more confidence
buys no accuracy while costing actions.

Deliberate probing helps only moderately: a balanced order cuts the median from
12 observations to 10, but one game doubles in cost and no new game becomes
learnable.

## 6. How far this generalises  *(~200 words)*

Nothing above depends on ARC. The mechanism is a property of learning agents: a
method is defeated by noise on the signal it extracts, and untouched by noise
elsewhere.

The failures span two unrelated method families and signal types — control
learning reads displacement, the click policy reads board change — yet both were
defeated the same way, by different noise: the simulator represented their signal
more cleanly than reality does. That is not one method's quirk.

The fourth failure sharpens this into something uncomfortable for any simulator-
built agent. Our second environment was calibrated from statistics measured over
500 recorded runs, and still selected the worse of two designs. Matching measured
statistics is not sufficient: the statistics one chooses to match come from the
same understanding that shaped the method being tested.

We expect this to recur: our own account predicts a further gap between the
calibrated environment and a live game, and that prediction is the most
falsifiable thing here.

## 7. What we release, and how to check it  *(~180 words)*

The noise ships as a wrapper around any environment returning `FrameData`, each
property switchable so a failure can be attributed to one rather than to noise in
general. It runs against another team's agent unchanged.

Three checks would have caught all five failures. We offer them as a minimum
before believing an agent works:

1. Test against data you did not generate — recordings, traces, a live game.
2. Measure the base rate of whatever signal you learn from. A signal present 95%
   of the time separates nothing, however reasonable it looks.
3. Measure component accuracy and playing ability separately. Ours diverged
   completely: 79% and zero levels.

Everything here is reproducible. The main table comes from a single command, 252
tests cover the library, and every figure traces to a document recording the run
that produced it — including the figures that contradict our earlier claims.

> เติม: ลิงก์ repo

## 8. Limitations  *(~60 words — needs the live run)*

Everything was measured against recorded games and environments we wrote. Our
submitted walker clears realistically noisy boards only in environments we
wrote. One recorded game completes nothing in 676 clicks, suggesting some games
need a sequence or a relative position rather than a colour, which our methods
cannot express.

> เติมหลังรันเกมสด: ผลจริง · ช่องว่างชั้นที่ 5 เจอหรือไม่
