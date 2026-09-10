#!/usr/bin/env python3
"""
Super Dev 知识图谱构建器
从 knowledge/ 目录提取知识节点和关系，构建可查询的知识图谱。

用法:
    python scripts/knowledge_graph_builder.py build      # 构建知识图谱
    python scripts/knowledge_graph_builder.py query "React性能优化"  # 查询
    python scripts/knowledge_graph_builder.py path "python-basics" "fastapi-complete"  # 学习路径
    python scripts/knowledge_graph_builder.py stats      # 统计信息
    python scripts/knowledge_graph_builder.py export     # 导出 JSON
"""

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class KnowledgeNode:
    """知识节点"""

    id: str
    title: str
    domain: str
    category: str  # 01-standards, 02-playbooks, etc.
    file_path: str
    difficulty: str = "intermediate"  # beginner/intermediate/advanced/expert
    tags: list[str] = field(default_factory=list)
    line_count: int = 0
    has_code: bool = False
    has_agent_checklist: bool = False
    summary: str = ""


@dataclass
class KnowledgeEdge:
    """知识关系"""

    source: str
    target: str
    relation: str  # prerequisite, related, alternative, applies_to, contains


@dataclass
class KnowledgeGraph:
    """知识图谱"""

    nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: list[KnowledgeEdge] = field(default_factory=list)
    _adjacency: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def add_node(self, node: KnowledgeNode):
        self.nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge):
        self.edges.append(edge)
        self._adjacency.setdefault(edge.source, []).append((edge.target, edge.relation))
        self._adjacency.setdefault(edge.target, []).append((edge.source, f"inv_{edge.relation}"))

    def get_neighbors(self, node_id: str) -> list[tuple[str, str]]:
        return self._adjacency.get(node_id, [])

    def query_by_tags(self, tags: list[str], limit: int = 10) -> list[KnowledgeNode]:
        results = []
        tag_set = set(t.lower() for t in tags)
        for node in self.nodes.values():
            node_tags = set(t.lower() for t in node.tags)
            overlap = len(tag_set & node_tags)
            if overlap > 0:
                results.append((overlap, node))
        results.sort(key=lambda x: (-x[0], x[1].title))
        return [n for _, n in results[:limit]]

    def query_by_domain(self, domain: str) -> list[KnowledgeNode]:
        return [n for n in self.nodes.values() if n.domain == domain]

    def query_by_text(self, query: str, limit: int = 10) -> list[KnowledgeNode]:
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []
        for node in self.nodes.values():
            score = 0
            text = f"{node.title} {node.summary} {' '.join(node.tags)}".lower()
            for word in query_words:
                if word in text:
                    score += 1
                if word in node.title.lower():
                    score += 3
                if word in [t.lower() for t in node.tags]:
                    score += 2
            if score > 0:
                results.append((score, node))
        results.sort(key=lambda x: -x[0])
        return [n for _, n in results[:limit]]

    def find_path(self, source_id: str, target_id: str, max_depth: int = 6) -> list[str]:
        """BFS 寻找学习路径"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        visited = {source_id}
        queue = [(source_id, [source_id])]
        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return path
            if len(path) >= max_depth:
                continue
            for neighbor, relation in self.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def get_stats(self) -> dict:
        domains = {}
        categories = {}
        difficulties = {}
        for node in self.nodes.values():
            domains[node.domain] = domains.get(node.domain, 0) + 1
            categories[node.category] = categories.get(node.category, 0) + 1
            difficulties[node.difficulty] = difficulties.get(node.difficulty, 0) + 1
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "domains": dict(sorted(domains.items(), key=lambda x: -x[1])),
            "categories": dict(sorted(categories.items(), key=lambda x: -x[1])),
            "difficulties": difficulties,
        }


# ── 知识关系定义 ──────────────────────────────────────────────

PREREQUISITE_MAP = {
    # Python 生态
    "python-complete": [],
    "python-async-programming": ["python-complete"],
    "python-design-patterns": ["python-complete"],
    "pytest-complete": ["python-complete"],
    "fastapi-complete": ["python-complete", "python-async-programming"],
    "django-complete": ["python-complete"],
    # JavaScript/TypeScript 生态
    "javascript-typescript-complete": [],
    "typescript-advanced-types": ["javascript-typescript-complete"],
    "react-complete": ["javascript-typescript-complete"],
    "react-hooks-complete": ["react-complete"],
    "vue3-complete": ["javascript-typescript-complete"],
    "nestjs-complete": ["typescript-advanced-types"],
    # 数据库
    "postgresql-complete": [],
    "redis-complete": [],
    "elasticsearch-complete": [],
    "mongodb-complete": [],
    # DevOps
    "docker-complete": [],
    "kubernetes-complete": ["docker-complete"],
    "k8s-troubleshooting-playbook": ["kubernetes-complete"],
    "github-actions-complete": ["git-complete"],
    "terraform-complete": ["docker-complete"],
    # 架构
    "microservices-patterns": ["docker-complete"],
    "kafka-complete": ["microservices-patterns"],
    # 安全
    "owasp-top10-complete": [],
    # AI
    "llm-application-complete": ["python-complete"],
    # Go/Rust
    "golang-complete": [],
    "rust-complete": [],
}

RELATED_MAP = {
    "fastapi-complete": ["django-complete", "nestjs-complete"],
    "react-hooks-complete": ["vue3-complete"],
    "postgresql-complete": ["redis-complete", "elasticsearch-complete"],
    "docker-complete": ["kubernetes-complete"],
    "github-actions-complete": ["terraform-complete"],
    "microservices-patterns": ["kafka-complete", "kubernetes-complete"],
    "owasp-top10-complete": ["fastapi-complete", "django-complete", "nestjs-complete"],
    "testing-strategy-complete": ["pytest-complete"],
    "prometheus-monitoring-complete": ["kubernetes-complete", "docker-complete"],
    "incident-response-complete": ["prometheus-monitoring-complete"],
}

DOMAIN_TAGS = {
    "development": ["programming", "coding", "software"],
    "frontend": ["ui", "web", "browser", "react", "vue"],
    "backend": ["api", "server", "database"],
    "devops": ["deployment", "ci-cd", "infrastructure"],
    "cloud-native": ["kubernetes", "container", "cloud"],
    "security": ["security", "owasp", "vulnerability"],
    "data": ["database", "sql", "nosql"],
    "data-engineering": ["etl", "pipeline", "streaming"],
    "ai": ["machine-learning", "llm", "agent"],
    "architecture": ["design", "patterns", "microservices"],
    "testing": ["test", "quality", "automation"],
    "cicd": ["ci", "cd", "automation", "pipeline"],
    "incident": ["incident", "oncall", "sre"],
    "operations": ["monitoring", "observability", "sre"],
    "design": ["ui", "ux", "design-system"],
    "product": ["product", "management", "agile"],
    "mobile": ["ios", "android", "react-native"],
    "blockchain": ["web3", "smart-contract", "defi"],
    "quantum": ["quantum", "qiskit", "algorithm"],
    "low-code": ["low-code", "no-code", "platform"],
    "industries": ["fintech", "ecommerce", "healthcare"],
}


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.graph = KnowledgeGraph()

    def build(self) -> KnowledgeGraph:
        """从知识库文件构建图谱"""
        self._extract_nodes()
        self._build_edges()
        return self.graph

    def _extract_nodes(self):
        """从 Markdown 文件提取节点"""
        for md_file in sorted(self.knowledge_dir.rglob("*.md")):
            rel_path = md_file.relative_to(self.knowledge_dir)
            parts = rel_path.parts

            if len(parts) < 2:
                continue

            domain = parts[0]
            category = parts[1] if len(parts) > 2 else "root"

            content = md_file.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            line_count = len(lines)

            # 提取标题
            title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else md_file.stem

            # 生成 ID
            node_id = md_file.stem

            # 提取标签
            tags = list(DOMAIN_TAGS.get(domain, []))
            # 从内容中提取更多标签
            for keyword in [
                "python",
                "javascript",
                "typescript",
                "react",
                "vue",
                "docker",
                "kubernetes",
                "postgresql",
                "redis",
                "kafka",
                "fastapi",
                "django",
                "go",
                "rust",
                "java",
                "security",
                "performance",
                "testing",
            ]:
                if keyword in content.lower() and keyword not in tags:
                    tags.append(keyword)

            # 判断难度
            difficulty = "intermediate"
            if any(w in title.lower() for w in ["basics", "introduction", "入门", "beginner"]):
                difficulty = "beginner"
            elif any(w in title.lower() for w in ["advanced", "deep", "高级", "深度", "complete"]):
                difficulty = "advanced"
            elif any(w in title.lower() for w in ["expert", "internals", "专家"]):
                difficulty = "expert"

            # 检测代码和 Agent Checklist
            has_code = bool(re.search(r"```\w+", content))
            has_agent_checklist = bool(re.search(r"agent.*checklist", content, re.IGNORECASE))

            # 提取摘要（第一个非标题段落）
            summary = ""
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                    summary = stripped[:200]
                    break

            node = KnowledgeNode(
                id=node_id,
                title=title,
                domain=domain,
                category=category,
                file_path=str(md_file),
                difficulty=difficulty,
                tags=tags[:15],
                line_count=line_count,
                has_code=has_code,
                has_agent_checklist=has_agent_checklist,
                summary=summary,
            )
            self.graph.add_node(node)

    def _build_edges(self):
        """构建知识关系"""
        # 前置关系
        for target, sources in PREREQUISITE_MAP.items():
            if target in self.graph.nodes:
                for source in sources:
                    if source in self.graph.nodes:
                        self.graph.add_edge(KnowledgeEdge(source, target, "prerequisite"))

        # 相关关系
        for source, targets in RELATED_MAP.items():
            if source in self.graph.nodes:
                for target in targets:
                    if target in self.graph.nodes:
                        self.graph.add_edge(KnowledgeEdge(source, target, "related"))

        # 同域关系（同一领域的文件自动关联）
        by_domain: dict[str, list[str]] = {}
        for node in self.graph.nodes.values():
            by_domain.setdefault(node.domain, []).append(node.id)

        for domain, node_ids in by_domain.items():
            if len(node_ids) <= 10:
                for i, a in enumerate(node_ids):
                    for b in node_ids[i + 1 :]:
                        if not any(e.source == a and e.target == b for e in self.graph.edges):
                            self.graph.add_edge(KnowledgeEdge(a, b, "related"))

    def export_json(self, output_path: str = "output/knowledge-graph.json"):
        """导出为 JSON"""
        data = {
            "nodes": [asdict(n) for n in self.graph.nodes.values()],
            "edges": [asdict(e) for e in self.graph.edges],
            "stats": self.graph.get_stats(),
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Knowledge graph exported to {output_path}")
        return data


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/knowledge_graph_builder.py [build|query|path|stats|export]")
        sys.exit(1)

    command = sys.argv[1]
    builder = KnowledgeGraphBuilder()
    graph = builder.build()

    if command == "build":
        stats = graph.get_stats()
        print("知识图谱构建完成!")
        print(f"  节点数: {stats['total_nodes']}")
        print(f"  关系数: {stats['total_edges']}")
        print("\n  领域分布:")
        for domain, count in stats["domains"].items():
            print(f"    {domain}: {count}")

    elif command == "query":
        if len(sys.argv) < 3:
            print("用法: python scripts/knowledge_graph_builder.py query '查询文本'")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        results = graph.query_by_text(query)
        print(f"查询: '{query}'")
        print(f"找到 {len(results)} 个相关知识:\n")
        for node in results:
            neighbors = graph.get_neighbors(node.id)
            related = [f"{nid}({rel})" for nid, rel in neighbors[:3]]
            print(f"  [{node.difficulty}] {node.title}")
            print(f"    文件: {node.file_path} ({node.line_count}行)")
            print(f"    标签: {', '.join(node.tags[:5])}")
            if related:
                print(f"    关联: {', '.join(related)}")
            print()

    elif command == "path":
        if len(sys.argv) < 4:
            print("用法: python scripts/knowledge_graph_builder.py path 'source-id' 'target-id'")
            sys.exit(1)
        source, target = sys.argv[2], sys.argv[3]
        path = graph.find_path(source, target)
        if path:
            print(f"学习路径: {source} → {target}")
            for i, node_id in enumerate(path):
                node = graph.nodes.get(node_id)
                if node:
                    print(f"  {i+1}. [{node.difficulty}] {node.title} ({node.line_count}行)")
        else:
            print(f"未找到从 {source} 到 {target} 的路径")

    elif command == "stats":
        stats = graph.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif command == "export":
        builder.export_json()

    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
