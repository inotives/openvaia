---
name: image_prompting
description: Prompt structure formula, camera/lens/lighting vocabulary, composition techniques, style modifiers, and example templates for AI image generation
tags: [image, prompting, photography, ai-generation, midjourney, stable-diffusion]
source: agency-agents/design/design-image-prompt-engineer.md
---

## Image Prompting

> ~2600 tokens

### Prompt Structure Formula

Build prompts in this layer order:

1. **Subject** -- who/what, details, expression, pose, materials
2. **Environment** -- location, background, atmospheric conditions
3. **Lighting** -- source, direction, quality, color temperature
4. **Camera/Technical** -- perspective, focal length, depth of field, exposure
5. **Style/Aesthetic** -- genre, era, post-processing, reference photographer

### Camera & Lens Vocabulary

| Effect              | Prompt terms                                          |
|---------------------|-------------------------------------------------------|
| Blurred background  | shallow depth of field, f/1.4 bokeh, 85mm lens        |
| Everything sharp    | deep focus, f/11, focus stacked                       |
| Dramatic distortion | wide angle, 24mm lens, barrel distortion              |
| Compressed/flat     | telephoto, 200mm lens, compressed perspective          |
| Miniature effect    | tilt-shift lens, selective focus plane                 |
| Cinematic           | anamorphic lens, 2.39:1 aspect ratio, oval bokeh      |

### Lighting Vocabulary

| Setup              | Prompt terms                                           |
|--------------------|--------------------------------------------------------|
| Golden hour        | warm golden hour side lighting, long shadows            |
| Overcast soft      | diffused overcast light, even soft illumination         |
| Studio key+fill    | softbox key light 45-degrees, fill light opposite side |
| Rembrandt          | Rembrandt lighting, triangle shadow on cheek            |
| Rim/edge           | rim light separating subject from background            |
| Neon/dramatic      | neon-lit, colored gel lighting, cyberpunk atmosphere    |
| Chiaroscuro        | chiaroscuro, dramatic contrast, deep shadows            |
| High key           | high-key lighting, bright, minimal shadows              |
| Low key            | low-key lighting, dark, dramatic single source          |

### Composition Techniques

- **Rule of thirds**: subject placed at intersection points
- **Leading lines**: environment lines drawing eye to subject
- **Negative space**: minimal background, isolated subject
- **Symmetry**: centered, balanced, architectural framing
- **Frame within frame**: doorways, windows, arches framing subject

### Style Modifiers

| Category      | Examples                                                    |
|---------------|-------------------------------------------------------------|
| Genre         | editorial, fashion, commercial, documentary, fine art       |
| Era           | vintage, contemporary, retro 70s, futuristic, timeless      |
| Film stocks   | Kodak Portra 400, Fuji Velvia, Ilford HP5, Cinestill 800T  |
| Color grade   | desaturated, warm tones, cool blue cast, cross-processed    |
| Texture       | film grain, clean digital, matte finish, high contrast      |

### Quality Modifiers

Add at the end of prompts: `8k resolution, professional photography, editorial quality, highly detailed, sharp focus`

### Negative Prompt Patterns

Use to exclude: `blurry, low quality, distorted, watermark, text, oversaturated, artificial looking, plastic skin, extra limbs`

### Genre Templates

**Cinematic Portrait**
```
Dramatic portrait of [subject], [appearance], wearing [attire],
[expression], cinematic lighting: key light 45-degrees camera left
creating Rembrandt triangle, subtle fill, rim light separating from
[background], shot on 85mm f/1.4 at eye level, shallow depth of field,
creamy bokeh, [color palette] color grade, inspired by [photographer],
[film stock] aesthetic, 8k resolution, editorial quality
```

**Luxury Product**
```
[Product] hero shot, [material/finish], positioned on [surface],
studio lighting: large softbox overhead creating gradient, two strip
lights for edge definition, [background], shot at [angle] with
[lens], focus stacked for complete sharpness, clean post-processing,
commercial advertising quality
```

**Landscape**
```
[Location and features], [time of day], [weather/sky], foreground
[element], midground [element], background [element], wide angle
deep focus, [light quality and direction], [color palette],
[documentary/fine art] style, 8k resolution
```

**Environmental Portrait**
```
[Subject] in [location], [activity], natural [time of day] lighting,
environmental context showing [background], shot on [focal length]
at f/[aperture], [composition technique], candid feel, [color palette],
documentary style, authentic aesthetic
```

### Common Pitfalls

- **Vague lighting**: say "soft golden hour side lighting" not "nice lighting"
- **Wrong terminology**: say "shallow depth of field, f/1.8 bokeh" not "blurry background"
- **Contradictions**: shadow direction must match stated light source position
- **Overloading**: 3-5 strong descriptors beat 15 weak ones
- **Missing aspect ratio**: always specify (--ar 16:9, --ar 3:4, etc.)

### Platform-Specific Tips

| Platform         | Key syntax                                               |
|------------------|----------------------------------------------------------|
| Midjourney       | `--ar 16:9 --v 6 --style raw --chaos 20`                |
| DALL-E           | Natural language, no special params, style mixing works  |
| Stable Diffusion | Token weighting `(word:1.3)`, LoRA references, CFG scale|
| Flux             | Detailed natural language, photorealistic emphasis        |
