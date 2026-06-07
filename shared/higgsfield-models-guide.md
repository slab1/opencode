# Higgsfield Models Guide for Content Creator Agent

## 🎯 Quick Recommendation

For an **all-contents creator agent**, use this tiered approach:

### Tier 1: Daily Use (Best Value)
| Model       | Type  | Cost    | Best For                            |
| ----------- | ----- | ------- | ----------------------------------- |
| **FLUX.2**      | Image | 1 credit  | Quick images, social media, concepts |
| **image_auto**  | Image | 2 credits | Balanced quality/speed               |
| **minimax_hailuo** | Video | 6 credits | Short clips, social videos           |

### Tier 2: Premium Quality
| Model       | Type  | Cost      | Best For                              |
| ----------- | ----- | --------- | ------------------------------------- |
| **GPT Image 2**     | Image | 7 credits   | High-quality marketing, hero images   |
| **cinematic_studio_video** | Video | 8 credits   | Professional video content            |
| **wan2_7**          | Video | 7 credits   | Balanced video quality                |

### Tier 3: Ultra Premium
| Model     | Type  | Cost       | Best For                |
| --------- | ----- | ---------- | ----------------------- |
| **veo3_1**      | Video | 22 credits   | Cinematic, film-quality |
| **seedance_2_0** | Video | 22 credits   | Dance/motion content    |
| **kling3_0**    | Video | 10 credits   | High-quality video      |

## 📊 Cost Analysis

### Image Generation
| Quality Level | Model       | Credits | Resolution | Speed   |
| ------------- | ----------- | ------- | ---------- | ------- |
| Quick         | flux_2      | 1       | 1024x1024  | Fast    |
| Balanced      | image_auto  | 2       | 1024x1024  | Medium  |
| High          | gpt_image_2 | 7       | 2048x2048  | Slower  |

### Video Generation
| Quality Level | Model             | Credits | Duration | Speed   |
| ------------- | ----------------- | ------- | -------- | ------- |
| Budget        | minimax_hailuo    | 6       | 5-10s    | Fast    |
| Balanced      | wan2_7            | 7       | 5-10s    | Medium  |
| Premium       | cinematic_studio  | 8       | 5-15s    | Slower  |
| Ultra         | veo3_1            | 22      | 10-20s   | Slowest |

## 🎨 Use Case Recommendations

### Social Media Content
- **Instagram/TikTok**: `flux_2` (1 credit) + `minimax_hailuo` (6 credits)
- **Twitter/X**: `image_auto` (2 credits) for quick posts
- **YouTube thumbnails**: `gpt_image_2` (7 credits) for hero images

### Marketing Materials
- **Hero images**: `gpt_image_2` (7 credits) - highest quality
- **Product photos**: `cinematic_studio_image` (varies) - professional look
- **Ad videos**: `cinematic_studio_video` (8 credits) - cinematic quality

### Blog/Website Content
- **Featured images**: `flux_2` (1 credit) - fast, good quality
- **Explainer videos**: `minimax_hailuo` (6 credits) - good value
- **Background videos**: `wan2_7` (7 credits) - balanced

### Creative Projects
- **Art/illustrations**: `flux_2` (1 credit) or `recraft_v4_1` (1 credit)
- **Concept art**: `gpt_image_2` (7 credits) - detailed
- **Music videos**: `seedance_2_0` (22 credits) - motion-focused

## 💡 Pro Tips

1. **Start cheap, upgrade if needed**: Begin with `flux_2` (1 credit), only use `gpt_image_2` (7 credits) for final deliverables
2. **Batch similar content**: Generate multiple variations with cheaper models before committing to premium
3. **Use `image_auto` for testing**: 2 credits gives you a good quality preview
4. **Video costs add up**: A 10-second video at 22 credits = 22 images at 1 credit each

## 🔄 Recommended Workflow

```
1. Concept phase: flux_2 (1 credit) - generate 5-10 variations
2. Selection phase: image_auto (2 credits) - refine best concept
3. Final phase: gpt_image_2 (7 credits) - production quality
4. Video phase: minimax_hailuo (6 credits) - quick video test
5. Final video: cinematic_studio_video (8 credits) - production
```

**Total for complete content package**: ~24 credits (1 concept + 1 final image + 1 final video)
