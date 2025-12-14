import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Network,
  Search,
  Filter,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Download
} from 'lucide-react';
import * as d3 from 'd3';
import axios from 'axios';

const KnowledgeGraph = () => {
  const svgRef = useRef(null);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [filteredData, setFilteredData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const simulationRef = useRef(null);

  useEffect(() => {
    fetchGraphData();
  }, []);

  useEffect(() => {
    if (graphData.nodes.length > 0) {
      filterAndRenderGraph();
    }
  }, [graphData, searchTerm, filterType]);

  const fetchGraphData = async () => {
    try {
      const response = await axios.get('/api/relationships/knowledge-graph');
      const data = response.data.graph;
      setGraphData(data);
      setFilteredData(data);
    } catch (error) {
      console.error('Failed to fetch knowledge graph:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterAndRenderGraph = () => {
    let filteredNodes = [...graphData.nodes];
    let filteredEdges = [...graphData.edges];

    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filteredNodes = filteredNodes.filter(node =>
        node.title.toLowerCase().includes(searchLower) ||
        node.entities?.tech_terms?.some(term => term.toLowerCase().includes(searchLower)) ||
        node.entities?.business_terms?.some(term => term.toLowerCase().includes(searchLower))
      );

      const nodeIds = new Set(filteredNodes.map(n => n.id));
      filteredEdges = filteredEdges.filter(edge =>
        nodeIds.has(graphData.nodes[edge.source]?.id) &&
        nodeIds.has(graphData.nodes[edge.target]?.id)
      );
    }

    // Apply type filter
    if (filterType !== 'all') {
      filteredNodes = filteredNodes.filter(node => node.type === filterType);
    }

    setFilteredData({ nodes: filteredNodes, edges: filteredEdges });
  };

  useEffect(() => {
    if (!svgRef.current || filteredData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = 600;

    // Clear previous simulation
    if (simulationRef.current) {
      simulationRef.current.stop();
    }

    // Create simulation
    const simulation = d3.forceSimulation(filteredData.nodes)
      .force('link', d3.forceLink(filteredData.edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    simulationRef.current = simulation;

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    const g = svg.append('g');

    // Create arrow markers
    svg.append('defs').selectAll('marker')
      .data(['arrow'])
      .enter().append('marker')
      .attr('id', d => d)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 15)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create links
    const link = g.append('g')
      .selectAll('line')
      .data(filteredData.edges)
      .enter().append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.strength * 5))
      .attr('marker-end', 'url(#arrow)');

    // Create node groups
    const node = g.append('g')
      .selectAll('g')
      .data(filteredData.nodes)
      .enter().append('g')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add circles for nodes
    node.append('circle')
      .attr('r', d => Math.max(5, Math.min(30, d.importance * 30)))
      .attr('fill', d => getNodeColor(d))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNode(d);
      })
      .on('mouseover', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', d => Math.max(8, Math.min(35, d.importance * 30 + 5)));
      })
      .on('mouseout', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', d => Math.max(5, Math.min(30, d.importance * 30)));
      });

    // Add labels
    node.append('text')
      .text(d => {
        const title = d.title.length > 20 ? d.title.substring(0, 20) + '...' : d.title;
        return title;
      })
      .attr('font-size', 10)
      .attr('dx', 15)
      .attr('dy', 4)
      .style('pointer-events', 'none');

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => {
          const sourceNode = filteredData.nodes[d.source];
          return sourceNode ? sourceNode.x : 0;
        })
        .attr('y1', d => {
          const sourceNode = filteredData.nodes[d.source];
          return sourceNode ? sourceNode.y : 0;
        })
        .attr('x2', d => {
          const targetNode = filteredData.nodes[d.target];
          return targetNode ? targetNode.x : 0;
        })
        .attr('y2', d => {
          const targetNode = filteredData.nodes[d.target];
          return targetNode ? targetNode.y : 0;
        });

      node
        .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [filteredData]);

  const getNodeColor = (node) => {
    const colors = {
      'unconsumed': '#ef4444',
      'reading': '#eab308',
      'reviewed': '#3b82f6',
      'applied': '#10b981'
    };
    return colors[node.consumption_status] || '#6b7280';
  };

  const handleZoomIn = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().transform,
      d3.zoomIdentity.scale(1.3)
    );
  };

  const handleZoomOut = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().transform,
      d3.zoomIdentity.scale(0.7)
    );
  };

  const handleReset = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().transform,
      d3.zoomIdentity
    );
  };

  const exportGraph = () => {
    const dataStr = JSON.stringify(filteredData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = 'knowledge-graph.json';

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Knowledge Graph
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                {filteredData.nodes.length} nodes
              </Badge>
              <Badge variant="outline">
                {filteredData.edges.length} connections
              </Badge>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="flex items-center gap-2 flex-1 min-w-[300px]">
              <Search className="h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search nodes..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1"
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="article">Articles</SelectItem>
                <SelectItem value="tweet">Tweets</SelectItem>
                <SelectItem value="note">Notes</SelectItem>
                <SelectItem value="url">URLs</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" onClick={handleZoomIn}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={handleZoomOut}>
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={handleReset}>
                <RotateCcw className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={exportGraph}>
                <Download className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span>Unconsumed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <span>Reading</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span>Reviewed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span>Applied</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Graph */}
      <Card>
        <CardContent className="p-0">
          <svg
            ref={svgRef}
            width="100%"
            height={600}
            style={{ border: '1px solid #e5e7eb' }}
          />
        </CardContent>
      </Card>

      {/* Selected Node Details */}
      {selectedNode && (
        <Card>
          <CardHeader>
            <CardTitle>Node Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold">{selectedNode.title}</h4>
                <p className="text-sm text-gray-600 mt-1">
                  Type: {selectedNode.type || 'unknown'}
                </p>
                <p className="text-sm text-gray-600">
                  Status: <span className="capitalize">{selectedNode.consumption_status}</span>
                </p>
                <p className="text-sm text-gray-600">
                  Importance: {(selectedNode.importance || 0).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm font-semibold mb-2">Entities:</p>
                {selectedNode.entities && (
                  <div className="space-y-1">
                    {Object.entries(selectedNode.entities).map(([type, entities]) => (
                      entities.length > 0 && (
                        <div key={type} className="text-xs">
                          <span className="font-medium capitalize">{type}:</span>{' '}
                          <span className="text-gray-600">
                            {Array.isArray(entities) ? entities.slice(0, 3).join(', ') : entities}
                            {Array.isArray(entities) && entities.length > 3 && '...'}
                          </span>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default KnowledgeGraph;