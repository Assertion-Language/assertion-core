/*
Execution DAG Visualizer
========================

Standalone graph engine using:
- Force-directed layout (physics)
- Canvas rendering
- Real-time node updates
- Node click events
- Status coloring

API:

DAGVisualizer.init("canvas-id");
DAGVisualizer.setGraph({ nodes:[...], edges:[...] });
DAGVisualizer.updateNodeState(nodeId, state);
DAGVisualizer.onNodeClick = fn;

*/

const DAGVisualizer = (() => {

    // Physics parameters
    const REPULSION = 9500;
    const SPRING = 0.05;
    const DAMPING = 0.85;
    const EDGE_LENGTH = 140;

    let canvas, ctx;
    let nodes = [];
    let edges = [];
    let nodeMap = new Map();
    let running = false;

    let onNodeClickHandler = null;

    function randomPos() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: 0,
            vy: 0
        };
    }

    function init(canvasId) {
        canvas = document.getElementById(canvasId);
        ctx = canvas.getContext("2d");

        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;

        canvas.addEventListener("click", canvasClick);

        running = true;
        requestAnimationFrame(loop);
    }

    function setGraph(graph) {
        nodes = graph.nodes.map(n => {
            const pos = randomPos();
            const node = {
                id: n.id,
                label: n.label || n.id,
                state: n.state || "pending",
                x: pos.x,
                y: pos.y,
                vx: 0,
                vy: 0
            };
            nodeMap.set(node.id, node);
            return node;
        });

        edges = graph.edges.map(e => ({
            from: e.from,
            to: e.to
        }));
    }

    function updateNodeState(id, state) {
        const node = nodeMap.get(id);
        if (node) node.state = state;
    }

    // Node color scheme
    function nodeColor(state) {
        switch (state) {
            case "running": return "#00d4ff";
            case "completed": return "#00ff99";
            case "failed": return "#ff4a4a";
            default: return "#cccccc";
        }
    }

    function physics() {
        // Repulsion
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const a = nodes[i];
                const b = nodes[j];

                const dx = b.x - a.x;
                const dy = b.y - a.y;
                let dist = Math.sqrt(dx * dx + dy * dy) + 0.1;

                const force = REPULSION / (dist * dist);

                const fx = force * (dx / dist);
                const fy = force * (dy / dist);

                a.vx -= fx;
                a.vy -= fy;

                b.vx += fx;
                b.vy += fy;
            }
        }

        // Springs (edges)
        edges.forEach(e => {
            const a = nodeMap.get(e.from);
            const b = nodeMap.get(e.to);

            if (!a || !b) return;

            const dx = b.x - a.x;
            const dy = b.y - a.y;
            let dist = Math.sqrt(dx * dx + dy * dy) + 0.1;

            const force = SPRING * (dist - EDGE_LENGTH);

            const fx = force * (dx / dist);
            const fy = force * (dy / dist);

            a.vx += fx;
            a.vy += fy;

            b.vx -= fx;
            b.vy -= fy;
        });

        // Integrate motion
        nodes.forEach(n => {
            n.vx *= DAMPING;
            n.vy *= DAMPING;

            n.x += n.vx;
            n.y += n.vy;

            // Boundaries
            n.x = Math.max(20, Math.min(canvas.width - 20, n.x));
            n.y = Math.max(20, Math.min(canvas.height - 20, n.y));
        });
    }

    function drawArrow(x1, y1, x2, y2) {
        const headLen = 10;

        const angle = Math.atan2(y2 - y1, x2 - x1);
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);

        ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6),
                   y2 - headLen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6),
                   y2 - headLen * Math.sin(angle + Math.PI / 6));
    }

    function draw() {
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Edges
        ctx.strokeStyle = "#555";
        ctx.lineWidth = 1.5;

        ctx.beginPath();
        edges.forEach(e => {
            const a = nodeMap.get(e.from);
            const b = nodeMap.get(e.to);
            if (a && b) drawArrow(a.x, a.y, b.x, b.y);
        });
        ctx.stroke();

        // Nodes
        nodes.forEach(n => {
            ctx.fillStyle = nodeColor(n.state);
            ctx.beginPath();
            ctx.arc(n.x, n.y, 14, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = "#fff";
            ctx.font = "11px monospace";
            ctx.textAlign = "center";
            ctx.fillText(n.label, n.x, n.y + 30);
        });
    }

    function loop() {
        if (!running) return;
        physics();
        draw();
        requestAnimationFrame(loop);
    }

    function canvasClick(ev) {
        const rect = canvas.getBoundingClientRect();
        const x = ev.clientX - rect.left;
        const y = ev.clientY - rect.top;

        for (const n of nodes) {
            const dx = n.x - x;
            const dy = n.y - y;
            if (dx * dx + dy * dy < 16 * 16) {
                if (onNodeClickHandler) {
                    onNodeClickHandler(n);
                }
            }
        }
    }

    return {
        init,
        setGraph,
        updateNodeState,
        set onNodeClick(fn) { onNodeClickHandler = fn; }
    };
})();
