# Receipt Avalanche — preview review

## Current revision — fixes from the user's screenshot folder

This section supersedes the older illustration notes below. References inspected: Pictures/Screenshots/Screenshot 2026-11-12 225153.png (clerk), 225229.png (printer), and 225317.png (customer handoff). The references were not altered.

- Replaced the filled, deforming sleeve polygons with constant-width shoulder/elbow/wrist paths. Elbow positions are calculated from a two-link arm for each keyed grip pose; wrist coordinates remain tied to the hand and paper. Both characters now use separate, rigid skin-colored hand drawings. The clerk's resting arm no longer ends in a green point, and the apron is one continuous silhouette.
- Corrected handoff draw order: bag and handle behind the clerk's fingers, with the two palms clearly separated. Moved the small receipt from the handle opening onto the bag's lower front so its outline and printed strokes cannot fuse with the hands. Updated the ending's paper transition to start at that new receipt position.
- Removed the duplicate blank paper overlay from the printer shot. The camera now scales uniformly into a blank region of the original printed receipt, keeping its existing edge and ink continuous. There is exactly one printed sheet during that shot.
- Replaced floating-point termination of receipt-tooth generation with exactly ten iterations; the old loop could create an extra tooth. The printer's serration is likewise generated at a consistent pitch.

Validation: final check 2d22c1d3-f48f-4b97-a7cc-797b969ce196 returns ok=true, browserSkipped=false, and zero errors/warnings in lint, runtime, layout, motion, contrast, craft and audio. Reviewed the changed areas at 3×–4× native crop scale, the printer transition at eight intermediate frames, and the refreshed beat/phone/cut sheets. These pixels, rather than the passing technical gate alone, were used to assess the screenshot defects.

Stable visual evidence: review/owner-detail.png, review/handoff-detail.png and review/printer-sequence.jpg. Latest full review sheets: .hyperframes/artifacts/snapshots/b29cfa75-e1ad-4a26-aff7-37d36d4cfcd4/. The live preview remains on port 3018; HTTP 200 was verified. Music and duration are unchanged. No new MP4 was exported in this correction turn.

Selected direction: Receipt Avalanche, requested by the user, with original vector art and music. The retail-pinball and living-poster alternatives were not built. Preserve ../../instagram/ as the rejected first version.

## Creative result

24.6 seconds, 1080 × 1920, 30 fps. An orange printer close-up establishes the hook; a continuous receipt tangles around an illustrated shop, the owner braces and pulls, and the paper straightens on the music change. One short real stock update provides proof. A full customer character then collects a bag; a receipt carries the film into the SampleERP end card.

Canonical artwork lives in scripts/art.mjs. Scene source is generated as editable literal HTML/SVG by scripts/build.mjs. No generated bitmap illustrations, stock characters, emojis or unrelated background shapes were used. League Gothic supplies the retail-poster type; Circuit green and the actual app logo anchor the source identity. SampleERP is the primary campaign name; Circuit Market is identified as the demo.

## Source and sound

- Actual product evidence was captured in an isolated browser from the unchanged local SampleERP application. One real demo order changes MacBook Air M3 stock from 24 to 23. Before/after images have identical crops and blurred focus, with no caret or focus-ring jump. Product name and stock fields are cropped tightly enough to read.
- Music is Electro Cabello by Kevin MacLeod, used under CC BY 4.0. The user authorized an alternative licensed source after the HeyGen helper proved unavailable on this Windows host. MUSIC-LICENSE.txt and INSTAGRAM-CAPTION.txt retain the artist, source, license link and modification disclosure. The final card includes an on-screen credit.
- Artist metadata and local signal analysis agree at 117 BPM. First source onset is 0.025s; a measured section change at 16.445s is edited onto the control cut at 8.2s. The actor's anticipation ends before that cut and the straightening begins at the cut. Bar boundaries are rounded independently to frames.
- Edited cue is assets/music/music-cut.wav: 24.6s, -15.7 LUFS integrated, -4.2 dBTP, zero clipped samples in signal analysis. Four source SFX have visible causes. The audio was measured, not listened to. Final mixed MP4 loudness is still to be verified after export.

## Technical gate

Final check report: .hyperframes/artifacts/checks/59c8f909-9c94-4fa2-81dd-b687fd6db4e8.json, also saved as check-report.json. Overall ok=true and browserSkipped=false. Lint, runtime, layout, motion, contrast, craft and audio each report zero errors and zero warnings.

Motion assertions cover the initial hook, one-sold stamp and CTA appearance, before/after stock ordering and excessive stillness. Foreground paper transitions participate in the motion checks; they are not hidden from the auditor as decoration.

## Visual and contact review

Reviewed scene beat frames, all cut strips and a 360px phone sheet, then inspected eight-frame pull and customer-handoff ranges. Updated pull evidence: .hyperframes/artifacts/snapshots/61acbfac-8caa-424d-92ed-af96111d940f/contact-sheet.jpg. Updated handoff evidence: .hyperframes/artifacts/snapshots/2a98d410-5f03-41f6-a05b-153471a55c80/contact-sheet.jpg.

An independent visual review found four P1s in the rough artwork: an oversized isolated customer sleeve, unclear paper grip, weak final transaction image, and insufficient software identity. Fixes:

- Replaced the sleeve with a proportioned full customer, articulated forearm and keyed steps. Customer and bag share motion after contact; the owner's hand releases first.
- Moved the paper grip outside the owner's torso to (650,1010), so the paper visibly reaches the palm. Anticipation uses (620,1000). The arm and paper endpoint follow the same coordinates and ease.
- Retracted the arch before the exchange and showed the shared bag handle, release and customer departure.
- Enlarged the actual product header, named SampleERP in the proof and made SAMPLE ERP the large end-card identity.

The focused independent recheck established no remaining P0/P1 defects in its sampled images and confirmed these four findings resolved. Still images cannot establish the entire movement or audible musical fit. After that review, the music entry and pull timing were refined; an additional eight-frame range verifies continuity across the revised cut.

Additional corrections: morphing arm and eyebrow paths now retain identical command/point structures, eliminating stray interpolation lines. Receipt leaves are clipped to the shop region y≥565 so they cannot land over the reading headline. Foreground paper expansion starts at the visible receipt's location instead of arriving as an unrelated wipe.

## Intentional exceptions and limits

Only the three contour paths forming each thick illustrated ribbon carry data-layout-ignore: the connector heuristic interprets them as UI connector shafts, while their endpoints are intentionally under the printer lip and gripping fingers. Character groups, hands, receipt leaves, titles and proof are audited. Foreground paper has narrow intentional-overflow/occlusion attributes.

The weakest beat is the short proof interval: it is intentionally a factual pause within an illustrated film, not a live walkthrough. A later Instagram reference could guide a different illustration language or cut density. Sound has not been auditioned here, and this is not a promise that every platform placement's overlays match the chosen safe band.

## Handoff

Editable review URL: http://localhost:3018/#project/film . No new MP4 has been exported yet. The user must review this new cut before export under the HyperFrames workflow. No publishing, upload or Instagram automation connection was performed.
