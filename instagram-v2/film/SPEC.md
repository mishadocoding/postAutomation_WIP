# Receipt Avalanche — final working specification

GOAL: Make a shop operator recognize the pressure of busywork, enjoy a visual joke, and remember that Circuit Market connects orders and stock. No production or speed claims.
OUTPUT: HyperFrames, 1080 × 1920, 30 fps, 24.6 seconds / 738 frames, portrait Instagram advertising sample.
STORY: User selected Receipt Avalanche. Keep version 1 unchanged. Do not revert to a title-and-screenshot walkthrough.

LOOK: Original editable flat vector illustration. Ink #1b2520, Circuit green #27755d, deep green #153e30, paper #fffdf7, chaos orange #f3693b, lime #d9ed9c, skin #e6a17d. 5.5px ink contours in the 1080-unit art space, round material joins, sharp paper teeth. Front-facing shop with shallow side faces only. No general shadow, grain, gradient or glow. League Gothic 400 at 130–154px / .96 line height / -1px tracking; Receipt Sans (local Inter) 700 at 28–52px for supporting information. Titles hold after landing.

SAFE AREA: key words x=90–930, y=226–1285; bottom 635px and right 150px contain background only except incidental edge of a parcel. Decorative paper may cross the frame during the intentional foreground-paper transition. Current platform overlays vary by placement.

OBJECTS: one canonical printer and slot, one canonical paper silhouette, one canonical shop, one original shopkeeper rig with stable limb path topology, a box and carry bag, and the original captured Circuit logo. Artwork source: scripts/art.mjs. All copies share this source, not independent redraws. Grip poses share coordinates with the ribbon endpoint. Bag contact target is the right handle corner at (604, 989); bag base lands on the counter at y=1120/1121.

MOTION: object entrances power4.out, paper growth and path morph power3.inOut, paper expansion power4.inOut, head reaction power3.inOut with a longer settle. Printer anticipation 0.05–0.29s; paper feed 0.12–0.60s. Loose receipts fall over 0.48s with 0.25s offsets, not in unison. Titles do not drift. No character breathing loop. Paper transitions originate from the visible prop's coordinates, not from an unrelated offscreen wipe.

MUSIC: Electro Cabello by Kevin MacLeod; author source https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1400048 ; CC BY 4.0. License and publication credit in MUSIC-LICENSE.txt. Artist metadata and local signal analysis both report 117 BPM. Measured first onset 0.025s; measured section change 16.445s. The 24.6s cue joins source 0.025–8.225s to 16.445–32.845s, bringing the measured section change onto the control beat at t=8.2. Normalize the edited cue with a limiter and loudnorm at -16 LUFS / -1.5 dBTP target. Final mix still requires measurement. Do not claim the music was listened to; it was analyzed as a signal.

TIMING: calculate each bar boundary independently from the measured tempo, round to a frame; never repeatedly add rounded beat lengths. Working cuts are f0,62,246,369,492,615,738. Real musical transitions and optical contacts take precedence over an arbitrary fixed duration.

SHOTS:
- f0–61 / printer burst, orange ground. Frame 0 has a readable “RUNNING / A SHOP?” and a recognizable printer with paper already visible. Feed paper, settle printer, expand that same receipt from x374/y601/scaleX.3037/scaleY.2186 into the next world. One whoosh on the actual feed.
- f62–245 / paper everywhere. Same shop and owner, white ground. Grow a continuous receipt from the printer slot (400,1130) to the grip (650,1010), curl around the facade, then rain eight matching receipt leaves. Owner reacts with a keyed head pose and blink. “PAPER. / EVERYWHERE.”
- f246–368 / control. Start from the same final shop state. Shared grip and arm move to (620,1000), then release back to (650,1010) while the paper path straightens. Loose paper collects at the printer rather than vanishing at a cut. The mouth and brows change through paths with identical commands and coordinate counts. “TAKE / CONTROL.” Paper pushes into the next shot from the actual grip-side strip.
- f369–491 / real proof. Receipt-shaped frame, lime surroundings. Actual MacBook Air M3 header and actual available-stock crop change from 24 to 23 at local 1.55s. Large, tightly captured real labels replace the old tiny whole-screen UI. “ONE SALE. / STOCK UPDATED.” A one-sold stamp marks the change. The receipt grows to fill the frame.
- f492–614 / payoff. Return to the same shop, clear counter, pleased owner. The paper retracts; the hand takes the bag at its actual handle anchor. The bag lands on the counter. “RUN THE SHOP. / NOT THE CHAOS.” The small receipt protruding from the bag grows into the next shot.
- f615–737 / receipt end card. Pull back from the same paper material to a printed receipt/poster on brand green. Original logo, Circuit Market, source copy “A little clarity for a busy day,” and “Explore the demo.” Music credit remains readable for the final hold.

BANNED: unrelated geometric decoration; random particles; fake dashboard; invented product control; API/production claims; dark neon void; floating UI cards; identical slide-up entrances; misaligned click rings; false shadow depth; changing prop silhouettes; mismatched SVG path topology; one large art ignore wrapper; unreadable whole-screen UI; silent finished video; synthesized replacement soundtrack.

QA: runtime/layout/contrast/audio/craft checks; motion assertions; full scene beat and phone sheets; every cut strip; 8-frame grip/contact range; paper expansion start/mid/end; matching before/after proof captures without caret/focus jumps; independent review of P0/P1 art/contact/continuity defects before preview handoff. Review all decoded render frames when export is authorized.

KNOWN AUDIT INTENT: only the three contour paths of each illustrated paper ribbon carry data-layout-ignore. The connector detector mistakes these thick artwork paths for UI connector shafts whose endpoints should be visible. Their endpoints are intentionally underneath the printer lip and gripping hand. No character, receipt leaf, proof or title is exempted as a whole.
