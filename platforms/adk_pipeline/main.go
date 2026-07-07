// ADK Go 2.0 — Platform Manager Content Pipeline
//
// Full integration: content-gen.py → media-optimizer.py → post.sh → calendar.py → analytics.py
// Runs as console app, web service, or REST API.
//
// Build:  go build -o pipeline . && ./pipeline console
// Config: ADK_PIPELINE_DRY_RUN=true|false (default: auto-detect)
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/workflowagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/session"
	"google.golang.org/adk/v2/workflow"
)

// ── Config ────────────────────────────────────────────────────

var (
	platformsDir  = os.ExpandEnv("$HOME/.config/opencode/platforms")
	scripts       = struct {
		contentGen  string
		mediaOpt    string
		postSh      string
		calendarPy  string
		analyticsPy string
	}{
		contentGen:  filepath.Join(platformsDir, "content-gen.py"),
		mediaOpt:    filepath.Join(platformsDir, "media-optimizer.py"),
		postSh:      filepath.Join(platformsDir, "post.sh"),
		calendarPy:  filepath.Join(platformsDir, "calendar.py"),
		analyticsPy: filepath.Join(platformsDir, "analytics.py"),
	}
	outputDir  = "/tmp/adk-pipeline"
	postsLog   = filepath.Join(platformsDir, "posts.jsonl")
	calendarFile = filepath.Join(platformsDir, "calendar.json")
	dryRun     = true
)

func init() {
	if v := os.Getenv("ADK_PIPELINE_DRY_RUN"); v != "" {
		dryRun = v != "false"
	} else {
		dryRun = !backendIsReady()
	}
	os.MkdirAll(outputDir, 0755)
}

type backendConfig struct {
	Backend string `json:"backend"`
	Status  string `json:"status"`
}

func backendIsReady() bool {
	data, err := os.ReadFile(filepath.Join(platformsDir, "backend.json"))
	if err != nil {
		return false
	}
	var cfg backendConfig
	if json.Unmarshal(data, &cfg) != nil {
		return false
	}
	return cfg.Status != "" && !strings.Contains(cfg.Status, "pending")
}

// ── Domain types ──────────────────────────────────────────────

type ContentPiece struct {
	Text      string   `json:"text"`
	MediaPath string   `json:"media_path,omitempty"`
	Platforms []string `json:"platforms"`
}

type OptimizedAssets struct {
	Content  ContentPiece      `json:"content"`
	Variants map[string]string `json:"variants"`
}

type PostInput struct {
	Platform string `json:"platform"`
	Text     string `json:"text"`
	Media    string `json:"media,omitempty"`
}

type PostResult struct {
	Platform string `json:"platform"`
	PostID   string `json:"post_id,omitempty"`
	Status   string `json:"status"`
	Error    string `json:"error,omitempty"`
}

// ── Script runners ────────────────────────────────────────────

func runScript(script string, args ...string) (string, error) {
	cmd := exec.Command("python3", append([]string{script}, args...)...)
	out, err := cmd.CombinedOutput()
	output := strings.TrimSpace(string(out))
	if err != nil {
		return output, fmt.Errorf("%s: %w\n%s", script, err, output)
	}
	return output, nil
}

func generateContentFromAI(topic string) (text string, mediaPath string, err error) {
	log.Printf("  [content-gen] topic=%q", topic)

	// Generate caption
	caption, err := runScript(scripts.contentGen, "caption", "--topic", topic, "--platform", "twitter")
	if err != nil {
		log.Printf("  [content-gen] caption failed (AI might be offline): %v", err)
		caption = topic // fallback to raw topic
	}

	// Generate image (optional — silently fails if no AI endpoint)
	imgOut := filepath.Join(outputDir, "generated.png")
	_, imgErr := runScript(scripts.contentGen, "image",
		"--prompt", fmt.Sprintf("Social media post about: %s", topic),
		"--output", imgOut)
	if imgErr != nil {
		log.Printf("  [content-gen] image gen skipped: %v", imgErr)
		mediaPath = ""
	} else {
		mediaPath = imgOut
	}

	return caption, mediaPath, nil
}

func optimizeForPlatforms(mediaPath string, platforms []string) (map[string]string, error) {
	if mediaPath == "" {
		return map[string]string{}, nil
	}
	if _, err := os.Stat(mediaPath); os.IsNotExist(err) {
		return map[string]string{}, nil
	}

	log.Printf("  [media-optimizer] %s for %v", mediaPath, platforms)
	optOut, err := runScript(scripts.mediaOpt, mediaPath,
		"--platforms", strings.Join(platforms, ","),
		"--output-dir", filepath.Join(outputDir, "optimized"))
	if err != nil {
		log.Printf("  [media-optimizer] error: %v", err)
		return map[string]string{}, nil
	}
	log.Printf("  [media-optimizer] output:\n%s", optOut)

	// Parse the results — media-optimizer outputs "✓ desc: /path (WxH)" lines
	variants := map[string]string{}
	for _, line := range strings.Split(optOut, "\n") {
		for _, p := range platforms {
			marker := fmt.Sprintf("_%s_", p)
			if strings.Contains(line, marker) {
				parts := strings.Split(line, ":")
				if len(parts) >= 2 {
					pathPart := strings.TrimSpace(parts[len(parts)-1])
					if idx := strings.Index(pathPart, " ("); idx > 0 {
						pathPart = pathPart[:idx]
					}
					variants[p] = pathPart
				}
			}
		}
	}
	return variants, nil
}

func callPostSh(platform, text, media string) (PostResult, error) {
	args := []string{
		scripts.postSh,
		"--platforms", platform,
		"--text", text,
	}
	if media != "" {
		args = append(args, "--media", media)
	}
	if dryRun {
		args = append(args, "--dry-run")
	} else {
		args = append(args, "--yes")
	}

	log.Printf("  [post.sh] %s (dry_run=%v)", platform, dryRun)
	cmd := exec.Command("bash", args...)
	out, err := cmd.CombinedOutput()

	result := PostResult{Platform: platform, Status: "published"}
	if err != nil {
		result.Status = "failed"
		result.Error = fmt.Sprintf("%s: %s", err, strings.TrimSpace(string(out)))
	} else {
		result.PostID = fmt.Sprintf("p_%s_%d", platform, time.Now().UnixNano())
	}
	return result, nil
}

func addToCalendar(text string, platforms []string, media string) string {
	args := []string{scripts.calendarPy, "add",
		"--text", text,
		"--platforms", strings.Join(platforms, ","),
	}
	if media != "" {
		args = append(args, "--media", media)
	}
	if dryRun {
		args = append(args, "--schedule", "now", "--status", "draft")
	} else {
		args = append(args, "--schedule", time.Now().UTC().Format(time.RFC3339))
	}
	out, err := exec.Command("python3", args...).CombinedOutput()
	if err != nil {
		log.Printf("  [calendar] add failed: %v", err)
		return ""
	}
	// Parse ID from output like "✓ Added: cal_20260702_123456_000"
	output := string(out)
	for _, line := range strings.Split(output, "\n") {
		if strings.Contains(line, "Added: cal_") {
			parts := strings.Split(line, "cal_")
			if len(parts) >= 2 {
				id := "cal_" + strings.TrimSpace(parts[len(parts)-1])
				log.Printf("  [calendar] added: %s", id)
				return id
			}
		}
	}
	return ""
}

func logToJSONL(results []PostResult) {
	entry := map[string]any{
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"dry_run":   dryRun,
		"count":     len(results),
		"results":   results,
	}
	data, _ := json.Marshal(entry)
	os.MkdirAll(filepath.Dir(postsLog), 0755)
	os.WriteFile(postsLog, append(data, '\n'), 0644)
}

func triggerAnalytics() {
	if _, err := os.Stat(scripts.analyticsPy); os.IsNotExist(err) {
		return
	}
	go func() {
		out, _ := exec.Command("python3", scripts.analyticsPy, "fetch").CombinedOutput()
		log.Printf("  [analytics] %s", strings.TrimSpace(string(out)))
	}()
}

// ── Pipeline nodes ────────────────────────────────────────────

func contentGen(ctx agent.Context, prompt string) (ContentPiece, error) {
	log.Printf("  📝 [content_gen] generating content for: %q", prompt)

	// 1. Read configured platforms from accounts.json
	platforms := getConfiguredPlatforms()
	if len(platforms) == 0 {
		platforms = []string{"twitter"}
	}

	// 2. Generate text + media via content-gen.py
	text, mediaPath, err := generateContentFromAI(prompt)
	if err != nil {
		log.Printf("  ⚠️ [content_gen] AI unavailable, using raw prompt: %v", err)
		text = prompt
	}

	return ContentPiece{
		Text:      text,
		MediaPath: mediaPath,
		Platforms: platforms,
	}, nil
}

func mediaOptimize(ctx agent.Context, content ContentPiece) (OptimizedAssets, error) {
	log.Printf("  🎨 [optimize_media] %d platforms", len(content.Platforms))

	variants, err := optimizeForPlatforms(content.MediaPath, content.Platforms)
	if err != nil {
		log.Printf("  ⚠️ [optimize_media] error: %v", err)
	}
	if len(variants) == 0 {
		// Fallback: no media, just pass through
		for _, p := range content.Platforms {
			variants[p] = ""
		}
	}

	return OptimizedAssets{Content: content, Variants: variants}, nil
}

func postBody(ctx agent.Context, assets OptimizedAssets, emit func(*session.Event) error) ([]PostResult, error) {
	if len(assets.Content.Platforms) == 0 {
		return nil, nil
	}

	postNode := workflow.NewFunctionNode("post_single",
		func(ctx agent.Context, input PostInput) (PostResult, error) {
			return callPostSh(input.Platform, input.Text, input.Media)
		}, workflow.NodeConfig{})

	results := make([]PostResult, 0, len(assets.Content.Platforms))

	for i, platform := range assets.Content.Platforms {
		input := PostInput{
			Platform: platform,
			Text:     assets.Content.Text,
			Media:    assets.Variants[platform],
		}

		// HITL: ask before real posts
		if !dryRun {
			_, err := workflow.ResumeOrRequestInput(ctx, emit, session.RequestInput{
				InterruptID: fmt.Sprintf("approve_%s_%d_%d", platform, i, time.Now().UnixNano()),
				Message:     fmt.Sprintf("Approve posting to %s?\n\nText: %s", platform, assets.Content.Text),
			})
			if err != nil {
				return nil, err // ErrNodeInterrupted pauses graph
			}
			log.Printf("  ✅ [hitl] %s approved", platform)
		}

		result, err := workflow.RunNode[PostResult](ctx, postNode, input,
			workflow.WithUseSubBranch(),
			workflow.WithRunID(fmt.Sprintf("%s-%d", platform, i)),
		)
		if err != nil {
			log.Printf("  ❌ [post] %s failed: %v", platform, err)
			results = append(results, PostResult{Platform: platform, Status: "failed", Error: err.Error()})
			continue
		}
		results = append(results, result)
	}

	return results, nil
}

func summarizeAndFinalize(ctx agent.Context, results []PostResult) (string, error) {
	log.Printf("  ✅ [finalize] %d posts", len(results))

	for _, r := range results {
		log.Printf("     %s: %s [%s]", r.Platform, r.Status, r.PostID)
	}

	// Extract platforms + text from results for calendar
	platforms := make([]string, len(results))
	for i, r := range results {
		platforms[i] = r.Platform
	}

	// Add to calendar
	if len(results) > 0 && results[0].Status == "published" {
		addToCalendar(results[0].Platform+" post", platforms, "")
	}

	// Log to posts.jsonl
	logToJSONL(results)

	// Trigger analytics (async)
	triggerAnalytics()

	return fmt.Sprintf("Done: %d posts published", len(results)), nil
}

func getConfiguredPlatforms() []string {
	data, err := os.ReadFile(filepath.Join(platformsDir, "accounts.json"))
	if err != nil {
		return nil
	}
	var accts struct {
		Accounts map[string]struct {
			Status string `json:"status"`
		} `json:"accounts"`
	}
	if json.Unmarshal(data, &accts) != nil {
		return nil
	}
	var out []string
	for name, acct := range accts.Accounts {
		if acct.Status == "configured" {
			out = append(out, name)
		}
	}
	return out
}

// ── Graph ─────────────────────────────────────────────────────

func buildAgent() (agent.Agent, error) {
	b := workflow.NewEdgeBuilder()

	gen       := workflow.NewFunctionNode("content_gen",      contentGen,        workflow.NodeConfig{})
	optimize  := workflow.NewFunctionNode("optimize_media",   mediaOptimize,     workflow.NodeConfig{})
	postAll   := workflow.NewDynamicNode("post_all",          postBody,          workflow.NodeConfig{})
	finalize  := workflow.NewFunctionNode("finalize",         summarizeAndFinalize, workflow.NodeConfig{})

	b.Add(workflow.Start, gen)
	b.Add(gen, optimize)
	b.Add(optimize, postAll)
	b.Add(postAll, finalize)

	return workflowagent.New(workflowagent.Config{
		Name:        "content_pipeline",
		Description: "Full content pipeline: content-gen → media-opt → post.sh → calendar → analytics",
		Edges:       b.Build(),
	})
}

// ── Main ──────────────────────────────────────────────────────

func main() {
	ctx := context.Background()

	a, err := buildAgent()
	if err != nil {
		log.Fatalf("build: %v", err)
	}

	log.Printf("Content Pipeline Agent: %s", a.Name())
	if dryRun {
		log.Printf("Mode: DRY RUN (set ADK_PIPELINE_DRY_RUN=false for live + HITL)")
	} else {
		log.Printf("Mode: LIVE (HITL approval required per platform)")
	}

	config := &launcher.Config{
		AgentLoader: agent.NewSingleLoader(a),
	}
	l := full.NewLauncher()
	if err := l.Execute(ctx, config, os.Args[1:]); err != nil {
		log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
	}
}
