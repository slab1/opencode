#!/usr/bin/env python3
"""Bridge Understand Anything knowledge graphs into OpenCode shared context.

Maps the rich U-A graph schema (20 node types, 35 edge types, layers, tours)
into our cross-agent shared context format so agents can query, search,
and navigate codebases through the existing graphify infrastructure.

Usage:
  python3 understand-bridge.py --input graph.json --output context.json [--project NAME]
  python3 understand-bridge.py --input graph.json --summary
  python3 understand-bridge.py --input graph.json --generate-tour --output TOUR.md
  python3 understand-bridge.py --diff old.json new.json
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ─── ANSI colors (matching OpenCode conventions) ───────────────────────
class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    GRAY = "\033[90m"


# ─── Node type mapping: U-A → graphify ─────────────────────────────────
NODE_TYPE_MAP = {
    "file": "file",
    "function": "function",
    "class": "class",
    "module": "module",
    "service": "service",
    "endpoint": "endpoint",
    "table": "table",
    "domain": "domain",
    "flow": "flow",
    "step": "step",
    "config": "config",
    "document": "document",
    "schema": "schema",
    "pipeline": "pipeline",
    "resource": "resource",
    "article": "article",
    "entity": "entity",
    "topic": "topic",
    "claim": "claim",
    "source": "source",
    "concept": "concept",
}

# ─── Edge type categories (for reporting) ──────────────────────────────
EDGE_CATEGORIES = {
    "imports": "structural", "exports": "structural", "contains": "structural",
    "inherits": "structural", "implements": "structural",
    "calls": "behavioral", "subscribes": "behavioral", "publishes": "behavioral",
    "middleware": "behavioral",
    "reads_from": "dataflow", "writes_to": "dataflow", "transforms": "dataflow",
    "validates": "dataflow",
    "depends_on": "dependency", "tested_by": "dependency", "configures": "dependency",
    "related": "semantic", "similar_to": "semantic",
    "deploys": "infra", "serves": "infra", "provisions": "infra", "triggers": "infra",
    "migrates": "schema", "documents": "schema", "routes": "schema",
    "defines_schema": "schema",
    "contains_flow": "domain", "flow_step": "domain", "cross_domain": "domain",
    "cites": "knowledge", "contradicts": "knowledge", "builds_on": "knowledge",
    "exemplifies": "knowledge", "categorized_under": "knowledge", "authored_by": "knowledge",
}

# ─── Helpers ───────────────────────────────────────────────────────────

def safe_read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"{C.RED}Error reading {path}: {e}{C.RESET}", file=sys.stderr)
        return None


def safe_write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"{C.GREEN}✓ Written:{C.RESET} {path}")


def get_node_type_label(t):
    """Return human-readable label for a node type."""
    return NODE_TYPE_MAP.get(t, t)


def build_graph_summary(graph):
    """Produce a rich text summary of a Understand Anything knowledge graph."""
    project = graph.get("project", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    layers = graph.get("layers", [])
    tour = graph.get("tour", [])

    # Node type breakdown
    type_counts = defaultdict(int)
    for n in nodes:
        type_counts[n.get("type", "unknown")] += 1

    # Edge type breakdown
    edge_type_counts = defaultdict(int)
    edge_cat_counts = defaultdict(int)
    for e in edges:
        et = e.get("type", "unknown")
        edge_type_counts[et] += 1
        edge_cat_counts[EDGE_CATEGORIES.get(et, "other")] += 1

    # Complexity distribution
    complexity_counts = defaultdict(int)
    for n in nodes:
        complexity_counts[n.get("complexity", "unknown")] += 1

    # Top tags
    tag_counts = defaultdict(int)
    for n in nodes:
        for tag in n.get("tags", []):
            tag_counts[tag] += 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]

    lines = []
    lines.append(f"{C.BOLD}{C.CYAN}═══ Understand Anything Knowledge Graph ═══{C.RESET}")
    lines.append("")
    lines.append(f"  {C.BOLD}Project:{C.RESET}   {project.get('name', 'unknown')}")
    lines.append(f"  {C.BOLD}Analyzed:{C.RESET}  {project.get('analyzedAt', 'unknown')}")
    lines.append(f"  {C.BOLD}Commit:{C.RESET}    {project.get('gitCommitHash', 'unknown')[:12]}")
    lines.append(f"  {C.BOLD}Language:{C.RESET}  {', '.join(project.get('languages', []))}")
    lines.append(f"  {C.BOLD}Framework:{C.RESET} {', '.join(project.get('frameworks', []))}")

    lines.append("")
    lines.append(f"  {C.BOLD}{'Metric':<30} {'Count':>6}{C.RESET}")
    lines.append(f"  {'─'*38}")
    lines.append(f"  {'Total nodes':<30} {len(nodes):>6}")
    lines.append(f"  {'Total edges':<30} {len(edges):>6}")
    lines.append(f"  {'Architectural layers':<30} {len(layers):>6}")
    lines.append(f"  {'Guided tour steps':<30} {len(tour):>6}")

    lines.append("")
    lines.append(f"  {C.BOLD}Node Types:{C.RESET}")
    for t in sorted(type_counts.keys()):
        label = get_node_type_label(t)
        bar = "█" * min(type_counts[t], 40)
        lines.append(f"    {label:<15} {type_counts[t]:>5}  {bar}")

    lines.append("")
    lines.append(f"  {C.BOLD}Edge Categories:{C.RESET}")
    for cat in sorted(edge_cat_counts.keys()):
        bar = "█" * min(edge_cat_counts[cat], 40)
        lines.append(f"    {cat:<15} {edge_cat_counts[cat]:>5}  {bar}")

    lines.append("")
    lines.append(f"  {C.BOLD}Complexity:{C.RESET}")
    for c in ["simple", "moderate", "complex"]:
        count = complexity_counts.get(c, 0)
        lines.append(f"    {c:<15} {count:>5}")

    if top_tags:
        lines.append("")
        lines.append(f"  {C.BOLD}Top Tags:{C.RESET}")
        for tag, count in top_tags:
            lines.append(f"    {tag:<20} {count:>5}")

    if layers:
        lines.append("")
        lines.append(f"  {C.BOLD}Architectural Layers:{C.RESET}")
        for layer in layers:
            lines.append(f"    • {layer.get('name', '?')}  "
                         f"({len(layer.get('nodeIds', []))} nodes)")

    if tour:
        lines.append("")
        lines.append(f"  {C.BOLD}Guided Tour:{C.RESET}")
        for step in tour:
            lines.append(f"    {step.get('order', '?')}. {step.get('title', '?')}  "
                         f"({len(step.get('nodeIds', []))} topics)")

    return "\n".join(lines)


def bridge_to_shared_context(graph, project_name=None):
    """Map a Understand Anything knowledge graph into OpenCode shared context format.

    Returns a dict suitable for merging into shared/context.json under a
    'knowledge_graphs' key.
    """
    project = graph.get("project", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    name = project_name or project.get("name", "unknown")

    # Convert nodes to a simplified format
    graph_nodes = []
    for n in nodes:
        graph_nodes.append({
            "id": n["id"],
            "name": n.get("name", ""),
            "type": n.get("type", "file"),
            "summary": n.get("summary", ""),
            "tags": n.get("tags", []),
            "complexity": n.get("complexity", "moderate"),
            "filePath": n.get("filePath"),
            "lineRange": n.get("lineRange"),
        })

    # Convert edges
    graph_edges = []
    for e in edges:
        graph_edges.append({
            "source": e["source"],
            "target": e["target"],
            "type": e.get("type", "depends_on"),
            "direction": e.get("direction", "forward"),
            "weight": e.get("weight", 0.5),
            "description": e.get("description"),
        })

    # Build adjacency index for fast queries
    adj_forward = defaultdict(list)
    adj_backward = defaultdict(list)
    for e in graph_edges:
        adj_forward[e["source"]].append(e["target"])
        adj_backward[e["target"]].append(e["source"])

    # Node lookup
    node_map = {n["id"]: n for n in graph_nodes}

    # Detect entry points (nodes with high out-degree / in-degree ratio)
    entry_scores = {}
    for n in graph_nodes:
        nid = n["id"]
        out_deg = len(adj_forward.get(nid, []))
        in_deg = len(adj_backward.get(nid, []))
        entry_scores[nid] = out_deg - in_deg

    top_entries = sorted(entry_scores.items(), key=lambda x: -x[1])[:5]
    entry_points = []
    for nid, score in top_entries:
        if nid in node_map and score > 0:
            entry_points.append({"id": nid, "name": node_map[nid]["name"], "score": score})

    return {
        "projectName": name,
        "analyzedAt": project.get("analyzedAt", datetime.now(timezone.utc).isoformat()),
        "gitCommitHash": project.get("gitCommitHash", ""),
        "languages": project.get("languages", []),
        "frameworks": project.get("frameworks", []),
        "nodeCount": len(graph_nodes),
        "edgeCount": len(graph_edges),
        "entryPoints": entry_points,
        "layers": [
            {"name": l.get("name", ""), "description": l.get("description", ""),
             "nodeCount": len(l.get("nodeIds", []))}
            for l in graph.get("layers", [])
        ],
        "tourSteps": [
            {"order": t.get("order", 0), "title": t.get("title", ""),
             "description": t.get("description", "")}
            for t in graph.get("tour", [])
        ],
        "nodes": graph_nodes,
        "edges": graph_edges,
        "adjForward": dict(adj_forward),
        "adjBackward": dict(adj_backward),
    }


def generate_tour_markdown(graph):
    """Generate a markdown guided tour from the graph's tour steps."""
    project = graph.get("project", {})
    node_map = {n["id"]: n for n in graph.get("nodes", [])}
    tour = graph.get("tour", [])

    lines = []
    lines.append(f"# Guided Tour: {project.get('name', 'Unknown Project')}")
    lines.append("")
    lines.append(f"*Generated from Understand Anything knowledge graph*  ")
    lines.append(f"*Analyzed: {project.get('analyzedAt', 'unknown')}*")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(project.get("description", "No description available."))
    lines.append("")
    lines.append(f"- **Languages:** {', '.join(project.get('languages', []))}")
    lines.append(f"- **Frameworks:** {', '.join(project.get('frameworks', []))}")
    lines.append(f"- **Nodes:** {len(graph.get('nodes', []))}")
    lines.append(f"- **Edges:** {len(graph.get('edges', []))}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Tour Steps")
    lines.append("")

    for step in sorted(tour, key=lambda s: s.get("order", 0)):
        lines.append(f"### Step {step.get('order', '?')}: {step.get('title', 'Untitled')}")
        lines.append("")
        lines.append(step.get("description", ""))
        lines.append("")

        node_ids = step.get("nodeIds", [])
        if node_ids:
            lines.append("**Topics covered:**")
            lines.append("")
            for nid in node_ids:
                node = node_map.get(nid, {})
                if node:
                    lines.append(f"- **{node.get('name', nid)}** "
                                 f"({node.get('type', '?')}) — "
                                 f"{node.get('summary', '')}")
                else:
                    lines.append(f"- {nid}")
            lines.append("")

        lesson = step.get("languageLesson")
        if lesson:
            lines.append(f"> **💡 Language Concept:** {lesson}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Tour auto-generated by OpenCode Platform Manager *")

    return "\n".join(lines)


def compute_diff(old_graph, new_graph):
    """Compare two knowledge graphs and report changes."""
    old_nodes = {n["id"]: n for n in old_graph.get("nodes", [])}
    new_nodes = {n["id"]: n for n in new_graph.get("nodes", [])}

    old_edges = {(e["source"], e["target"], e.get("type", ""))
                 for e in old_graph.get("edges", [])}
    new_edges = {(e["source"], e["target"], e.get("type", ""))
                 for e in new_graph.get("edges", [])}

    added_nodes = set(new_nodes.keys()) - set(old_nodes.keys())
    removed_nodes = set(old_nodes.keys()) - set(new_nodes.keys())
    common_nodes = set(old_nodes.keys()) & set(new_nodes.keys())

    added_edges = new_edges - old_edges
    removed_edges = old_edges - new_edges

    # Detect changed summaries (semantic drift)
    changed_summaries = []
    for nid in common_nodes:
        old_summary = old_nodes[nid].get("summary", "")
        new_summary = new_nodes[nid].get("summary", "")
        if old_summary != new_summary:
            changed_summaries.append({
                "id": nid,
                "name": old_nodes[nid].get("name", nid),
                "oldSummary": old_summary[:100],
                "newSummary": new_summary[:100],
            })

    return {
        "addedNodes": len(added_nodes),
        "removedNodes": len(removed_nodes),
        "changedNodes": len(common_nodes),
        "addedEdges": len(added_edges),
        "removedEdges": len(removed_edges),
        "changedSummaries": len(changed_summaries),
        "addedNodeList": sorted(added_nodes)[:20],
        "removedNodeList": sorted(removed_nodes)[:20],
        "addedEdgeList": sorted(added_edges)[:20],
        "removedEdgeList": sorted(removed_edges)[:20],
        "changedSummaryList": changed_summaries[:10],
    }


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bridge Understand Anything knowledge graphs into OpenCode shared context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Path to understand-anything knowledge-graph.json")
    parser.add_argument("--output", "-o",
                        help="Path to output file (context.json, summary, or tour)")
    parser.add_argument("--project", "-p",
                        help="Optional project name override")
    parser.add_argument("--summary", action="store_true",
                        help="Print graph summary to stdout")
    parser.add_argument("--generate-tour", action="store_true",
                        help="Generate guided tour as markdown")
    parser.add_argument("--diff", metavar="OLD_GRAPH",
                        help="Compare two graph versions (pass old graph path)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without writing")

    args = parser.parse_args()
    input_path = args.input

    # ── Load graph ──
    graph = safe_read_json(input_path)
    if graph is None:
        sys.exit(1)

    # ── Summary mode ──
    if args.summary:
        print(build_graph_summary(graph))
        return

    # ── Diff mode ──
    if args.diff:
        old_graph = safe_read_json(args.diff)
        if old_graph is None:
            sys.exit(1)
        diff = compute_diff(old_graph, graph)
        print(f"{C.BOLD}{C.CYAN}═══ Knowledge Graph Diff ═══{C.RESET}")
        print(f"  {C.GREEN}+{diff['addedNodes']} nodes{C.RESET}  "
              f"{C.RED}-{diff['removedNodes']} nodes{C.RESET}  "
              f"{C.YELLOW}~{diff['changedSummaries']} summaries changed{C.RESET}")
        print(f"  {C.GREEN}+{diff['addedEdges']} edges{C.RESET}  "
              f"{C.RED}-{diff['removedEdges']} edges{C.RESET}")
        if diff["addedNodeList"]:
            print(f"  {C.GREEN}Added:{C.RESET} {', '.join(diff['addedNodeList'][:5])}")
        if diff["removedNodeList"]:
            print(f"  {C.RED}Removed:{C.RESET} {', '.join(diff['removedNodeList'][:5])}")
        if diff["changedSummaryList"]:
            print(f"  {C.YELLOW}Summary changes:{C.RESET}")
            for item in diff["changedSummaryList"][:3]:
                print(f"    {item['name']}: {item['oldSummary'][:60]} → {item['newSummary'][:60]}")
        return

    # ── Generate tour mode ──
    if args.generate_tour:
        tour_md = generate_tour_markdown(graph)
        if args.dry_run:
            print(f"{C.YELLOW}[dry-run] Would write tour ({len(tour_md)} chars) → {args.output}{C.RESET}")
            return
        if not args.output:
            print(tour_md)
            return
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(tour_md)
        print(f"{C.GREEN}✓ Tour written:{C.RESET} {args.output} ({len(tour_md)} chars)")
        return

    # ── Bridge to shared context mode ──
    if not args.output:
        print(f"{C.RED}Error: --output required for bridge mode (use --summary or --generate-tour instead){C.RESET}",
              file=sys.stderr)
        sys.exit(1)

    bridge_data = bridge_to_shared_context(graph, project_name=args.project)

    if args.dry_run:
        print(f"{C.YELLOW}[dry-run] Would merge {len(bridge_data['nodes'])} nodes, "
              f"{len(bridge_data['edges'])} edges → {args.output}{C.RESET}")
        return

    # Read existing context, merge, write
    existing = safe_read_json(args.output) or {}
    if "knowledge_graphs" not in existing:
        existing["knowledge_graphs"] = {}
    existing["knowledge_graphs"][bridge_data["projectName"]] = bridge_data

    # Update last_analyzed
    existing["last_analyzed"] = bridge_data["projectName"]

    safe_write_json(args.output, existing)
    print(f"{C.GREEN}✓ Bridged {len(bridge_data['nodes'])} nodes, "
          f"{len(bridge_data['edges'])} edges → {args.output}{C.RESET}")
    print(f"  Project: {bridge_data['projectName']}")
    print(f"  Languages: {', '.join(bridge_data['languages'])}")
    print(f"  Layers: {len(bridge_data['layers'])}")
    print(f"  Tour steps: {len(bridge_data['tourSteps'])}")


if __name__ == "__main__":
    main()
