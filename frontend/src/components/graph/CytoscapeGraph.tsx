import React, { useEffect, useRef, useState } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import { GraphData, GraphNode } from '../../types';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw, Layers } from 'lucide-react';

interface CytoscapeGraphProps {
  data: GraphData;
  onNodeSelect?: (node: GraphNode | null) => void;
  focalNodeId?: string;
  height?: string;
}

export const CytoscapeGraph: React.FC<CytoscapeGraphProps> = ({
  data,
  onNodeSelect,
  focalNodeId,
  height = '600px',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layoutName, setLayoutName] = useState<'cose' | 'breadthfirst' | 'concentric' | 'circle'>('cose');

  useEffect(() => {
    if (!containerRef.current) return;

    // Convert GraphData to Cytoscape elements
    const elements: cytoscape.ElementDefinition[] = [];

    data.nodes.forEach((n) => {
      elements.push({
        group: 'nodes',
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          risk_score: n.risk_score,
          anomaly_score: n.anomaly_score,
          is_focal: n.id === focalNodeId,
          raw_node: n,
        },
      });
    });

    data.edges.forEach((e) => {
      elements.push({
        group: 'edges',
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.label || '',
          amount: e.amount,
        },
      });
    });

    const stylesheet: any[] = [
      // Node base
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'color': '#E2E8F0',
          'font-family': 'JetBrains Mono, monospace',
          'font-size': '11px',
          'text-valign': 'bottom',
          'text-margin-y': 6,
          'text-background-color': '#0B0F19',
          'text-background-opacity': 0.85,
          'text-background-padding': '3px',
          'text-background-shape': 'roundrectangle',
          'border-width': 2,
          'border-color': '#334155',
          'transition-property': 'background-color, border-color, width, height',
          'transition-duration': '0.2s',
        },
      },
      // WALLET Nodes
      {
        selector: 'node[type = "WALLET"]',
        style: {
          'background-color': '#10B981', // Emerald
          'shape': 'ellipse',
          'width': 36,
          'height': 36,
          'border-color': '#059669',
        },
      },
      // TRANSACTION Nodes
      {
        selector: 'node[type = "TRANSACTION"]',
        style: {
          'background-color': '#3B82F6', // Blue
          'shape': 'round-rectangle',
          'width': 32,
          'height': 32,
          'border-color': '#2563EB',
        },
      },
      // IP Nodes
      {
        selector: 'node[type = "IP"]',
        style: {
          'background-color': '#8B5CF6', // Purple
          'shape': 'diamond',
          'width': 34,
          'height': 34,
          'border-color': '#7C3AED',
        },
      },
      // ASN Nodes
      {
        selector: 'node[type = "ASN"]',
        style: {
          'background-color': '#F59E0B', // Amber
          'shape': 'hexagon',
          'width': 30,
          'height': 30,
          'border-color': '#D97706',
        },
      },
      // COUNTRY Nodes
      {
        selector: 'node[type = "COUNTRY"]',
        style: {
          'background-color': '#EC4899', // Pink
          'shape': 'octagon',
          'width': 28,
          'height': 28,
          'border-color': '#DB2777',
        },
      },
      // High Risk Glow
      {
        selector: 'node[risk_score >= 60]',
        style: {
          'background-color': '#EF4444',
          'border-color': '#F87171',
          'border-width': 4,
          'width': 44,
          'height': 44,
          'underlay-color': '#EF4444',
          'underlay-padding': '6px',
          'underlay-opacity': 0.4,
        },
      },
      // Medium Risk
      {
        selector: 'node[risk_score >= 35][risk_score < 60]',
        style: {
          'background-color': '#F97316',
          'border-color': '#FB923C',
          'border-width': 3,
          'width': 38,
          'height': 38,
          'underlay-color': '#F97316',
          'underlay-padding': '4px',
          'underlay-opacity': 0.3,
        },
      },
      // Focal Node
      {
        selector: 'node:selected, node[?is_focal]',
        style: {
          'border-color': '#38BDF8',
          'border-width': 4,
          'underlay-color': '#38BDF8',
          'underlay-padding': '8px',
          'underlay-opacity': 0.5,
        },
      },
      // Edge base
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#475569',
          'target-arrow-color': '#475569',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 1.2,
          'font-family': 'JetBrains Mono, monospace',
          'font-size': '9px',
          'color': '#94A3B8',
          'text-background-color': '#0B0F19',
          'text-background-opacity': 0.8,
          'text-background-padding': '2px',
          'text-rotation': 'autorotate',
          'label': 'data(label)',
        },
      },
      // Value flow edges
      {
        selector: 'edge[type = "INPUT_OF"], edge[type = "OUTPUT_TO"]',
        style: {
          'line-color': '#10B981',
          'target-arrow-color': '#10B981',
          'width': 2.5,
        },
      },
      // Network relay edges
      {
        selector: 'edge[type = "OBSERVED_IN"]',
        style: {
          'line-color': '#8B5CF6',
          'target-arrow-color': '#8B5CF6',
          'line-style': 'dashed',
          'width': 2,
        },
      },
    ];

    const effectiveLayout = (elements.filter(e => e.group === 'edges').length === 0 && layoutName === 'cose')
      ? 'concentric'
      : layoutName;

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: stylesheet,
      layout: {
        name: effectiveLayout,
        animate: true,
        animationDuration: 400,
        padding: 40,
      } as any,
    });

    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const raw = node.data('raw_node') as GraphNode;
      if (onNodeSelect) {
        onNodeSelect(raw);
      }
    });

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy && onNodeSelect) {
        onNodeSelect(null);
      }
    });

    cyRef.current = cy;

    // Ensure layout dimensions stabilize and graph fits canvas
    const fitTimer = setTimeout(() => {
      if (cyRef.current) {
        cyRef.current.resize();
        cyRef.current.fit(undefined, 40);
      }
    }, 80);

    // ResizeObserver ensures canvas scales accurately on window/drawer resize
    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        if (cyRef.current) {
          cyRef.current.resize();
        }
      });
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      clearTimeout(fitTimer);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      cy.destroy();
    };
  }, [data, layoutName, focalNodeId]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 40);
  const handleResetLayout = () => {
    const effectiveLayout = (data.edges.length === 0 && layoutName === 'cose') ? 'concentric' : layoutName;
    cyRef.current?.layout({ name: effectiveLayout, animate: true, padding: 40 } as any).run();
  };

  return (
    <div className="cyber-card relative overflow-hidden border border-cyber-border rounded-xl" style={{ height }}>
      {/* Cytoscape Canvas */}
      <div ref={containerRef} className="w-full h-full bg-cyber-bg" />

      {/* Empty State Overlay */}
      {data.nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-slate-950/80 backdrop-blur-sm z-20">
          <Layers className="w-10 h-10 text-slate-600 mb-3" />
          <h4 className="text-sm font-bold text-slate-300 uppercase tracking-wider">No Graph Nodes Available</h4>
          <p className="text-xs text-slate-500 max-w-sm mt-1">
            No topological links found for the selected entity or dataset scope. Select another entity or reset to the global view.
          </p>
        </div>
      )}

      {/* Floating Toolbar */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-1.5 p-1 rounded-lg bg-cyber-card/90 backdrop-blur-md border border-cyber-border shadow-lg">
        {/* Layout Selector */}
        <div className="flex items-center gap-1 px-2 border-r border-slate-700 text-xs font-mono text-slate-400">
          <Layers className="w-3.5 h-3.5 text-cyber-emerald" />
          <select
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value as any)}
            className="bg-transparent text-slate-200 text-xs focus:outline-none cursor-pointer"
          >
            <option value="cose" className="bg-slate-900">Force Directed (COSE)</option>
            <option value="breadthfirst" className="bg-slate-900">Hierarchy (Breadthfirst)</option>
            <option value="concentric" className="bg-slate-900">Concentric</option>
            <option value="circle" className="bg-slate-900">Circle</option>
          </select>
        </div>

        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFit}
          title="Fit to Screen"
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        <button
          onClick={handleResetLayout}
          title="Re-run Layout"
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Legend Footer */}
      <div className="absolute bottom-4 left-4 z-10 flex flex-wrap items-center gap-3 p-2 rounded-lg bg-cyber-card/90 backdrop-blur-md border border-cyber-border text-[11px] font-mono text-slate-300 shadow-md">
        <span className="text-slate-500 font-semibold uppercase text-[10px]">LEGEND:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
          <span>Wallet</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-500 inline-block" />
          <span>Transaction</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rotate-45 bg-purple-500 inline-block" />
          <span>Relay IP</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block shadow-[0_0_8px_#EF4444]" />
          <span>Anomalous Node</span>
        </div>
      </div>
    </div>
  );
};
