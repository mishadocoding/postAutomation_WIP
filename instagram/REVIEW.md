# Review — Circuit Market Instagram preview

Selected direction: the user's combination of the scattered-work opening and one real sale through stock and fulfillment. The alternate language-switching film was not built.

Creative result: 25 seconds, 1080 × 1920, 30 fps. Product white and green, 88–102px claims, large 24 → 23 stock change, actual source screenshots, original captured logo, and eight restrained action sounds. No voiceover or music, as requested for this preview. Important copy and proof stay in the central portrait band; the bottom and right action areas are reserved. Placement overlays can vary.

## Verified

- An isolated browser ran the actual local product. A real demo order for one MacBook Air M3 reduced its stock from 24 to 23, then its real status advanced through Processing, Shipped and Completed. Capture manifest: assets/product/capture.json. The existing user's browser storage and source application were not edited.
- Final `hyperframes check --json` returned ok=true and browserSkipped=false. Lint, runtime, layout, motion, contrast, craft and audio each reported zero errors and zero warnings.
- Motion assertions verified the opening, stock value and CTA appearances, ordering of sale confirmation before stock deduction, and absence of long static stretches.
- Reviewed the full beat sheet, the 360px phone sheet, all six cut strips, and updated exact-cut frames. The opening now starts moving at 0.15 seconds. Cut-frame headings remain visible instead of starting on an empty frame.
- Preview server was checked with HTTP 200 and `preview --status` reported its managed process running on port 3017.

## Corrections made

- Workspace exit changed from a second fromTo to a to tween, eliminating unstable initial-state seeking.
- Sale confirmation shortened to “Order created” so the short hold is readable.
- Product-detail image windows intentionally crop to the source's first stock row; fulfillment windows crop away controls. The exact screenshot wrappers declare intentional overflow, preserving other layout audits.
- No automated warnings remain. The last three seconds intentionally hold the end card after its entrance.

## Limits and weakest shot

The whole-workspace overview is contextual: its small UI labels are not intended to be read on a phone. Product details and status are explained by much larger editorial callouts. A further iteration could replace the overview with a longer live interaction recording if the user wants more of a walkthrough.

Audio files were validated as readable and non-silent by the check. The exported mix was measured, not listened to: -21.3 LUFS integrated, -8.6 dBTP true peak, zero clipping and no analysis warnings. The sparse sound-effects-only mix deliberately has long silent gaps and was not boosted to music-bed loudness.

The user approved the preview. Exported renders/circuit-market-instagram.mp4: 25.000 seconds, 1080 × 1920, 30 fps, 750 frames, H.264 / yuv420p with stereo AAC at 48 kHz, 2,280,795 bytes. A full FFmpeg decode completed without errors. Decoded frames at 0, 5, 10, 15, 20 and 24 seconds were reviewed in renders/delivery-frames.jpg and match the intended sequence. Nothing was uploaded, published, or connected to Instagram automation. The editable preview remains available on port 3017.
