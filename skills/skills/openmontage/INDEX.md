# OpenMontage Skills — Import Index

> **Source:** [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL-3.0)
> **Imported:** 2026-06-22
> **Destination:** `~/.config/opencode/skills/skills/openmontage/`
> **Total:** ~545 skill files across 73 directories (4 Layer 2 groups + 69 Layer 3 skill packages)

---

## Knowledge Architecture (from OpenMontage)

OpenMontage organizes its skills in a 3-layer knowledge architecture:

```
Layer 1: tools/tool_registry.py          "What tools exist and what they can do"
Layer 2: skills/                          "How OpenMontage uses these tools"
         {core, creative, meta, pipelines}/
Layer 3: .agents/skills/                  "How the technology itself works"
         Generic API knowledge — correct import paths, code patterns,
         constraints, parameters — tech-agnostic
```

This import covers **Layers 2 & 3** — the project-specific conventions (Layer 2) and the generic API/tech knowledge (Layer 3).

---

## Layer 2: Pipeline & Project Skills (~150 files)

These teach how OpenMontage integrates tools into its pipelines and conventions.

### `core/` — Core Tool Skills (6 files)

| Skill | File | Purpose |
|-------|------|---------|
| FFmpeg | `core/ffmpeg.md` | Video encoding, filtering, composition |
| Remotion | `core/remotion.md` | React-based composition |
| HyperFrames | `core/hyperframes.md` | HTML/CSS/GSAP composition runtime |
| WhisperX | `core/whisperx.md` | Transcription with word-level timestamps |
| Subtitle Sync | `core/subtitle-sync.md` | Subtitle timing and alignment |
| Color Grading | `core/color-grading.md` | FFmpeg color profiles, LUT workflow |

### `creative/` — Creative Skills (33 files)

- **Video Production:** video-editing, enhancement-strategy, video-stitching, cinematic, short-form, long-form, screen-recording, animation-pipeline, scene-detect-usage, broll-planning, stock-sourcing-usage
- **Prompting Subfamily:** video-gen-prompting, seedance-prompting, grok-prompting, sora-prompting, veo-prompting, ltx-prompting, hunyuan-prompting
- **Visual Design:** typography, data-visualization, diagram-gen-usage, image-gen-usage, image-provider-usage
- **Audio:** sound-design, music-gen-usage
- **AI/ML:** bg-remove-usage, upscale-usage, face-restore-usage, lip-sync-usage, talking-head-gen-usage, video-understand-usage
- **Narrative:** storytelling, manim-usage

### `meta/` — Meta Skills (8 files)

| Skill | File | Purpose |
|-------|------|---------|
| Onboarding | `meta/onboarding.md` | First-interaction greeting, capability discovery |
| Reviewer | `meta/reviewer.md` | Self-review protocol after every stage |
| Checkpoint Protocol | `meta/checkpoint-protocol.md` | Human approval checkpoints |
| Skill Creator | `meta/skill-creator.md` | Dynamically create new skills during pipeline runs |
| Animation Runtime Selector | `meta/animation-runtime-selector.md` | Runtime selection guidance |
| Capability Extension | `meta/capability-extension.md` | Extending system capabilities |
| Creative Intake | `meta/creative-intake.md` | Creative brief intake process |
| Video Reference Analyst | `meta/video-reference-analyst.md` | Analyzing reference videos |

### `pipelines/` — Pipeline Stage Director Skills (103 files across 12 pipelines)

Each pipeline has an Executive Producer + 7-8 stage directors:

| Pipeline | Stages | Focus |
|----------|--------|-------|
| `explainer/` | 8 | Animated explainer production v2.0 |
| `talking-head/` | 7 | Talking head video production |
| `screen-demo/` | 8 | Screen recording/demo production v2.0 |
| `clip-factory/` | 8 | Short-form clip batch production v2.0 |
| `podcast-repurpose/` | 8 | Podcast clip repurposing v2.0 |
| `cinematic/` | 8 | Cinematic video production v2.0 |
| `animation/` | 9 | Math/data animation (Manim) v2.0 |
| `hybrid/` | 8 | Mixed-source video production v2.0 |
| `avatar-spokesperson/` | 8 | AI avatar presenter videos v2.0 |
| `localization-dub/` | 8 | Multi-language dubbing v2.0 |
| `character-animation/` | 11 | Local cartoon character animation |
| `documentary-montage/` | 6 | Documentary-style montage production |

---

## Layer 3: API & Technology Skills (~395 files across 69 packages)

Generic skill packages covering APIs, libraries, and technologies:

### Video Processing & Composition (6 packages)
- `ffmpeg/` — FFmpeg video processing
- `video_toolkit/` — Video toolkit utilities
- `remotion/`, `remotion-best-practices/` — React-based video (38+2 files)
- `hyperframes/`, `hyperframes-cli/`, `hyperframes-registry/`, `website-to-hyperframes/` — HTML/CSS/GSAP runtime (38+1+8+9 files)

### AI Video Generation (10 packages)
- `ai-video-gen/`, `create-video/` (10 files), `video-download/`, `video-edit/` (2), `video-translate/`, `video-understand/` (2)
- `heygen/` (21 files), `avatar-video/` (16 files), `faceswap/`, `visual-style/` (16 files)
- `seedance-2-0/` — Premium cinematic AI video

### TTS & Audio (6 packages)
- `text-to-speech/`, `speech-to-text/` (7 files), `elevenlabs/` (2 files)
- `music/` (3 files), `sound-effects/` (2 files), `doubao-tts/`

### Image Generation (3 packages)
- `flux-best-practices/` (14 files), `bfl-api/` (7 files), `grok-media/`

### Math Animation (3 packages)
- `manimce-best-practices/` (24 files), `manimgl-best-practices/` (27 files), `manim-composer/` (5 files)

### 3D Graphics (10 packages — Three.js ecosystem)
- `threejs-{animation,fundamentals,geometry,interaction,lighting,loaders,materials,postprocessing,shaders,textures}/`

### Diagrams & Visualization (2 packages)
- `beautiful-mermaid/` (2 files), `d3-viz/` (4 files)

### Animation & Motion (4 packages)
- `framer-motion/`, `lottie-bodymovin/`, `gsap/` + 7 GSAP satellite packages (gsap-core, gsap-frameworks, gsap-performance, gsap-plugins, gsap-react, gsap-scrolltrigger, gsap-timeline, gsap-utils)

### Character Animation (4 packages)
- `canvas-procedural-animation/`, `character-animation-qa/`, `character-rigging/`, `pose-library-design/`, `svg-character-animation/`

### Design & Web (4 packages)
- `tailwind-design-system/`, `web-design-guidelines/`, `vercel-react-best-practices/` (71 files), `vercel-composition-patterns/` (13 files)

### Infrastructure & Tools (6 packages)
- `acestep/`, `ltx2/`, `playwright-recording/` (2 files), `synthetic-screen-recording/`, `setup-api-key/`, `agents/` (6 files)

---

## Comparison with Hermes Skills

Our existing skills directory (`~/.config/opencode/skills/skills/hermes/`) contains 72 Hermes-style skill packages focused on general agent capabilities. The OpenMontage import adds:

| Dimension | Hermes Skills (72) | OpenMontage (73 packages, ~545 files) |
|-----------|-------------------|--------------------------------------|
| **Domain** | General agent productivity | Video production pipeline |
| **Depth** | Single SKILL.md per package | Multi-file packages (up to 71 files) |
| **Focus** | Tools & APIs | Production workflows & stage direction |
| **Pipeline** | None | 12 end-to-end video pipelines |
| **AI Video** | Minimal | Extensive (HeyGen, Seedance, etc.) |
| **3D/Animation** | None | Three.js, GSAP, Manim, Lottie |

---

## Usage

These skills teach an agent how to use OpenMontage's pipeline system. They are SKILL.md format files loadable via the `skill` tool.

To register any of these skills with an agent, reference the skill by its path:

```
skill: "openmontage/ffmpeg"
skill: "openmontage/core/ffmpeg"
skill: "openmontage/pipelines/explainer/script-director"
```

---

## Source

- **Repository:** [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage)
- **License:** AGPL-3.0
- **Imported files:** ~545 markdown files across 4 Layer 2 groups + 69 Layer 3 packages
- **Original INDEX.md:** `/home/OpenMontage/skills/INDEX.md`
