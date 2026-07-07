// ADK Content Pipeline Dashboard
//
// Standalone web dashboard for monitoring pipeline status, viewing post history,
// and triggering pipeline runs.
//
// Build:  go build -o dashboard ./dashboard
// Run:    ./dashboard
// Serve:  http://localhost:8081

package main

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

//go:embed template.html
var templateHTML string

var (
	platformsDir = filepath.Join(os.Getenv("HOME"), ".config", "opencode", "platforms")
	postsFile    = filepath.Join(platformsDir, "posts.jsonl")
	pipelineBin  = filepath.Join(platformsDir, "adk_pipeline", "pipeline")
	runMu        sync.Mutex
)

// ── Data types ──────────────────────────────────────────────────

type PlatformStatus struct {
	Key         string `json:"key"`
	Name        string `json:"name"`
	Status      string `json:"status"`
	Via         string `json:"via,omitempty"`
	TokenStatus string `json:"token_status,omitempty"`
	Note        string `json:"note,omitempty"`
}

type PostEntry struct {
	Timestamp  string   `json:"timestamp"`
	Platform   string   `json:"platform"`
	Text       string   `json:"text"`
	PostID     string   `json:"post_id"`
	Status     string   `json:"status"`
	MediaPath  string   `json:"media_path,omitempty"`
	DryRun     bool     `json:"dry_run"`
	Platforms  []string `json:"platforms,omitempty"`
}

type RunResult struct {
	Success  bool     `json:"success"`
	Output   string   `json:"output"`
	Duration string   `json:"duration"`
	Posts    int      `json:"posts"`
}

type DashboardData struct {
	DryRun      bool              `json:"dry_run"`
	Backend     string            `json:"backend"`
	BackendReady bool             `json:"backend_ready"`
	Platforms   []PlatformStatus  `json:"platforms"`
	History     []PostEntry       `json:"history"`
	LastRun     string            `json:"last_run"`
	PipelinePID int               `json:"pipeline_pid"`
}

// ── Main ────────────────────────────────────────────────────────

func main() {
	port := "8081"
	if p := os.Getenv("DASHBOARD_PORT"); p != "" {
		port = p
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", handleDashboard)
	mux.HandleFunc("/api/status", handleStatus)
	mux.HandleFunc("/api/history", handleHistory)
	mux.HandleFunc("/api/run", handleRun)
	mux.HandleFunc("/api/platforms", handlePlatforms)

	addr := ":" + port
	log.Printf("Dashboard serving on http://localhost%s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}

// ── Handlers ────────────────────────────────────────────────────

func handleDashboard(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(templateHTML))
}

func handleStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(gatherData())
}

func handleHistory(w http.ResponseWriter, r *http.Request) {
	entries := readPostHistory()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(entries)
}

func handlePlatforms(w http.ResponseWriter, r *http.Request) {
	platforms := readPlatforms()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(platforms)
}

func handleRun(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	var req struct {
		Prompt string `json:"prompt"`
		DryRun *bool  `json:"dry_run"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if req.Prompt == "" {
		req.Prompt = "post a quick update"
	}

	runMu.Lock()
	defer runMu.Unlock()

	start := time.Now()

	// Build env: override dry-run if specified, else auto-detect
	cmd := exec.Command(pipelineBin, "console")
	cmd.Stdin = bytes.NewBufferString(req.Prompt + "\n")
	cmd.Dir = filepath.Dir(pipelineBin)

	if req.DryRun != nil {
		val := "true"
		if !*req.DryRun {
			val = "false"
		}
		cmd.Env = append(os.Environ(), "ADK_PIPELINE_DRY_RUN="+val)
	}

	output, err := cmd.CombinedOutput()
	duration := time.Since(start).Round(time.Millisecond).String()

	result := RunResult{
		Success:  err == nil,
		Output:   string(output),
		Duration: duration,
	}

	// Count posts from output
	if strings.Contains(string(output), "posts published") {
		fmt.Sscanf(string(output), "Done: %d posts published", &result.Posts)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// ── Data gathering ──────────────────────────────────────────────

func gatherData() DashboardData {
	data := DashboardData{
		DryRun:   true,
		Platforms: readPlatforms(),
		History:  readPostHistory(),
	}

	// Backend config
	bc, _ := readBackendConfig()
	data.Backend = bc.Backend
	data.BackendReady = bc.Status == "ready"

	// Determine dry-run from env or backend status
	envDR := os.Getenv("ADK_PIPELINE_DRY_RUN")
	if envDR == "false" {
		data.DryRun = false
	} else if envDR == "true" {
		data.DryRun = true
	} else {
		data.DryRun = !data.BackendReady
	}

	// Last run time
	if len(data.History) > 0 {
		data.LastRun = data.History[0].Timestamp
	}

	// Pipeline PID
	pidData, err := os.ReadFile(filepath.Join(platformsDir, "adk_pipeline", "pipeline.pid"))
	if err == nil {
		fmt.Sscanf(string(pidData), "%d", &data.PipelinePID)
	}

	return data
}

func readBackendConfig() (struct {
	Backend string `json:"backend"`
	Status  string `json:"status"`
}, error) {
	var cfg struct {
		Backend string `json:"backend"`
		Status  string `json:"status"`
	}
	data, err := os.ReadFile(filepath.Join(platformsDir, "backend.json"))
	if err != nil {
		return cfg, err
	}
	json.Unmarshal(data, &cfg)
	return cfg, nil
}

func readPlatforms() []PlatformStatus {
	var list []PlatformStatus

	// Read accounts.json
	data, err := os.ReadFile(filepath.Join(platformsDir, "accounts.json"))
	if err != nil {
		return list
	}

	var accts struct {
		Accounts map[string]struct {
			Name        string `json:"name"`
			Status      string `json:"status"`
			Via         string `json:"via,omitempty"`
			TokenStatus string `json:"token_status,omitempty"`
			Note        string `json:"note,omitempty"`
		} `json:"accounts"`
	}
	if json.Unmarshal(data, &accts) != nil {
		return list
	}

	// Sort keys for consistent display
	var keys []string
	for k := range accts.Accounts {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		a := accts.Accounts[k]
		list = append(list, PlatformStatus{
			Key:         k,
			Name:        a.Name,
			Status:      a.Status,
			Via:         a.Via,
			TokenStatus: a.TokenStatus,
			Note:        a.Note,
		})
	}

	return list
}

func readPostHistory() []PostEntry {
	var entries []PostEntry

	data, err := os.ReadFile(postsFile)
	if err != nil {
		return entries
	}

	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	// Read last 50 entries
	start := 0
	if len(lines) > 50 {
		start = len(lines) - 50
	}

	for _, line := range lines[start:] {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var entry PostEntry
		if json.Unmarshal([]byte(line), &entry) == nil {
			entries = append(entries, entry)
		}
	}

	// Reverse so newest first
	for i, j := 0, len(entries)-1; i < j; i, j = i+1, j-1 {
		entries[i], entries[j] = entries[j], entries[i]
	}

	return entries
}
